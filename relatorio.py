from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import tempfile
import time
from calendar import monthrange
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone, tzinfo
from pathlib import Path
from typing import Callable, Iterable, Iterator, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:  # pragma: no cover - Python 3.8 or older
    ZoneInfo = None  # type: ignore[assignment]
    ZoneInfoNotFoundError = Exception  # type: ignore[assignment]


PROJECT_ROOT = Path(__file__).resolve().parent
ENV_FILE = PROJECT_ROOT / "env.txt"
OUTPUT_ROOT = PROJECT_ROOT / "outputs"
REPORT_TIMEZONE_NAME = "America/Sao_Paulo"
IDENTIFICATION_FILENAME = "01_identificacao_periodo.csv"
MONTHLY_DISTRIBUTION_FILENAME = "02_distribuicao_mensal_responsavel.csv"
GLOBAL_STAGES_FILENAME = "03_numeros_globais_etapas.csv"
WEEKLY_CONVERSION_FILENAME = "04_conversao_responsavel.csv"
MONTHLY_DISTRIBUTION_FIELDS = [
    "mes_referencia",
    "pipeline_id",
    "pipeline_nome",
    "responsavel_id",
    "responsavel_nome",
    "usuario_ativo",
    "quantidade_leads",
    "participacao_percentual",
    "total_leads_mes",
    "data_hora_extracao",
]
GLOBAL_STAGES_FIELDS = [
    "mes_referencia",
    "pipeline_id",
    "pipeline_nome",
    "responsavel_id",
    "responsavel_nome",
    "categoria_relatorio",
    "status_id",
    "etapa_crm",
    "loss_reason_id",
    "motivo_perda_crm",
    "quantidade_leads",
    "total_responsavel",
    "percentual_responsavel",
    "total_geral",
    "percentual_geral",
    "data_hora_extracao",
]
WEEKLY_CONVERSION_FIELDS = [
    "pipeline_id",
    "pipeline_nome",
    "responsavel_id",
    "responsavel_nome",
    "universo",
    "semana_anterior_inicio",
    "semana_anterior_fim",
    "total_leads_anterior",
    "servicos_iniciados_anterior",
    "taxa_conversao_anterior",
    "semana_atual_inicio",
    "semana_atual_fim",
    "total_leads_atual",
    "servicos_iniciados_atual",
    "taxa_conversao_atual",
    "variacao_pp",
    "situacao_semana_atual",
    "observacao_maturacao",
    "data_hora_extracao",
]


class KommoApiError(RuntimeError):
    pass


@dataclass(frozen=True)
class KommoConfig:
    base_url: str
    token: str

    @classmethod
    def from_environment(cls) -> "KommoConfig":
        base_url = os.environ.get("KOMMO_BASE_URL", "").strip().rstrip("/")
        token = os.environ.get("KOMMO_TOKEN", "").strip()
        if not base_url:
            raise ValueError("KOMMO_BASE_URL não foi definido em env.txt.")
        if not token:
            raise ValueError("KOMMO_TOKEN não foi definido em env.txt.")

        parsed = urlparse(base_url)
        hostname = (parsed.hostname or "").lower()
        if (
            parsed.scheme != "https"
            or not hostname.endswith(".kommo.com")
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/"}
        ):
            raise ValueError(
                "KOMMO_BASE_URL deve ter o formato https://sua-conta.kommo.com."
            )
        return cls(base_url=base_url, token=token)


class KommoReadOnlyClient:
    """Cliente intencionalmente restrito a consultas GET na conta configurada."""

    def __init__(
        self,
        config: KommoConfig,
        *,
        timeout_seconds: float = 30.0,
        minimum_interval_seconds: float = 0.2,
        maximum_attempts: int = 4,
    ) -> None:
        self._config = config
        self._timeout_seconds = timeout_seconds
        self._minimum_interval_seconds = minimum_interval_seconds
        self._maximum_attempts = maximum_attempts
        self._last_request_at = 0.0

    def _respect_rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        remaining = self._minimum_interval_seconds - elapsed
        if remaining > 0:
            time.sleep(remaining)

    def get_json(
        self, path: str, params: Mapping[str, object] | None = None
    ) -> dict[str, object] | None:
        if not path.startswith("/api/v4/"):
            raise KommoApiError("Endpoint Kommo não permitido pelo cliente de leitura.")

        query = urlencode(params or {}, doseq=True)
        url = f"{self._config.base_url}{path}"
        if query:
            url = f"{url}?{query}"

        request = Request(
            url,
            headers={
                "Accept": "application/hal+json, application/json",
                "Authorization": f"Bearer {self._config.token}",
                "User-Agent": "Advanced-Relatorio-Comercial/1.0",
            },
            method="GET",
        )

        retryable_statuses = {429, 500, 502, 503, 504}
        for attempt in range(self._maximum_attempts):
            self._respect_rate_limit()
            try:
                with urlopen(request, timeout=self._timeout_seconds) as response:
                    self._last_request_at = time.monotonic()
                    payload = response.read()
                    if response.status == 204 or not payload:
                        return None
                    decoded = json.loads(payload.decode("utf-8"))
                    if not isinstance(decoded, dict):
                        raise KommoApiError("A Kommo retornou uma resposta JSON inesperada.")
                    return decoded
            except HTTPError as exc:
                self._last_request_at = time.monotonic()
                if exc.code in retryable_statuses and attempt + 1 < self._maximum_attempts:
                    retry_after = exc.headers.get("Retry-After")
                    try:
                        delay = float(retry_after) if retry_after else 2**attempt
                    except ValueError:
                        delay = 2**attempt
                    time.sleep(min(max(delay, 0.5), 10.0))
                    continue
                if exc.code == 401:
                    raise KommoApiError("Token Kommo inválido, expirado ou revogado.") from exc
                if exc.code == 403:
                    raise KommoApiError("A integração não possui permissão para esta consulta.") from exc
                raise KommoApiError(f"A Kommo respondeu com HTTP {exc.code}.") from exc
            except URLError as exc:
                self._last_request_at = time.monotonic()
                if attempt + 1 < self._maximum_attempts:
                    time.sleep(min(2**attempt, 10.0))
                    continue
                raise KommoApiError(f"Não foi possível conectar à Kommo: {exc.reason}") from exc
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise KommoApiError("A Kommo retornou JSON inválido.") from exc

        raise KommoApiError("A consulta à Kommo não pôde ser concluída.")


@dataclass(frozen=True)
class PeriodIdentification:
    titulo: str
    data_inicial: str
    data_final: str
    fuso_horario: str
    situacao_semana: str
    fecha_mes: str
    mes_fechado: str
    data_hora_geracao: str


@dataclass(frozen=True)
class MonthlySnapshot:
    pipeline: dict[str, object]
    users: dict[int, dict[str, object]]
    loss_reasons: list[dict[str, object]]
    leads: list[dict[str, object]]


@dataclass(frozen=True)
class WeeklySnapshot:
    pipeline: dict[str, object]
    users: dict[int, dict[str, object]]
    leads: list[dict[str, object]]


def load_env_file(path: Path = ENV_FILE) -> None:
    """Load KEY=VALUE entries without replacing variables already in the environment."""
    if not path.exists():
        return

    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"Linha {line_number} inválida em {path.name}; use CHAVE=VALOR.")
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            raise ValueError(f"Chave vazia na linha {line_number} de {path.name}.")
        os.environ.setdefault(key, value)


def report_timezone() -> tzinfo:
    if ZoneInfo is not None:
        try:
            return ZoneInfo(REPORT_TIMEZONE_NAME)
        except ZoneInfoNotFoundError:
            pass
    # O Brasil não adota horário de verão desde 2019. Este fallback mantém o
    # script funcional em instalações Windows sem o banco IANA de fusos.
    return timezone(timedelta(hours=-3), name="-03:00")


def parse_week_start(value: str) -> date:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "a data deve estar no formato AAAA-MM-DD, por exemplo 2026-08-17"
        ) from exc
    return parsed


def week_status(week_start: date, today: date) -> str:
    week_end = week_start + timedelta(days=6)
    if today < week_start:
        return "futura"
    if today <= week_end:
        return "parcial"
    return "completa"


def closing_month(week_start: date) -> str:
    for offset in range(7):
        current = week_start + timedelta(days=offset)
        if current.day == monthrange(current.year, current.month)[1]:
            return current.strftime("%Y-%m")
    return ""


def month_boundaries(month_reference: str) -> tuple[date, date]:
    year_text, month_text = month_reference.split("-", 1)
    month_start = date(int(year_text), int(month_text), 1)
    if month_start.month == 12:
        next_month = date(month_start.year + 1, 1, 1)
    else:
        next_month = date(month_start.year, month_start.month + 1, 1)
    return month_start, next_month


def build_identification(week_start: date, generated_at: datetime) -> PeriodIdentification:
    week_end = week_start + timedelta(days=6)
    closed_month = closing_month(week_start)
    return PeriodIdentification(
        titulo="Relatório de Desempenho Comercial",
        data_inicial=week_start.isoformat(),
        data_final=week_end.isoformat(),
        fuso_horario=REPORT_TIMEZONE_NAME,
        situacao_semana=week_status(week_start, generated_at.date()),
        fecha_mes="sim" if closed_month else "não",
        mes_fechado=closed_month,
        data_hora_geracao=generated_at.isoformat(timespec="seconds"),
    )


def output_path(week_start: date) -> Path:
    return (
        OUTPUT_ROOT
        / str(week_start.year)
        / week_start.isoformat()
        / IDENTIFICATION_FILENAME
    )


def monthly_distribution_path(week_start: date) -> Path:
    return (
        OUTPUT_ROOT
        / str(week_start.year)
        / week_start.isoformat()
        / MONTHLY_DISTRIBUTION_FILENAME
    )


def global_stages_path(week_start: date) -> Path:
    return (
        OUTPUT_ROOT
        / str(week_start.year)
        / week_start.isoformat()
        / GLOBAL_STAGES_FILENAME
    )


def weekly_conversion_path(week_start: date) -> Path:
    return (
        OUTPUT_ROOT
        / str(week_start.year)
        / week_start.isoformat()
        / WEEKLY_CONVERSION_FILENAME
    )


def confirm_overwrite(path: Path, input_fn: Callable[[str], str] = input) -> bool:
    if not path.exists():
        return True

    print(f"O arquivo já existe: {path}")
    try:
        answer = input_fn("Deseja sobrescrevê-lo? [s/N]: ").strip().casefold()
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    return answer in {"s", "sim"}


def write_csv_rows_atomic(
    path: Path, fieldnames: Sequence[str], rows: Iterable[Mapping[str, object]]
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8-sig",
            newline="",
            dir=path.parent,
            prefix=f".{path.stem}_",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            writer = csv.DictWriter(temporary_file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, path)
    except Exception:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise


def write_csv_atomic(path: Path, record: PeriodIdentification) -> None:
    row = asdict(record)
    write_csv_rows_atomic(path, list(row), [row])


def embedded_collection(
    payload: Mapping[str, object] | None, collection_name: str
) -> list[dict[str, object]]:
    if payload is None:
        return []
    embedded = payload.get("_embedded")
    if not isinstance(embedded, dict):
        raise KommoApiError("Resposta da Kommo sem o objeto _embedded esperado.")
    collection = embedded.get(collection_name, [])
    if not isinstance(collection, list):
        raise KommoApiError(f"Coleção {collection_name} inválida na resposta da Kommo.")
    return [item for item in collection if isinstance(item, dict)]


def iter_kommo_collection(
    client: KommoReadOnlyClient,
    path: str,
    collection_name: str,
    params: Mapping[str, object] | None = None,
) -> Iterator[dict[str, object]]:
    limit = 250
    page = 1
    while True:
        page_params = dict(params or {})
        page_params.update({"limit": limit, "page": page})
        payload = client.get_json(path, page_params)
        items = embedded_collection(payload, collection_name)
        yield from items
        if len(items) < limit:
            return
        page += 1


def select_main_pipeline(client: KommoReadOnlyClient) -> dict[str, object]:
    payload = client.get_json("/api/v4/leads/pipelines")
    pipelines = embedded_collection(payload, "pipelines")
    candidates = [
        pipeline
        for pipeline in pipelines
        if pipeline.get("is_main") is True and pipeline.get("is_archive") is not True
    ]
    if len(candidates) != 1:
        raise KommoApiError(
            "Não foi possível identificar exatamente um funil principal ativo na Kommo."
        )
    return candidates[0]


def fetch_users(client: KommoReadOnlyClient) -> dict[int, dict[str, object]]:
    users: dict[int, dict[str, object]] = {}
    for user in iter_kommo_collection(client, "/api/v4/users", "users"):
        user_id = user.get("id")
        if isinstance(user_id, int):
            users[user_id] = user
    return users


def fetch_loss_reasons(client: KommoReadOnlyClient) -> list[dict[str, object]]:
    payload = client.get_json("/api/v4/leads/loss_reasons")
    reasons = embedded_collection(payload, "loss_reasons")
    return sorted(
        reasons,
        key=lambda reason: (
            reason.get("sort") if isinstance(reason.get("sort"), int) else 0,
            reason.get("id") if isinstance(reason.get("id"), int) else 0,
        ),
    )


def fetch_period_leads(
    client: KommoReadOnlyClient,
    pipeline_id: int,
    period_start: date,
    period_end_exclusive: date,
    tz: tzinfo,
    *,
    include_loss_reason: bool = False,
) -> Iterator[dict[str, object]]:
    start_at = datetime.combine(period_start, datetime.min.time(), tzinfo=tz)
    end_at = datetime.combine(period_end_exclusive, datetime.min.time(), tzinfo=tz)
    params = {
        "filter[created_at][from]": int(start_at.timestamp()),
        "filter[created_at][to]": int(end_at.timestamp()) - 1,
        "filter[pipeline_id][]": pipeline_id,
        "order[created_at]": "asc",
    }
    if include_loss_reason:
        params["with"] = "loss_reason"
    for lead in iter_kommo_collection(client, "/api/v4/leads", "leads", params):
        created_at = lead.get("created_at")
        if not isinstance(created_at, int):
            continue
        if not int(start_at.timestamp()) <= created_at < int(end_at.timestamp()):
            continue
        if lead.get("pipeline_id") != pipeline_id:
            continue
        yield lead


def fetch_month_leads(
    client: KommoReadOnlyClient,
    pipeline_id: int,
    month_start: date,
    next_month: date,
    tz: tzinfo,
) -> Iterator[dict[str, object]]:
    return fetch_period_leads(
        client,
        pipeline_id,
        month_start,
        next_month,
        tz,
        include_loss_reason=True,
    )


def load_monthly_snapshot(month_reference: str) -> MonthlySnapshot:
    config = KommoConfig.from_environment()
    client = KommoReadOnlyClient(config)
    account = client.get_json("/api/v4/account")
    if account is None or not isinstance(account.get("id"), int):
        raise KommoApiError("Não foi possível validar a conta Kommo.")

    pipeline = select_main_pipeline(client)
    pipeline_id = pipeline.get("id")
    if not isinstance(pipeline_id, int):
        raise KommoApiError("O funil principal retornou um ID inválido.")

    users = fetch_users(client)
    loss_reasons = fetch_loss_reasons(client)
    month_start, next_month = month_boundaries(month_reference)
    leads = list(
        fetch_month_leads(
            client, pipeline_id, month_start, next_month, report_timezone()
        )
    )
    return MonthlySnapshot(
        pipeline=pipeline,
        users=users,
        loss_reasons=loss_reasons,
        leads=leads,
    )


def load_weekly_snapshot(week_start: date) -> WeeklySnapshot:
    config = KommoConfig.from_environment()
    client = KommoReadOnlyClient(config)
    account = client.get_json("/api/v4/account")
    if account is None or not isinstance(account.get("id"), int):
        raise KommoApiError("Não foi possível validar a conta Kommo.")

    pipeline = select_main_pipeline(client)
    pipeline_id = pipeline.get("id")
    if not isinstance(pipeline_id, int):
        raise KommoApiError("O funil principal retornou um ID inválido.")

    users = fetch_users(client)
    previous_week_start = week_start - timedelta(days=7)
    current_week_end_exclusive = week_start + timedelta(days=7)
    leads = list(
        fetch_period_leads(
            client,
            pipeline_id,
            previous_week_start,
            current_week_end_exclusive,
            report_timezone(),
        )
    )
    return WeeklySnapshot(pipeline=pipeline, users=users, leads=leads)


def build_monthly_distribution_rows(
    leads: Iterable[Mapping[str, object]],
    users: Mapping[int, Mapping[str, object]],
    pipeline: Mapping[str, object],
    month_reference: str,
    extracted_at: datetime,
) -> list[dict[str, object]]:
    counts: Counter[int] = Counter()
    for lead in leads:
        responsible_id = lead.get("responsible_user_id")
        counts[responsible_id if isinstance(responsible_id, int) else 0] += 1

    total = sum(counts.values())
    rows: list[dict[str, object]] = []
    for responsible_id, quantity in sorted(
        counts.items(), key=lambda item: (-item[1], item[0])
    ):
        user = users.get(responsible_id)
        if user is None:
            responsible_name = (
                "Sem responsável"
                if responsible_id == 0
                else f"Usuário não localizado (ID {responsible_id})"
            )
            active = "desconhecido"
        else:
            responsible_name = str(user.get("name") or f"Usuário {responsible_id}")
            rights = user.get("rights")
            is_active = rights.get("is_active") if isinstance(rights, dict) else None
            active = "sim" if is_active is True else "não" if is_active is False else "desconhecido"

        rows.append(
            {
                "mes_referencia": month_reference,
                "pipeline_id": pipeline.get("id", ""),
                "pipeline_nome": pipeline.get("name", ""),
                "responsavel_id": responsible_id or "",
                "responsavel_nome": responsible_name,
                "usuario_ativo": active,
                "quantidade_leads": quantity,
                "participacao_percentual": round(quantity / total * 100, 1) if total else 0.0,
                "total_leads_mes": total,
                "data_hora_extracao": extracted_at.isoformat(timespec="seconds"),
            }
        )
    return rows


def pipeline_statuses(pipeline: Mapping[str, object]) -> list[dict[str, object]]:
    embedded = pipeline.get("_embedded")
    if not isinstance(embedded, dict):
        raise KommoApiError("O funil principal não retornou suas etapas.")
    statuses = embedded.get("statuses")
    if not isinstance(statuses, list):
        raise KommoApiError("As etapas do funil principal são inválidas.")
    return sorted(
        (status for status in statuses if isinstance(status, dict)),
        key=lambda status: (
            status.get("sort") if isinstance(status.get("sort"), int) else 0,
            status.get("id") if isinstance(status.get("id"), int) else 0,
        ),
    )


def lead_loss_reason_name(lead: Mapping[str, object]) -> str:
    embedded = lead.get("_embedded")
    if not isinstance(embedded, dict):
        return ""
    reason = embedded.get("loss_reason")
    if not isinstance(reason, dict):
        return ""
    return str(reason.get("name") or "")


def build_global_stage_rows(
    snapshot: MonthlySnapshot,
    month_reference: str,
    extracted_at: datetime,
) -> list[dict[str, object]]:
    lost_status_id = 143
    statuses = pipeline_statuses(snapshot.pipeline)
    status_names = {
        status["id"]: str(status.get("name") or f"Etapa {status['id']}")
        for status in statuses
        if isinstance(status.get("id"), int)
    }
    lost_status_name = status_names.get(lost_status_id, "Perdido")
    reason_names = {
        reason["id"]: str(reason.get("name") or f"Motivo {reason['id']}")
        for reason in snapshot.loss_reasons
        if isinstance(reason.get("id"), int)
    }

    categories: list[dict[str, object]] = []
    category_keys: set[tuple[int, int | None]] = set()

    def add_category(
        status_id: int,
        status_name: str,
        reason_id: int | None = None,
        reason_name: str = "",
    ) -> None:
        key = (status_id, reason_id if status_id == lost_status_id else None)
        if key in category_keys:
            return
        category_keys.add(key)
        if status_id == lost_status_id:
            label = (
                f"{status_name} — {reason_name}"
                if reason_name
                else f"{status_name} — indefinido/sem motivo"
            )
        else:
            label = status_name
        categories.append(
            {
                "key": key,
                "status_id": status_id,
                "status_name": status_name,
                "reason_id": reason_id,
                "reason_name": reason_name,
                "label": label,
            }
        )

    for status in statuses:
        status_id = status.get("id")
        if not isinstance(status_id, int) or status_id == lost_status_id:
            continue
        add_category(status_id, status_names[status_id])

    if lost_status_id in status_names:
        for reason in snapshot.loss_reasons:
            reason_id = reason.get("id")
            if isinstance(reason_id, int):
                add_category(
                    lost_status_id,
                    lost_status_name,
                    reason_id,
                    reason_names[reason_id],
                )
        add_category(lost_status_id, lost_status_name)

    counts: Counter[tuple[int, int, int | None]] = Counter()
    responsible_totals: Counter[int] = Counter()
    for lead in snapshot.leads:
        responsible_value = lead.get("responsible_user_id")
        responsible_id = responsible_value if isinstance(responsible_value, int) else 0
        status_value = lead.get("status_id")
        status_id = status_value if isinstance(status_value, int) else 0
        reason_value = lead.get("loss_reason_id")
        reason_id = (
            reason_value
            if status_id == lost_status_id and isinstance(reason_value, int)
            else None
        )

        key = (status_id, reason_id)
        if key not in category_keys:
            status_name = status_names.get(
                status_id, f"Etapa não localizada (ID {status_id})"
            )
            reason_name = ""
            if status_id == lost_status_id and reason_id is not None:
                reason_name = reason_names.get(reason_id) or lead_loss_reason_name(lead)
                if not reason_name:
                    reason_name = f"Motivo não localizado (ID {reason_id})"
            add_category(status_id, status_name, reason_id, reason_name)

        counts[(responsible_id, status_id, reason_id)] += 1
        responsible_totals[responsible_id] += 1

    total_general = len(snapshot.leads)
    ordered_responsibles = sorted(
        responsible_totals,
        key=lambda responsible_id: (-responsible_totals[responsible_id], responsible_id),
    )
    rows: list[dict[str, object]] = []
    for responsible_id in ordered_responsibles:
        user = snapshot.users.get(responsible_id)
        if user is None:
            responsible_name = (
                "Sem responsável"
                if responsible_id == 0
                else f"Usuário não localizado (ID {responsible_id})"
            )
        else:
            responsible_name = str(user.get("name") or f"Usuário {responsible_id}")

        total_responsible = responsible_totals[responsible_id]
        for category in categories:
            status_id, reason_id = category["key"]
            quantity = counts[(responsible_id, status_id, reason_id)]
            rows.append(
                {
                    "mes_referencia": month_reference,
                    "pipeline_id": snapshot.pipeline.get("id", ""),
                    "pipeline_nome": snapshot.pipeline.get("name", ""),
                    "responsavel_id": responsible_id or "",
                    "responsavel_nome": responsible_name,
                    "categoria_relatorio": category["label"],
                    "status_id": status_id or "",
                    "etapa_crm": category["status_name"],
                    "loss_reason_id": reason_id or "",
                    "motivo_perda_crm": category["reason_name"],
                    "quantidade_leads": quantity,
                    "total_responsavel": total_responsible,
                    "percentual_responsavel": round(
                        quantity / total_responsible * 100, 1
                    )
                    if total_responsible
                    else 0.0,
                    "total_geral": total_general,
                    "percentual_geral": round(quantity / total_general * 100, 1)
                    if total_general
                    else 0.0,
                    "data_hora_extracao": extracted_at.isoformat(timespec="seconds"),
                }
            )
    return rows


def generate_monthly_distribution(
    destination: Path,
    snapshot: MonthlySnapshot,
    month_reference: str,
    extracted_at: datetime,
) -> int:
    rows = build_monthly_distribution_rows(
        snapshot.leads,
        snapshot.users,
        snapshot.pipeline,
        month_reference,
        extracted_at,
    )
    write_csv_rows_atomic(destination, MONTHLY_DISTRIBUTION_FIELDS, rows)
    return sum(int(row["quantidade_leads"]) for row in rows)


def generate_global_stages(
    destination: Path,
    snapshot: MonthlySnapshot,
    month_reference: str,
    extracted_at: datetime,
) -> int:
    rows = build_global_stage_rows(snapshot, month_reference, extracted_at)
    consolidated_total = sum(int(row["quantidade_leads"]) for row in rows)
    if consolidated_total != len(snapshot.leads):
        raise KommoApiError(
            "A soma das etapas não corresponde ao total de leads extraídos."
        )
    write_csv_rows_atomic(destination, GLOBAL_STAGES_FIELDS, rows)
    return consolidated_total


def build_weekly_conversion_rows(
    snapshot: WeeklySnapshot,
    week_start: date,
    extracted_at: datetime,
) -> list[dict[str, object]]:
    won_status_id = 142
    previous_start = week_start - timedelta(days=7)
    previous_end = week_start - timedelta(days=1)
    current_end = week_start + timedelta(days=6)
    tz = report_timezone()

    previous_totals: Counter[int] = Counter()
    previous_won: Counter[int] = Counter()
    current_totals: Counter[int] = Counter()
    current_won: Counter[int] = Counter()

    for lead in snapshot.leads:
        created_at = lead.get("created_at")
        if not isinstance(created_at, int):
            continue
        created_date = datetime.fromtimestamp(created_at, tz=tz).date()
        responsible_value = lead.get("responsible_user_id")
        responsible_id = responsible_value if isinstance(responsible_value, int) else 0
        is_won = lead.get("status_id") == won_status_id

        if previous_start <= created_date < week_start:
            previous_totals[responsible_id] += 1
            if is_won:
                previous_won[responsible_id] += 1
        elif week_start <= created_date <= current_end:
            current_totals[responsible_id] += 1
            if is_won:
                current_won[responsible_id] += 1

    responsible_ids = set(previous_totals) | set(current_totals)
    ordered_responsibles = sorted(
        responsible_ids,
        key=lambda responsible_id: (
            -current_totals[responsible_id],
            -previous_totals[responsible_id],
            responsible_id,
        ),
    )

    rows: list[dict[str, object]] = []
    for responsible_id in ordered_responsibles:
        user = snapshot.users.get(responsible_id)
        if user is None:
            responsible_name = (
                "Sem responsável"
                if responsible_id == 0
                else f"Usuário não localizado (ID {responsible_id})"
            )
        else:
            responsible_name = str(user.get("name") or f"Usuário {responsible_id}")

        previous_total = previous_totals[responsible_id]
        current_total = current_totals[responsible_id]
        previous_rate: float | str = (
            round(previous_won[responsible_id] / previous_total * 100, 1)
            if previous_total
            else "N/C"
        )
        current_rate: float | str = (
            round(current_won[responsible_id] / current_total * 100, 1)
            if current_total
            else "N/C"
        )
        variation: float | str = (
            round(current_rate - previous_rate, 1)
            if isinstance(previous_rate, float) and isinstance(current_rate, float)
            else "N/C"
        )

        rows.append(
            {
                "pipeline_id": snapshot.pipeline.get("id", ""),
                "pipeline_nome": snapshot.pipeline.get("name", ""),
                "responsavel_id": responsible_id or "",
                "responsavel_nome": responsible_name,
                "universo": "leads_criados_na_semana",
                "semana_anterior_inicio": previous_start.isoformat(),
                "semana_anterior_fim": previous_end.isoformat(),
                "total_leads_anterior": previous_total,
                "servicos_iniciados_anterior": previous_won[responsible_id],
                "taxa_conversao_anterior": previous_rate,
                "semana_atual_inicio": week_start.isoformat(),
                "semana_atual_fim": current_end.isoformat(),
                "total_leads_atual": current_total,
                "servicos_iniciados_atual": current_won[responsible_id],
                "taxa_conversao_atual": current_rate,
                "variacao_pp": variation,
                "situacao_semana_atual": week_status(week_start, extracted_at.date()),
                "observacao_maturacao": (
                    "Taxas baseadas no estado atual dos leads; "
                    "a semana mais recente pode estar menos amadurecida."
                ),
                "data_hora_extracao": extracted_at.isoformat(timespec="seconds"),
            }
        )
    return rows


def generate_weekly_conversion(
    destination: Path,
    snapshot: WeeklySnapshot,
    week_start: date,
    extracted_at: datetime,
) -> tuple[int, int]:
    rows = build_weekly_conversion_rows(snapshot, week_start, extracted_at)
    previous_total = sum(int(row["total_leads_anterior"]) for row in rows)
    current_total = sum(int(row["total_leads_atual"]) for row in rows)
    for row in rows:
        if int(row["servicos_iniciados_anterior"]) > int(row["total_leads_anterior"]):
            raise KommoApiError("Conversões anteriores excedem a base de leads.")
        if int(row["servicos_iniciados_atual"]) > int(row["total_leads_atual"]):
            raise KommoApiError("Conversões atuais excedem a base de leads.")
    write_csv_rows_atomic(destination, WEEKLY_CONVERSION_FIELDS, rows)
    return previous_total, current_total


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Gera os dados de identificação do relatório semanal de desempenho comercial."
    )
    parser.add_argument(
        "--week-start",
        required=True,
        type=parse_week_start,
        metavar="AAAA-MM-DD",
        help="primeiro dia da semana analisada",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        load_env_file()
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"Erro ao carregar {ENV_FILE.name}: {exc}", file=sys.stderr)
        return 1

    generated_at = datetime.now(report_timezone())
    identification_destination = output_path(args.week_start)
    if confirm_overwrite(identification_destination):
        record = build_identification(args.week_start, generated_at)
        try:
            write_csv_atomic(identification_destination, record)
        except OSError as exc:
            print(f"Erro ao gravar o CSV: {exc}", file=sys.stderr)
            return 1
        print(f"CSV gerado com sucesso: {identification_destination}")
    else:
        print("Arquivo de identificação preservado.")

    month_reference = closing_month(args.week_start)
    if not month_reference:
        print("Itens 4.2 e 4.3 não aplicáveis: esta semana não fecha um mês.")
    else:
        _, next_month = month_boundaries(month_reference)
        if generated_at.date() < next_month:
            print(
                f"Itens 4.2 e 4.3 ainda não aplicáveis: "
                f"o mês {month_reference} não terminou."
            )
        else:
            monthly_destination = monthly_distribution_path(args.week_start)
            generate_distribution = confirm_overwrite(monthly_destination)
            if not generate_distribution:
                print("Arquivo de distribuição mensal preservado.")

            stages_destination = global_stages_path(args.week_start)
            generate_stages = confirm_overwrite(stages_destination)
            if not generate_stages:
                print("Arquivo de números globais por etapa preservado.")

            if generate_distribution or generate_stages:
                print(
                    f"Consultando a Kommo em modo somente leitura "
                    f"para o mês {month_reference}..."
                )
                try:
                    snapshot = load_monthly_snapshot(month_reference)
                    if generate_distribution:
                        lead_count = generate_monthly_distribution(
                            monthly_destination, snapshot, month_reference, generated_at
                        )
                        print(
                            f"CSV gerado com sucesso: {monthly_destination} "
                            f"({lead_count} leads consolidados)"
                        )
                    if generate_stages:
                        stage_lead_count = generate_global_stages(
                            stages_destination, snapshot, month_reference, generated_at
                        )
                        print(
                            f"CSV gerado com sucesso: {stages_destination} "
                            f"({stage_lead_count} leads consolidados)"
                        )
                except (KommoApiError, OSError, ValueError) as exc:
                    print(f"Erro ao gerar o consolidado mensal: {exc}", file=sys.stderr)
                    return 1

    if week_status(args.week_start, generated_at.date()) == "futura":
        print("Item 4.4 não aplicável: a semana informada é futura.")
        return 0

    conversion_destination = weekly_conversion_path(args.week_start)
    if not confirm_overwrite(conversion_destination):
        print("Arquivo de conversão por responsável preservado.")
        return 0

    print("Consultando a Kommo em modo somente leitura para as duas semanas...")
    try:
        weekly_snapshot = load_weekly_snapshot(args.week_start)
        previous_total, current_total = generate_weekly_conversion(
            conversion_destination, weekly_snapshot, args.week_start, generated_at
        )
    except (KommoApiError, OSError, ValueError) as exc:
        print(f"Erro ao gerar a conversão por responsável: {exc}", file=sys.stderr)
        return 1
    print(
        f"CSV gerado com sucesso: {conversion_destination} "
        f"({previous_total} leads anteriores; {current_total} leads atuais)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
