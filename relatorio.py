from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import tempfile
import time
import unicodedata
from calendar import monthrange
from collections import Counter
from dataclasses import asdict, dataclass, field
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
MANUAL_INPUT_ROOT = PROJECT_ROOT / "entradas_manuais"
MANUAL_RESPONSE_ROOT = MANUAL_INPUT_ROOT / "tempo_resposta"
MANUAL_ATTENDANCE_ROOT = MANUAL_INPUT_ROOT / "atendimentos"
REPORT_TIMEZONE_NAME = "America/Sao_Paulo"
RESPONSIBLE_NAME_SUFFIX = " - Advanced Mecânica Especializada"
IDENTIFICATION_FILENAME = "01_identificacao_periodo.csv"
MONTHLY_DISTRIBUTION_FILENAME = "02_distribuicao_mensal_responsavel.csv"
GLOBAL_STAGES_FILENAME = "03_numeros_globais_etapas.csv"
WEEKLY_CONVERSION_FILENAME = "04_conversao_responsavel.csv"
WEEKLY_MOVEMENT_FILENAME = "05_movimentacao_semanal.csv"
MOVEMENT_METHOD_FILENAME = "06_nota_metodologica_movimentacao.csv"
WEEKLY_NEW_LEADS_FILENAME = "07_novos_leads_semana.csv"
CONSULTANT_STAGES_FILENAME = "08_etapas_por_consultor.csv"
RESPONSE_TIME_FILENAME = "09_tempo_medio_resposta.csv"
CLOSURE_EVENTS_FILENAME = "10_eventos_fechamento.csv"
LOST_COMPOSITION_FILENAME = "11_composicao_leads_perdidos.csv"
MONTHLY_WEEKS_FILENAME = "13_analise_quantitativa_mes.csv"
MONTHLY_SUMMARY_FILENAME = "14_resumo_consolidado_mes.csv"
MONTHLY_DISTRIBUTION_FIELDS = [
    "mes_referencia",
    "universo",
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
    "universo",
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
WEEKLY_MOVEMENT_FIELDS = [
    "responsavel_id",
    "responsavel_nome",
    "unidade_contagem",
    "atendimentos_semana_anterior",
    "atendimentos_semana_atual",
    "variacao_absoluta",
    "participacao_anterior",
    "participacao_atual",
    "variacao_pp",
    "total_pares_usuario_lead_anterior",
    "total_pares_usuario_lead_atual",
    "leads_unicos_anterior",
    "leads_unicos_atual",
    "situacao_semana_atual",
    "data_hora_extracao",
]
MOVEMENT_METHOD_FIELDS = [
    "universo",
    "unidade_contagem",
    "fonte",
    "atribuicao",
    "eventos_considerados",
    "eventos_sem_usuario_excluidos_anterior",
    "eventos_sem_usuario_excluidos_atual",
    "nota_comparabilidade",
    "data_hora_extracao",
]
WEEKLY_NEW_LEADS_FIELDS = [
    "pipeline_id",
    "pipeline_nome",
    "universo",
    "responsavel_id",
    "responsavel_nome",
    "novos_leads_anterior",
    "novos_leads_atual",
    "variacao_absoluta_responsavel",
    "participacao_anterior",
    "participacao_atual",
    "variacao_pp",
    "total_novos_leads_anterior",
    "total_novos_leads_atual",
    "variacao_total_absoluta",
    "situacao_semana_atual",
    "data_hora_extracao",
]
CONSULTANT_STAGES_FIELDS = [
    "pipeline_id",
    "pipeline_nome",
    "universo",
    "responsavel_id",
    "responsavel_nome",
    "categoria_relatorio",
    "status_id",
    "etapa_crm",
    "loss_reason_id",
    "motivo_perda_crm",
    "quantidade_anterior",
    "percentual_anterior",
    "quantidade_atual",
    "percentual_atual",
    "variacao_pp",
    "total_responsavel_anterior",
    "total_responsavel_atual",
    "situacao_semana_atual",
    "data_hora_extracao",
]
RESPONSE_TIME_FIELDS = [
    "status_dado",
    "motivo_indisponibilidade",
    "responsavel_id",
    "responsavel_nome",
    "conversas_anterior",
    "tempo_medio_minutos_anterior",
    "conversas_atual",
    "tempo_medio_minutos_atual",
    "variacao_minutos",
    "definicao",
    "situacao_semana_atual",
    "data_hora_extracao",
]
LOST_COMPOSITION_FIELDS = [
    "pipeline_id",
    "pipeline_nome",
    "universo",
    "loss_reason_id",
    "motivo_perda",
    "quantidade_anterior",
    "percentual_anterior",
    "quantidade_atual",
    "percentual_atual",
    "variacao_pp",
    "total_perdidos_anterior",
    "total_perdidos_atual",
    "situacao_semana_atual",
    "data_hora_extracao",
]
MONTHLY_WEEKS_FIELDS = [
    "mes_referencia",
    "universo",
    "semana_numero",
    "periodo_inicio",
    "periodo_fim",
    "semana_parcial_no_mes",
    "novos_leads",
    "servicos_iniciados",
    "taxa_servicos_iniciados",
    "variacao_servicos_iniciados_pp",
    "agendados",
    "taxa_agendados",
    "variacao_agendados_pp",
    "perdidos",
    "taxa_perdidos",
    "variacao_perdidos_pp",
    "em_andamento",
    "taxa_em_andamento",
    "variacao_em_andamento_pp",
    "data_hora_extracao",
]
MONTHLY_SUMMARY_FIELDS = [
    "mes_referencia",
    "universo",
    "pipeline_id",
    "pipeline_nome",
    "novos_leads",
    "servicos_iniciados",
    "taxa_servicos_iniciados",
    "agendados",
    "taxa_agendados",
    "perdidos",
    "taxa_perdidos",
    "em_andamento",
    "taxa_em_andamento",
    "data_hora_extracao",
]
CLOSURE_EVENTS_FIELDS = [
    "periodo",
    "lead_id",
    "evento_id",
    "data_hora_evento",
    "status_destino_id",
    "status_destino_nome",
    "usuario_responsavel",
    "considerado_no_indicador",
    "data_hora_extracao",
]
WON_STATUS_ID = 142
LOST_STATUS_ID = 143
RESPONSIBLE_CUSTOM_FIELD_NAME = "Usuário responsável"
UNASSIGNED_RESPONSIBLE = "Sem usuário responsável"


class KommoApiError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


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
                    raise KommoApiError(
                        "Token Kommo inválido, expirado ou revogado.", 401
                    ) from exc
                if exc.code == 403:
                    raise KommoApiError(
                        "A integração não possui permissão para esta consulta.", 403
                    ) from exc
                raise KommoApiError(
                    f"A Kommo respondeu com HTTP {exc.code}.", exc.code
                ) from exc
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
    created_leads: list[dict[str, object]] = field(default_factory=list)
    outcome_events: list[dict[str, object]] = field(default_factory=list)
    lead_details: dict[int, dict[str, object]] = field(default_factory=dict)
    responsible_field_id: int | None = None


@dataclass(frozen=True)
class WeeklySnapshot:
    pipeline: dict[str, object]
    users: dict[int, dict[str, object]]
    leads: list[dict[str, object]]
    created_leads: list[dict[str, object]] = field(default_factory=list)
    loss_reasons: list[dict[str, object]] = field(default_factory=list)
    events: list[dict[str, object]] = field(default_factory=list)
    outcome_events: list[dict[str, object]] = field(default_factory=list)
    lead_details: dict[int, dict[str, object]] = field(default_factory=dict)
    responsible_field_id: int | None = None


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


def validate_week_start(week_start: date) -> None:
    if week_start.weekday() != 0:
        raise ValueError(
            "--week-start deve indicar uma segunda-feira (início da semana)."
        )


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


def applicable_month(week_start: date, generated_on: date) -> str:
    """Return the closed month applicable to this reporting week, if any.

    A monthly section is applicable only when the seven-day reporting window
    contains a month end and the report is generated on or after the first day
    of the following month. This keeps partial month-end runs weekly-only.
    """
    month_reference = closing_month(week_start)
    if not month_reference:
        return ""
    _, next_month = month_boundaries(month_reference)
    return month_reference if generated_on >= next_month else ""


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


def report_output_path(week_start: date, filename: str) -> Path:
    return OUTPUT_ROOT / str(week_start.year) / week_start.isoformat() / filename


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


def should_overwrite(path: Path, *, force: bool = False) -> bool:
    return True if force else confirm_overwrite(path)


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


def compact_responsible_name(value: object) -> str:
    name = str(value or "").strip()
    if name.endswith(RESPONSIBLE_NAME_SUFFIX):
        return name[: -len(RESPONSIBLE_NAME_SUFFIX)].rstrip()
    return name


def fetch_users(client: KommoReadOnlyClient) -> dict[int, dict[str, object]]:
    users: dict[int, dict[str, object]] = {}
    for user in iter_kommo_collection(client, "/api/v4/users", "users"):
        user_id = user.get("id")
        if isinstance(user_id, int):
            normalized_user = dict(user)
            normalized_user["name"] = compact_responsible_name(user.get("name"))
            users[user_id] = normalized_user
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


def fetch_responsible_custom_field(client: KommoReadOnlyClient) -> dict[str, object]:
    matches = [
        custom_field
        for custom_field in iter_kommo_collection(
            client, "/api/v4/leads/custom_fields", "custom_fields"
        )
        if str(custom_field.get("name") or "").strip().casefold()
        == RESPONSIBLE_CUSTOM_FIELD_NAME.casefold()
    ]
    if len(matches) != 1:
        raise KommoApiError(
            "Não foi possível identificar exatamente um campo personalizado de lead "
            f"chamado {RESPONSIBLE_CUSTOM_FIELD_NAME!r}."
        )
    field_id = matches[0].get("id")
    if not isinstance(field_id, int):
        raise KommoApiError(
            f"O campo personalizado {RESPONSIBLE_CUSTOM_FIELD_NAME!r} retornou ID inválido."
        )
    return matches[0]


def lead_custom_responsible_name(
    lead: Mapping[str, object], responsible_field_id: int | None
) -> str:
    if responsible_field_id is None:
        return UNASSIGNED_RESPONSIBLE
    custom_fields = lead.get("custom_fields_values")
    if not isinstance(custom_fields, list):
        return UNASSIGNED_RESPONSIBLE
    for custom_field in custom_fields:
        if not isinstance(custom_field, dict) or custom_field.get("field_id") != responsible_field_id:
            continue
        values = custom_field.get("values")
        if not isinstance(values, list):
            return UNASSIGNED_RESPONSIBLE
        populated = [
            str(value.get("value") or "").strip()
            for value in values
            if isinstance(value, dict) and str(value.get("value") or "").strip()
        ]
        if not populated:
            return UNASSIGNED_RESPONSIBLE
        if len(populated) != 1:
            raise KommoApiError(
                f"O lead {lead.get('id', 'sem ID')} possui mais de um valor em "
                f"{RESPONSIBLE_CUSTOM_FIELD_NAME!r}."
            )
        return populated[0]
    return UNASSIGNED_RESPONSIBLE


def fetch_period_leads(
    client: KommoReadOnlyClient,
    pipeline_id: int,
    period_start: date,
    period_end_exclusive: date,
    tz: tzinfo,
    *,
    date_field: str,
    include_loss_reason: bool = False,
) -> Iterator[dict[str, object]]:
    if date_field != "created_at":
        raise ValueError("date_field deve ser 'created_at'.")
    start_at = datetime.combine(period_start, datetime.min.time(), tzinfo=tz)
    end_at = datetime.combine(period_end_exclusive, datetime.min.time(), tzinfo=tz)
    params = {
        f"filter[{date_field}][from]": int(start_at.timestamp()),
        f"filter[{date_field}][to]": int(end_at.timestamp()) - 1,
        "filter[pipeline_id][]": pipeline_id,
        f"order[{date_field}]": "asc",
    }
    if include_loss_reason:
        params["with"] = "loss_reason"
    for lead in iter_kommo_collection(client, "/api/v4/leads", "leads", params):
        period_timestamp = lead.get(date_field)
        if not isinstance(period_timestamp, int):
            continue
        if not int(start_at.timestamp()) <= period_timestamp < int(end_at.timestamp()):
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
    *,
    date_field: str,
) -> Iterator[dict[str, object]]:
    return fetch_period_leads(
        client,
        pipeline_id,
        month_start,
        next_month,
        tz,
        date_field=date_field,
        include_loss_reason=True,
    )


def fetch_period_events(
    client: KommoReadOnlyClient,
    period_start: date,
    period_end_exclusive: date,
    tz: tzinfo,
    *,
    entity: str | None = None,
    event_type: str | None = None,
    target_pipeline_id: int | None = None,
    target_status_id: int | None = None,
) -> list[dict[str, object]]:
    start_at = datetime.combine(period_start, datetime.min.time(), tzinfo=tz)
    end_at = datetime.combine(period_end_exclusive, datetime.min.time(), tzinfo=tz)
    params: dict[str, object] = {
        "filter[created_at][from]": int(start_at.timestamp()),
        "filter[created_at][to]": int(end_at.timestamp()) - 1,
    }
    if entity:
        params["filter[entity]"] = entity
    if event_type:
        params["filter[type]"] = event_type
    if (target_pipeline_id is None) != (target_status_id is None):
        raise ValueError("pipeline e etapa de destino devem ser informados juntos.")
    if target_pipeline_id is not None and target_status_id is not None:
        params["filter[value_after][leads_statuses][0][pipeline_id]"] = target_pipeline_id
        params["filter[value_after][leads_statuses][0][status_id]"] = target_status_id
    events = list(iter_kommo_collection(client, "/api/v4/events", "events", params))
    return [
        event
        for event in events
        if isinstance(event.get("created_at"), int)
        and int(start_at.timestamp())
        <= int(event["created_at"])
        < int(end_at.timestamp())
    ]


def event_lead_status(
    event: Mapping[str, object], value_key: str = "value_after"
) -> tuple[int, int] | None:
    changes = event.get(value_key)
    if not isinstance(changes, list):
        return None
    for change in changes:
        if not isinstance(change, dict):
            continue
        lead_status = change.get("lead_status")
        if not isinstance(lead_status, dict):
            continue
        status_id = lead_status.get("id")
        pipeline_id = lead_status.get("pipeline_id")
        if isinstance(status_id, int) and isinstance(pipeline_id, int):
            return pipeline_id, status_id
    return None


def fetch_terminal_events(
    client: KommoReadOnlyClient,
    pipeline_id: int,
    period_start: date,
    period_end_exclusive: date,
    tz: tzinfo,
) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for status_id in (WON_STATUS_ID, LOST_STATUS_ID):
        candidates = fetch_period_events(
            client,
            period_start,
            period_end_exclusive,
            tz,
            entity="lead",
            event_type="lead_status_changed",
            target_pipeline_id=pipeline_id,
            target_status_id=status_id,
        )
        events.extend(
            event
            for event in candidates
            if event_lead_status(event) == (pipeline_id, status_id)
        )
    unique: dict[tuple[object, object, object], dict[str, object]] = {}
    for event in events:
        key = (event.get("id"), event.get("entity_id"), event.get("created_at"))
        unique[key] = event
    return sorted(
        unique.values(),
        key=lambda event: (
            int(event.get("created_at") or 0),
            str(event.get("id") or ""),
        ),
    )


def select_weekly_terminal_events(
    events: Iterable[Mapping[str, object]], week_start: date
) -> dict[tuple[str, int], Mapping[str, object]]:
    selected: dict[tuple[str, int], Mapping[str, object]] = {}
    for event in events:
        timestamp = event.get("created_at")
        lead_id = event.get("entity_id")
        if not isinstance(timestamp, int) or not isinstance(lead_id, int):
            continue
        bucket = weekly_bucket(timestamp, week_start)
        if bucket is None:
            continue
        key = (bucket, lead_id)
        current = selected.get(key)
        current_key = (
            int(current.get("created_at") or 0),
            str(current.get("id") or ""),
        ) if current is not None else (-1, "")
        candidate_key = (timestamp, str(event.get("id") or ""))
        if candidate_key >= current_key:
            selected[key] = event
    return selected


def select_monthly_terminal_events(
    events: Iterable[Mapping[str, object]],
) -> dict[int, Mapping[str, object]]:
    """Select the last terminal transition for each lead within the month."""
    selected: dict[int, Mapping[str, object]] = {}
    for event in events:
        timestamp = event.get("created_at")
        lead_id = event.get("entity_id")
        if not isinstance(timestamp, int) or not isinstance(lead_id, int):
            continue
        current = selected.get(lead_id)
        current_key = (
            int(current.get("created_at") or 0),
            str(current.get("id") or ""),
        ) if current is not None else (-1, "")
        candidate_key = (timestamp, str(event.get("id") or ""))
        if candidate_key >= current_key:
            selected[lead_id] = event
    return selected


def terminal_status_name(status_id: int) -> str:
    if status_id == WON_STATUS_ID:
        return "Serviço iniciado"
    if status_id == LOST_STATUS_ID:
        return "Perdido"
    return f"Etapa {status_id}"


def fetch_leads_by_ids(
    client: KommoReadOnlyClient, lead_ids: Iterable[int]
) -> dict[int, dict[str, object]]:
    unique_ids = sorted(set(lead_ids))
    leads: dict[int, dict[str, object]] = {}
    for offset in range(0, len(unique_ids), 250):
        batch = unique_ids[offset : offset + 250]
        if not batch:
            continue
        payload = client.get_json(
            "/api/v4/leads", {"filter[id][]": batch, "limit": 250}
        )
        for lead in embedded_collection(payload, "leads"):
            lead_id = lead.get("id")
            if isinstance(lead_id, int):
                leads[lead_id] = lead
    return leads


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
    responsible_field = fetch_responsible_custom_field(client)
    responsible_field_id = int(responsible_field["id"])
    month_start, next_month = month_boundaries(month_reference)
    outcome_events = fetch_terminal_events(
        client, pipeline_id, month_start, next_month, report_timezone()
    )
    outcome_lead_ids = [
        int(event["entity_id"])
        for event in outcome_events
        if isinstance(event.get("entity_id"), int)
    ]
    lead_details = fetch_leads_by_ids(client, outcome_lead_ids)
    leads = list(lead_details.values())
    created_leads = list(
        fetch_month_leads(
            client,
            pipeline_id,
            month_start,
            next_month,
            report_timezone(),
            date_field="created_at",
        )
    )
    return MonthlySnapshot(
        pipeline=pipeline,
        users=users,
        loss_reasons=loss_reasons,
        leads=leads,
        created_leads=created_leads,
        outcome_events=outcome_events,
        lead_details=lead_details,
        responsible_field_id=responsible_field_id,
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
    loss_reasons = fetch_loss_reasons(client)
    responsible_field = fetch_responsible_custom_field(client)
    responsible_field_id = int(responsible_field["id"])
    previous_week_start = week_start - timedelta(days=7)
    current_week_end_exclusive = week_start + timedelta(days=7)
    outcome_events = fetch_terminal_events(
        client,
        pipeline_id,
        previous_week_start,
        current_week_end_exclusive,
        report_timezone(),
    )
    created_leads = list(
        fetch_period_leads(
            client,
            pipeline_id,
            previous_week_start,
            current_week_end_exclusive,
            report_timezone(),
            date_field="created_at",
            include_loss_reason=True,
        )
    )
    events = fetch_period_events(
        client,
        previous_week_start,
        current_week_end_exclusive,
        report_timezone(),
        entity="lead",
    )
    event_lead_ids = [
        event_id
        for event in [*events, *outcome_events]
        for event_id in [event.get("entity_id")]
        if isinstance(event_id, int)
    ]
    event_leads = fetch_leads_by_ids(client, event_lead_ids)
    for lead in created_leads:
        lead_id = lead.get("id")
        if isinstance(lead_id, int):
            event_leads.setdefault(lead_id, lead)
    main_pipeline_events = [
        event
        for event in events
        if isinstance(event.get("entity_id"), int)
        and event_leads.get(int(event["entity_id"]), {}).get("pipeline_id")
        == pipeline_id
    ]
    return WeeklySnapshot(
        pipeline=pipeline,
        users=users,
        leads=[
            event_leads[lead_id]
            for lead_id in sorted(
                {
                    int(event["entity_id"])
                    for event in outcome_events
                    if isinstance(event.get("entity_id"), int)
                    and int(event["entity_id"]) in event_leads
                }
            )
        ],
        created_leads=created_leads,
        loss_reasons=loss_reasons,
        events=main_pipeline_events,
        outcome_events=outcome_events,
        lead_details=event_leads,
        responsible_field_id=responsible_field_id,
    )


def monthly_terminal_records(
    snapshot: MonthlySnapshot,
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for lead_id, event in sorted(
        select_monthly_terminal_events(snapshot.outcome_events).items(),
        key=lambda item: (int(item[1].get("created_at") or 0), item[0]),
    ):
        lead = snapshot.lead_details.get(lead_id)
        if lead is None:
            raise KommoApiError(
                f"O lead {lead_id} referenciado por um evento de fechamento não foi retornado."
            )
        target = event_lead_status(event)
        if target is None or target[1] not in {WON_STATUS_ID, LOST_STATUS_ID}:
            continue
        records.append(
            {
                "lead_id": lead_id,
                "event": event,
                "lead": lead,
                "status_id": target[1],
                "responsavel_nome": lead_custom_responsible_name(
                    lead, snapshot.responsible_field_id
                ),
            }
        )
    return records


def build_monthly_distribution_rows(
    snapshot: MonthlySnapshot,
    month_reference: str,
    extracted_at: datetime,
) -> list[dict[str, object]]:
    counts: Counter[str] = Counter(
        str(record["responsavel_nome"])
        for record in monthly_terminal_records(snapshot)
    )

    total = sum(counts.values())
    rows: list[dict[str, object]] = []
    for responsible_name, quantity in sorted(
        counts.items(), key=lambda item: (-item[1], item[0].casefold())
    ):
        rows.append(
            {
                "mes_referencia": month_reference,
                "universo": "leads_com_ultima_transicao_terminal_no_mes",
                "pipeline_id": snapshot.pipeline.get("id", ""),
                "pipeline_nome": snapshot.pipeline.get("name", ""),
                "responsavel_id": "",
                "responsavel_nome": responsible_name,
                "usuario_ativo": "não aplicável",
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
        if status_id != WON_STATUS_ID:
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

    counts: Counter[tuple[str, int, int | None]] = Counter()
    responsible_totals: Counter[str] = Counter()
    for record in monthly_terminal_records(snapshot):
        lead = record["lead"]
        responsible_name = str(record["responsavel_nome"])
        status_id = int(record["status_id"])
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

        counts[(responsible_name, status_id, reason_id)] += 1
        responsible_totals[responsible_name] += 1

    total_general = sum(responsible_totals.values())
    ordered_responsibles = sorted(
        responsible_totals,
        key=lambda responsible_name: (
            -responsible_totals[responsible_name],
            responsible_name.casefold(),
        ),
    )
    rows: list[dict[str, object]] = []
    for responsible_name in ordered_responsibles:
        total_responsible = responsible_totals[responsible_name]
        for category in categories:
            status_id, reason_id = category["key"]
            quantity = counts[(responsible_name, status_id, reason_id)]
            rows.append(
                {
                    "mes_referencia": month_reference,
                    "universo": "leads_com_ultima_transicao_terminal_no_mes",
                    "pipeline_id": snapshot.pipeline.get("id", ""),
                    "pipeline_nome": snapshot.pipeline.get("name", ""),
                    "responsavel_id": "",
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
        snapshot,
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
    if consolidated_total != len(monthly_terminal_records(snapshot)):
        raise KommoApiError(
            "A soma das etapas não corresponde ao total de leads extraídos."
        )
    write_csv_rows_atomic(destination, GLOBAL_STAGES_FIELDS, rows)
    return consolidated_total


def weekly_terminal_records(
    snapshot: WeeklySnapshot, week_start: date
) -> list[dict[str, object]]:
    selected = select_weekly_terminal_events(snapshot.outcome_events, week_start)
    records: list[dict[str, object]] = []
    for (bucket, lead_id), event in sorted(
        selected.items(),
        key=lambda item: (
            item[0][0],
            int(item[1].get("created_at") or 0),
            item[0][1],
        ),
    ):
        lead = snapshot.lead_details.get(lead_id)
        if lead is None:
            raise KommoApiError(
                f"O lead {lead_id} referenciado por um evento de fechamento não foi retornado."
            )
        target = event_lead_status(event)
        if target is None or target[1] not in {WON_STATUS_ID, LOST_STATUS_ID}:
            continue
        records.append(
            {
                "bucket": bucket,
                "lead_id": lead_id,
                "event": event,
                "lead": lead,
                "status_id": target[1],
                "responsavel_nome": lead_custom_responsible_name(
                    lead, snapshot.responsible_field_id
                ),
            }
        )
    return records


def build_closure_event_rows(
    snapshot: WeeklySnapshot,
    week_start: date,
    extracted_at: datetime,
) -> list[dict[str, object]]:
    selected = select_weekly_terminal_events(snapshot.outcome_events, week_start)
    rows: list[dict[str, object]] = []
    for event in snapshot.outcome_events:
        timestamp = event.get("created_at")
        lead_id = event.get("entity_id")
        target = event_lead_status(event)
        if (
            not isinstance(timestamp, int)
            or not isinstance(lead_id, int)
            or target is None
        ):
            continue
        bucket = weekly_bucket(timestamp, week_start)
        if bucket is None:
            continue
        lead = snapshot.lead_details.get(lead_id, {})
        rows.append(
            {
                "periodo": bucket,
                "lead_id": lead_id,
                "evento_id": event.get("id", ""),
                "data_hora_evento": datetime.fromtimestamp(
                    timestamp, tz=report_timezone()
                ).isoformat(timespec="seconds"),
                "status_destino_id": target[1],
                "status_destino_nome": terminal_status_name(target[1]),
                "usuario_responsavel": lead_custom_responsible_name(
                    lead, snapshot.responsible_field_id
                ),
                "considerado_no_indicador": (
                    "sim" if selected.get((bucket, lead_id)) == event else "não"
                ),
                "data_hora_extracao": extracted_at.isoformat(timespec="seconds"),
            }
        )
    return rows


def build_weekly_conversion_rows(
    snapshot: WeeklySnapshot,
    week_start: date,
    extracted_at: datetime,
) -> list[dict[str, object]]:
    previous_start = week_start - timedelta(days=7)
    previous_end = week_start - timedelta(days=1)
    current_end = week_start + timedelta(days=6)
    totals: Counter[tuple[str, str]] = Counter()
    won: Counter[tuple[str, str]] = Counter()
    for record in weekly_terminal_records(snapshot, week_start):
        bucket = str(record["bucket"])
        responsible_name = str(record["responsavel_nome"])
        totals[(bucket, responsible_name)] += 1
        if record["status_id"] == WON_STATUS_ID:
            won[(bucket, responsible_name)] += 1

    responsible_names = {
        responsible_name for _, responsible_name in totals
    }
    ordered_responsibles = sorted(
        responsible_names,
        key=lambda responsible_name: (
            -totals[("atual", responsible_name)],
            -totals[("anterior", responsible_name)],
            responsible_name.casefold(),
        ),
    )

    rows: list[dict[str, object]] = []
    for responsible_name in ordered_responsibles:
        previous_total = totals[("anterior", responsible_name)]
        current_total = totals[("atual", responsible_name)]
        previous_rate: float | str = (
            round(won[("anterior", responsible_name)] / previous_total * 100, 1)
            if previous_total
            else "N/C"
        )
        current_rate: float | str = (
            round(won[("atual", responsible_name)] / current_total * 100, 1)
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
                "responsavel_id": "",
                "responsavel_nome": responsible_name,
                "universo": "leads_com_ultima_transicao_terminal_na_semana",
                "semana_anterior_inicio": previous_start.isoformat(),
                "semana_anterior_fim": previous_end.isoformat(),
                "total_leads_anterior": previous_total,
                "servicos_iniciados_anterior": won[("anterior", responsible_name)],
                "taxa_conversao_anterior": previous_rate,
                "semana_atual_inicio": week_start.isoformat(),
                "semana_atual_fim": current_end.isoformat(),
                "total_leads_atual": current_total,
                "servicos_iniciados_atual": won[("atual", responsible_name)],
                "taxa_conversao_atual": current_rate,
                "variacao_pp": variation,
                "situacao_semana_atual": week_status(week_start, extracted_at.date()),
                "observacao_maturacao": (
                    "Cada lead é atribuído à última entrada em Serviço iniciado ou "
                    "Perdido dentro da semana; o responsável vem exclusivamente do "
                    f"campo personalizado {RESPONSIBLE_CUSTOM_FIELD_NAME!r}."
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


def display_user_name(
    users: Mapping[int, Mapping[str, object]], responsible_id: int
) -> str:
    user = users.get(responsible_id)
    if user is not None:
        return compact_responsible_name(
            user.get("name") or f"Usuário {responsible_id}"
        )
    if responsible_id == 0:
        return "Sem responsável"
    return f"Usuário não localizado (ID {responsible_id})"


def weekly_bucket(timestamp: int, week_start: date) -> str | None:
    event_date = datetime.fromtimestamp(timestamp, tz=report_timezone()).date()
    if week_start - timedelta(days=7) <= event_date < week_start:
        return "anterior"
    if week_start <= event_date < week_start + timedelta(days=7):
        return "atual"
    return None


def build_weekly_movement_rows(
    snapshot: WeeklySnapshot,
    week_start: date,
    extracted_at: datetime,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    pairs: dict[str, set[tuple[str, int]]] = {"anterior": set(), "atual": set()}
    unique_leads: dict[str, set[int]] = {"anterior": set(), "atual": set()}
    excluded_events = {"anterior": 0, "atual": 0}
    event_types: set[str] = set()

    for event in snapshot.events:
        created_at = event.get("created_at")
        entity_id = event.get("entity_id")
        if not isinstance(created_at, int) or not isinstance(entity_id, int):
            continue
        bucket = weekly_bucket(created_at, week_start)
        if bucket is None:
            continue
        event_type = event.get("type")
        if isinstance(event_type, str):
            event_types.add(event_type)
        lead = snapshot.lead_details.get(entity_id)
        if lead is None:
            excluded_events[bucket] += 1
            continue
        responsible_name = lead_custom_responsible_name(
            lead, snapshot.responsible_field_id
        )
        pairs[bucket].add((responsible_name, entity_id))
        unique_leads[bucket].add(entity_id)

    previous_counts: Counter[str] = Counter(name for name, _ in pairs["anterior"])
    current_counts: Counter[str] = Counter(name for name, _ in pairs["atual"])
    previous_total = sum(previous_counts.values())
    current_total = sum(current_counts.values())
    responsible_names = set(previous_counts) | set(current_counts)
    rows: list[dict[str, object]] = []
    for responsible_name in sorted(
        responsible_names,
        key=lambda value: (-current_counts[value], -previous_counts[value], value.casefold()),
    ):
        previous_quantity = previous_counts[responsible_name]
        current_quantity = current_counts[responsible_name]
        previous_share: float | str = (
            round(previous_quantity / previous_total * 100, 1)
            if previous_total
            else "N/C"
        )
        current_share: float | str = (
            round(current_quantity / current_total * 100, 1)
            if current_total
            else "N/C"
        )
        variation: float | str = (
            round(current_share - previous_share, 1)
            if isinstance(previous_share, float) and isinstance(current_share, float)
            else "N/C"
        )
        rows.append(
            {
                "responsavel_id": "",
                "responsavel_nome": responsible_name,
                "unidade_contagem": "par_responsavel_lead_distinto",
                "atendimentos_semana_anterior": previous_quantity,
                "atendimentos_semana_atual": current_quantity,
                "variacao_absoluta": current_quantity - previous_quantity,
                "participacao_anterior": previous_share,
                "participacao_atual": current_share,
                "variacao_pp": variation,
                "total_pares_usuario_lead_anterior": previous_total,
                "total_pares_usuario_lead_atual": current_total,
                "leads_unicos_anterior": len(unique_leads["anterior"]),
                "leads_unicos_atual": len(unique_leads["atual"]),
                "situacao_semana_atual": week_status(week_start, extracted_at.date()),
                "data_hora_extracao": extracted_at.isoformat(timespec="seconds"),
            }
        )

    method_row = {
        "universo": "leads atualmente no funil principal com evento no período",
        "unidade_contagem": "um lead por responsável por semana, mesmo com vários eventos",
        "fonte": "GET /api/v4/events com entity=lead",
        "atribuicao": f"campo personalizado do lead {RESPONSIBLE_CUSTOM_FIELD_NAME!r}",
        "eventos_considerados": "|".join(sorted(event_types)),
        "eventos_sem_usuario_excluidos_anterior": excluded_events["anterior"],
        "eventos_sem_usuario_excluidos_atual": excluded_events["atual"],
        "nota_comparabilidade": (
            "O usuário que criou ou movimentou o evento não é usado na atribuição; "
            "leads não retornados pela extração são excluídos."
        ),
        "data_hora_extracao": extracted_at.isoformat(timespec="seconds"),
    }
    return rows, method_row


def build_weekly_new_leads_rows(
    snapshot: WeeklySnapshot,
    week_start: date,
    extracted_at: datetime,
) -> list[dict[str, object]]:
    previous_counts: Counter[str] = Counter()
    current_counts: Counter[str] = Counter()
    for lead in snapshot.created_leads:
        created_at = lead.get("created_at")
        if not isinstance(created_at, int):
            continue
        bucket = weekly_bucket(created_at, week_start)
        responsible_name = lead_custom_responsible_name(
            lead, snapshot.responsible_field_id
        )
        if bucket == "anterior":
            previous_counts[responsible_name] += 1
        elif bucket == "atual":
            current_counts[responsible_name] += 1

    previous_total = sum(previous_counts.values())
    current_total = sum(current_counts.values())
    rows: list[dict[str, object]] = []
    for responsible_name in sorted(
        set(previous_counts) | set(current_counts),
        key=lambda value: (-current_counts[value], -previous_counts[value], value.casefold()),
    ):
        previous_quantity = previous_counts[responsible_name]
        current_quantity = current_counts[responsible_name]
        previous_share: float | str = (
            round(previous_quantity / previous_total * 100, 1)
            if previous_total
            else "N/C"
        )
        current_share: float | str = (
            round(current_quantity / current_total * 100, 1)
            if current_total
            else "N/C"
        )
        rows.append(
            {
                "pipeline_id": snapshot.pipeline.get("id", ""),
                "pipeline_nome": snapshot.pipeline.get("name", ""),
                "universo": "leads_criados_no_periodo",
                "responsavel_id": "",
                "responsavel_nome": responsible_name,
                "novos_leads_anterior": previous_quantity,
                "novos_leads_atual": current_quantity,
                "variacao_absoluta_responsavel": current_quantity - previous_quantity,
                "participacao_anterior": previous_share,
                "participacao_atual": current_share,
                "variacao_pp": (
                    round(current_share - previous_share, 1)
                    if isinstance(previous_share, float)
                    and isinstance(current_share, float)
                    else "N/C"
                ),
                "total_novos_leads_anterior": previous_total,
                "total_novos_leads_atual": current_total,
                "variacao_total_absoluta": current_total - previous_total,
                "situacao_semana_atual": week_status(week_start, extracted_at.date()),
                "data_hora_extracao": extracted_at.isoformat(timespec="seconds"),
            }
        )
    return rows


def build_dynamic_stage_categories(
    pipeline: Mapping[str, object],
    loss_reasons: Iterable[Mapping[str, object]],
    leads: Iterable[Mapping[str, object]],
) -> list[dict[str, object]]:
    lost_status_id = 143
    statuses = pipeline_statuses(pipeline)
    status_names = {
        int(status["id"]): str(status.get("name") or f"Etapa {status['id']}")
        for status in statuses
        if isinstance(status.get("id"), int)
    }
    lost_name = status_names.get(lost_status_id, "Perdido")
    ordered_reasons = list(loss_reasons)
    reason_names = {
        int(reason["id"]): str(reason.get("name") or f"Motivo {reason['id']}")
        for reason in ordered_reasons
        if isinstance(reason.get("id"), int)
    }
    categories: list[dict[str, object]] = []
    keys: set[tuple[int, int | None]] = set()

    def add(status_id: int, reason_id: int | None = None, reason_name: str = "") -> None:
        key = (status_id, reason_id if status_id == lost_status_id else None)
        if key in keys:
            return
        keys.add(key)
        status_name = status_names.get(
            status_id, f"Etapa não localizada (ID {status_id})"
        )
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
        if isinstance(status_id, int) and status_id != lost_status_id:
            add(status_id)
    if lost_status_id in status_names:
        for reason in ordered_reasons:
            reason_id = reason.get("id")
            if isinstance(reason_id, int):
                add(lost_status_id, reason_id, reason_names[reason_id])
        add(lost_status_id)

    for lead in leads:
        status_value = lead.get("status_id")
        status_id = status_value if isinstance(status_value, int) else 0
        reason_value = lead.get("loss_reason_id")
        reason_id = (
            reason_value
            if status_id == lost_status_id and isinstance(reason_value, int)
            else None
        )
        key = (status_id, reason_id)
        if key in keys:
            continue
        reason_name = ""
        if status_id == lost_status_id and reason_id is not None:
            reason_name = reason_names.get(reason_id) or lead_loss_reason_name(lead)
            if not reason_name:
                reason_name = f"Motivo não localizado (ID {reason_id})"
        add(status_id, reason_id, reason_name)
    return categories


def build_consultant_stage_rows(
    snapshot: WeeklySnapshot,
    week_start: date,
    extracted_at: datetime,
) -> list[dict[str, object]]:
    categories = [
        category
        for category in build_dynamic_stage_categories(
            snapshot.pipeline, snapshot.loss_reasons, snapshot.leads
        )
        if category["status_id"] in {WON_STATUS_ID, LOST_STATUS_ID}
    ]
    counts: Counter[tuple[str, str, int, int | None]] = Counter()
    totals: Counter[tuple[str, str]] = Counter()
    for record in weekly_terminal_records(snapshot, week_start):
        bucket = str(record["bucket"])
        responsible_name = str(record["responsavel_nome"])
        status_id = int(record["status_id"])
        lead = record["lead"]
        reason_value = lead.get("loss_reason_id") if isinstance(lead, dict) else None
        reason_id = (
            reason_value
            if status_id == LOST_STATUS_ID and isinstance(reason_value, int)
            else None
        )
        counts[(bucket, responsible_name, status_id, reason_id)] += 1
        totals[(bucket, responsible_name)] += 1

    responsible_names = {responsible_name for _, responsible_name in totals}
    rows: list[dict[str, object]] = []
    for responsible_name in sorted(
        responsible_names,
        key=lambda value: (
            -totals[("atual", value)],
            -totals[("anterior", value)],
            value.casefold(),
        ),
    ):
        previous_total = totals[("anterior", responsible_name)]
        current_total = totals[("atual", responsible_name)]
        for category in categories:
            status_id, reason_id = category["key"]
            previous_quantity = counts[
                ("anterior", responsible_name, status_id, reason_id)
            ]
            current_quantity = counts[("atual", responsible_name, status_id, reason_id)]
            previous_rate: float | str = (
                round(previous_quantity / previous_total * 100, 1)
                if previous_total
                else "N/C"
            )
            current_rate: float | str = (
                round(current_quantity / current_total * 100, 1)
                if current_total
                else "N/C"
            )
            rows.append(
                {
                    "pipeline_id": snapshot.pipeline.get("id", ""),
                    "pipeline_nome": snapshot.pipeline.get("name", ""),
                    "universo": "leads_com_ultima_transicao_terminal_no_periodo",
                    "responsavel_id": "",
                    "responsavel_nome": responsible_name,
                    "categoria_relatorio": category["label"],
                    "status_id": status_id or "",
                    "etapa_crm": category["status_name"],
                    "loss_reason_id": reason_id or "",
                    "motivo_perda_crm": category["reason_name"],
                    "quantidade_anterior": previous_quantity,
                    "percentual_anterior": previous_rate,
                    "quantidade_atual": current_quantity,
                    "percentual_atual": current_rate,
                    "variacao_pp": (
                        round(current_rate - previous_rate, 1)
                        if isinstance(previous_rate, float)
                        and isinstance(current_rate, float)
                        else "N/C"
                    ),
                    "total_responsavel_anterior": previous_total,
                    "total_responsavel_atual": current_total,
                    "situacao_semana_atual": week_status(
                        week_start, extracted_at.date()
                    ),
                    "data_hora_extracao": extracted_at.isoformat(timespec="seconds"),
                }
            )
    return rows


def build_lost_composition_rows(
    snapshot: WeeklySnapshot,
    week_start: date,
    extracted_at: datetime,
) -> list[dict[str, object]]:
    categories = [
        category
        for category in build_dynamic_stage_categories(
            snapshot.pipeline, snapshot.loss_reasons, snapshot.leads
        )
        if category["status_id"] == LOST_STATUS_ID
    ]
    counts: Counter[tuple[str, int | None]] = Counter()
    totals: Counter[str] = Counter()
    for record in weekly_terminal_records(snapshot, week_start):
        if record["status_id"] != LOST_STATUS_ID:
            continue
        bucket = str(record["bucket"])
        lead = record["lead"]
        if not isinstance(lead, dict):
            continue
        reason_value = lead.get("loss_reason_id")
        reason_id = reason_value if isinstance(reason_value, int) else None
        counts[(bucket, reason_id)] += 1
        totals[bucket] += 1

    rows: list[dict[str, object]] = []
    for category in categories:
        reason_id = category["reason_id"]
        previous_quantity = counts[("anterior", reason_id)]
        current_quantity = counts[("atual", reason_id)]
        previous_rate: float | str = (
            round(previous_quantity / totals["anterior"] * 100, 1)
            if totals["anterior"]
            else "N/C"
        )
        current_rate: float | str = (
            round(current_quantity / totals["atual"] * 100, 1)
            if totals["atual"]
            else "N/C"
        )
        rows.append(
            {
                "pipeline_id": snapshot.pipeline.get("id", ""),
                "pipeline_nome": snapshot.pipeline.get("name", ""),
                "universo": "leads_com_ultima_transicao_terminal_perdido_no_periodo",
                "loss_reason_id": reason_id or "",
                "motivo_perda": category["label"],
                "quantidade_anterior": previous_quantity,
                "percentual_anterior": previous_rate,
                "quantidade_atual": current_quantity,
                "percentual_atual": current_rate,
                "variacao_pp": (
                    round(current_rate - previous_rate, 1)
                    if isinstance(previous_rate, float)
                    and isinstance(current_rate, float)
                    else "N/C"
                ),
                "total_perdidos_anterior": totals["anterior"],
                "total_perdidos_atual": totals["atual"],
                "situacao_semana_atual": week_status(week_start, extracted_at.date()),
                "data_hora_extracao": extracted_at.isoformat(timespec="seconds"),
            }
        )
    return rows


def build_response_time_rows(
    week_start: date,
    extracted_at: datetime,
) -> list[dict[str, object]]:
    definition = (
        "Minutos entre a primeira mensagem recebida e a primeira resposta "
        "de um usuário interno na conversa."
    )
    config = KommoConfig.from_environment()
    client = KommoReadOnlyClient(config)
    account = client.get_json("/api/v4/account")
    if account is None or not isinstance(account.get("id"), int):
        raise KommoApiError("Não foi possível validar a conta Kommo.")
    users = fetch_users(client)
    talk_events = fetch_period_events(
        client,
        week_start - timedelta(days=7),
        week_start + timedelta(days=7),
        report_timezone(),
        event_type="talk_created",
    )

    if not talk_events:
        return [
            {
                "status_dado": "sem_conversas_no_periodo",
                "motivo_indisponibilidade": "Nenhuma conversa iniciada nas duas semanas.",
                "responsavel_id": "",
                "responsavel_nome": "",
                "conversas_anterior": 0,
                "tempo_medio_minutos_anterior": "N/C",
                "conversas_atual": 0,
                "tempo_medio_minutos_atual": "N/C",
                "variacao_minutos": "N/C",
                "definicao": definition,
                "situacao_semana_atual": week_status(
                    week_start, extracted_at.date()
                ),
                "data_hora_extracao": extracted_at.isoformat(timespec="seconds"),
            }
        ]

    response_minutes: dict[str, dict[int, list[float]]] = {
        "anterior": {},
        "atual": {},
    }
    try:
        for event in talk_events:
            talk_id = event.get("entity_id")
            if not isinstance(talk_id, int):
                continue
            messages = list(
                iter_kommo_collection(
                    client,
                    f"/api/v4/talks/{talk_id}/messages",
                    "messages",
                )
            )
            messages.sort(
                key=lambda message: (
                    message.get("created_at")
                    if isinstance(message.get("created_at"), int)
                    else 0
                )
            )
            first_incoming = next(
                (
                    message
                    for message in messages
                    if message.get("type") == "incoming"
                    and isinstance(message.get("created_at"), int)
                ),
                None,
            )
            if first_incoming is None:
                continue
            incoming_at = int(first_incoming["created_at"])
            first_response = None
            for message in messages:
                message_at = message.get("created_at")
                author = message.get("author")
                if (
                    message.get("type") == "outgoing"
                    and isinstance(message_at, int)
                    and message_at >= incoming_at
                    and isinstance(author, dict)
                    and author.get("type") == "internal"
                    and isinstance(author.get("user_id"), int)
                ):
                    first_response = message
                    break
            if first_response is None:
                continue
            bucket = weekly_bucket(incoming_at, week_start)
            if bucket is None:
                continue
            author = first_response["author"]
            user_id = int(author["user_id"])
            minutes = (int(first_response["created_at"]) - incoming_at) / 60
            response_minutes[bucket].setdefault(user_id, []).append(minutes)
    except KommoApiError as exc:
        if exc.status_code != 403:
            raise
        return [
            {
                "status_dado": "indisponivel",
                "motivo_indisponibilidade": (
                    "A integração não possui o escopo External chat history."
                ),
                "responsavel_id": "",
                "responsavel_nome": "",
                "conversas_anterior": "N/C",
                "tempo_medio_minutos_anterior": "N/C",
                "conversas_atual": "N/C",
                "tempo_medio_minutos_atual": "N/C",
                "variacao_minutos": "N/C",
                "definicao": definition,
                "situacao_semana_atual": week_status(
                    week_start, extracted_at.date()
                ),
                "data_hora_extracao": extracted_at.isoformat(timespec="seconds"),
            }
        ]

    user_ids = set(response_minutes["anterior"]) | set(response_minutes["atual"])
    if not user_ids:
        return [
            {
                "status_dado": "disponivel_sem_respostas_validas",
                "motivo_indisponibilidade": (
                    "Não foi encontrado par entrada/resposta interna nas conversas."
                ),
                "responsavel_id": "",
                "responsavel_nome": "",
                "conversas_anterior": 0,
                "tempo_medio_minutos_anterior": "N/C",
                "conversas_atual": 0,
                "tempo_medio_minutos_atual": "N/C",
                "variacao_minutos": "N/C",
                "definicao": definition,
                "situacao_semana_atual": week_status(
                    week_start, extracted_at.date()
                ),
                "data_hora_extracao": extracted_at.isoformat(timespec="seconds"),
            }
        ]

    rows: list[dict[str, object]] = []
    for user_id in sorted(user_ids):
        previous_values = response_minutes["anterior"].get(user_id, [])
        current_values = response_minutes["atual"].get(user_id, [])
        previous_average: float | str = (
            round(sum(previous_values) / len(previous_values), 1)
            if previous_values
            else "N/C"
        )
        current_average: float | str = (
            round(sum(current_values) / len(current_values), 1)
            if current_values
            else "N/C"
        )
        rows.append(
            {
                "status_dado": "disponivel",
                "motivo_indisponibilidade": "",
                "responsavel_id": user_id,
                "responsavel_nome": display_user_name(users, user_id),
                "conversas_anterior": len(previous_values),
                "tempo_medio_minutos_anterior": previous_average,
                "conversas_atual": len(current_values),
                "tempo_medio_minutos_atual": current_average,
                "variacao_minutos": (
                    round(current_average - previous_average, 1)
                    if isinstance(previous_average, float)
                    and isinstance(current_average, float)
                    else "N/C"
                ),
                "definicao": definition,
                "situacao_semana_atual": week_status(
                    week_start, extracted_at.date()
                ),
                "data_hora_extracao": extracted_at.isoformat(timespec="seconds"),
            }
        )
    return rows


def manual_response_time_path(week_start: date) -> Path:
    return MANUAL_RESPONSE_ROOT / week_start.isoformat() / "tempo_resposta.csv"


def _manual_number(value: object, *, field: str, allow_na: bool = True) -> float | str:
    text = str(value or "").strip()
    if allow_na and text.casefold() in {"", "n/c", "nc", "n/a", "na"}:
        return "N/C"
    try:
        number = float(text.replace(".", "").replace(",", ".")) if "," in text else float(text)
    except ValueError as exc:
        raise ValueError(f"Valor inválido em {field}: {text!r}.") from exc
    if number < 0:
        raise ValueError(f"{field} não pode ser negativo.")
    return round(number, 1)


def _manual_integer(value: object, *, field: str) -> int | str:
    number = _manual_number(value, field=field)
    if number == "N/C":
        return number
    if not float(number).is_integer():
        raise ValueError(f"{field} deve ser um número inteiro.")
    return int(number)


def build_manual_response_time_rows(
    source_path: Path,
    week_start: date,
    extracted_at: datetime,
) -> list[dict[str, object]]:
    """Normalize the manually supplied response-time CSV to the report schema."""
    if not source_path.is_file():
        raise ValueError(f"Arquivo manual não encontrado: {source_path}")
    text = source_path.read_text(encoding="utf-8-sig")
    if not text.strip():
        raise ValueError(f"O arquivo manual está vazio: {source_path}")
    first_line = text.splitlines()[0]
    delimiter = ";" if first_line.count(";") > first_line.count(",") else ","
    reader = csv.DictReader(text.splitlines(), delimiter=delimiter)
    required = {
        "responsavel_nome",
        "conversas_anterior",
        "tempo_medio_minutos_anterior",
        "conversas_atual",
        "tempo_medio_minutos_atual",
    }
    missing = required - set(reader.fieldnames or [])
    if missing:
        raise ValueError(
            "Colunas ausentes no tempo de resposta manual: " + ", ".join(sorted(missing))
        )

    definition = (
        "Minutos entre a primeira mensagem recebida e a primeira resposta "
        "de um usuário interno na conversa. Fonte informada manualmente."
    )
    seen: set[str] = set()
    rows: list[dict[str, object]] = []
    for line_number, source in enumerate(reader, 2):
        responsible = str(source.get("responsavel_nome") or "").strip()
        if not responsible:
            raise ValueError(f"Responsável vazio na linha {line_number}.")
        key = responsible.casefold()
        if key in seen:
            raise ValueError(f"Responsável duplicado no arquivo manual: {responsible}.")
        seen.add(key)
        previous_minutes = _manual_number(
            source.get("tempo_medio_minutos_anterior"),
            field=f"tempo_medio_minutos_anterior (linha {line_number})",
        )
        current_minutes = _manual_number(
            source.get("tempo_medio_minutos_atual"),
            field=f"tempo_medio_minutos_atual (linha {line_number})",
        )
        if previous_minutes == "N/C" and current_minutes == "N/C":
            raise ValueError(
                f"A linha {line_number} precisa ter ao menos um tempo médio mensurável."
            )
        variation: float | str = "N/C"
        if isinstance(previous_minutes, float) and isinstance(current_minutes, float):
            variation = round(current_minutes - previous_minutes, 1)
        rows.append(
            {
                "status_dado": "disponivel_manual",
                "motivo_indisponibilidade": "",
                "responsavel_id": "",
                "responsavel_nome": responsible,
                "conversas_anterior": _manual_integer(
                    source.get("conversas_anterior"),
                    field=f"conversas_anterior (linha {line_number})",
                ),
                "tempo_medio_minutos_anterior": previous_minutes,
                "conversas_atual": _manual_integer(
                    source.get("conversas_atual"),
                    field=f"conversas_atual (linha {line_number})",
                ),
                "tempo_medio_minutos_atual": current_minutes,
                "variacao_minutos": variation,
                "definicao": definition,
                "situacao_semana_atual": week_status(week_start, extracted_at.date()),
                "data_hora_extracao": extracted_at.isoformat(timespec="seconds"),
            }
        )
    if not rows:
        raise ValueError("O arquivo manual de tempo de resposta não possui dados.")
    return rows


def normalize_label(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(character for character in normalized if not unicodedata.combining(character)).casefold()


def scheduled_status_ids(pipeline: Mapping[str, object]) -> set[int]:
    result: set[int] = set()
    for status in pipeline_statuses(pipeline):
        status_id = status.get("id")
        name = normalize_label(str(status.get("name") or ""))
        if isinstance(status_id, int) and "agend" in name:
            result.add(status_id)
    return result


def classify_monthly_outcome(
    lead: Mapping[str, object], scheduled_ids: set[int]
) -> str:
    status_id = lead.get("status_id")
    if status_id == 142:
        return "servicos_iniciados"
    if status_id == 143:
        return "perdidos"
    if isinstance(status_id, int) and status_id in scheduled_ids:
        return "agendados"
    return "em_andamento"


def monthly_week_segments(
    month_start: date, next_month: date, reporting_weekday: int
) -> list[tuple[date, date, bool]]:
    anchor = month_start - timedelta(
        days=(month_start.weekday() - reporting_weekday) % 7
    )
    segments: list[tuple[date, date, bool]] = []
    while anchor < next_month:
        full_end = anchor + timedelta(days=6)
        segment_start = max(anchor, month_start)
        segment_end = min(full_end, next_month - timedelta(days=1))
        if segment_start <= segment_end:
            segments.append(
                (segment_start, segment_end, segment_start != anchor or segment_end != full_end)
            )
        anchor += timedelta(days=7)
    return segments


def build_monthly_week_rows(
    snapshot: MonthlySnapshot,
    month_reference: str,
    reporting_week_start: date,
    extracted_at: datetime,
) -> list[dict[str, object]]:
    month_start, next_month = month_boundaries(month_reference)
    segments = monthly_week_segments(
        month_start, next_month, reporting_week_start.weekday()
    )
    scheduled_ids = scheduled_status_ids(snapshot.pipeline)
    leads_by_date: dict[date, list[dict[str, object]]] = {}
    for lead in snapshot.created_leads:
        created_at = lead.get("created_at")
        if not isinstance(created_at, int):
            continue
        created_date = datetime.fromtimestamp(
            created_at, tz=report_timezone()
        ).date()
        leads_by_date.setdefault(created_date, []).append(lead)

    provisional: list[dict[str, object]] = []
    for number, (segment_start, segment_end, is_partial) in enumerate(segments, 1):
        segment_leads = [
            lead
            for offset in range((segment_end - segment_start).days + 1)
            for lead in leads_by_date.get(segment_start + timedelta(days=offset), [])
        ]
        outcomes: Counter[str] = Counter(
            classify_monthly_outcome(lead, scheduled_ids) for lead in segment_leads
        )
        total = len(segment_leads)

        def rate(key: str) -> float | str:
            return round(outcomes[key] / total * 100, 1) if total else "N/C"

        provisional.append(
            {
                "mes_referencia": month_reference,
                "universo": "leads_criados_no_mes_e_estado_atual",
                "semana_numero": number,
                "periodo_inicio": segment_start.isoformat(),
                "periodo_fim": segment_end.isoformat(),
                "semana_parcial_no_mes": "sim" if is_partial else "não",
                "novos_leads": total,
                "servicos_iniciados": outcomes["servicos_iniciados"],
                "taxa_servicos_iniciados": rate("servicos_iniciados"),
                "agendados": outcomes["agendados"],
                "taxa_agendados": rate("agendados"),
                "perdidos": outcomes["perdidos"],
                "taxa_perdidos": rate("perdidos"),
                "em_andamento": outcomes["em_andamento"],
                "taxa_em_andamento": rate("em_andamento"),
                "data_hora_extracao": extracted_at.isoformat(timespec="seconds"),
            }
        )

    metric_pairs = [
        ("taxa_servicos_iniciados", "variacao_servicos_iniciados_pp"),
        ("taxa_agendados", "variacao_agendados_pp"),
        ("taxa_perdidos", "variacao_perdidos_pp"),
        ("taxa_em_andamento", "variacao_em_andamento_pp"),
    ]
    for index, row in enumerate(provisional):
        for metric, variation_field in metric_pairs:
            if index == 0:
                row[variation_field] = "N/A"
                continue
            previous = provisional[index - 1]
            if (
                row["semana_parcial_no_mes"] == "sim"
                or previous["semana_parcial_no_mes"] == "sim"
            ):
                row[variation_field] = "N/C"
                continue
            current_rate = row[metric]
            previous_rate = previous[metric]
            row[variation_field] = (
                round(current_rate - previous_rate, 1)
                if isinstance(current_rate, float) and isinstance(previous_rate, float)
                else "N/C"
            )
    return provisional


def build_monthly_summary_rows(
    snapshot: MonthlySnapshot,
    month_reference: str,
    extracted_at: datetime,
) -> list[dict[str, object]]:
    scheduled_ids = scheduled_status_ids(snapshot.pipeline)
    outcomes: Counter[str] = Counter(
        classify_monthly_outcome(lead, scheduled_ids) for lead in snapshot.created_leads
    )
    total = len(snapshot.created_leads)

    def rate(key: str) -> float | str:
        return round(outcomes[key] / total * 100, 1) if total else "N/C"

    return [
        {
            "mes_referencia": month_reference,
            "universo": "leads_criados_no_mes_e_estado_atual",
            "pipeline_id": snapshot.pipeline.get("id", ""),
            "pipeline_nome": snapshot.pipeline.get("name", ""),
            "novos_leads": total,
            "servicos_iniciados": outcomes["servicos_iniciados"],
            "taxa_servicos_iniciados": rate("servicos_iniciados"),
            "agendados": outcomes["agendados"],
            "taxa_agendados": rate("agendados"),
            "perdidos": outcomes["perdidos"],
            "taxa_perdidos": rate("perdidos"),
            "em_andamento": outcomes["em_andamento"],
            "taxa_em_andamento": rate("em_andamento"),
            "data_hora_extracao": extracted_at.isoformat(timespec="seconds"),
        }
    ]


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
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--force",
        action="store_true",
        help="sobrescreve todos os arquivos aplicáveis sem pedir confirmação",
    )
    mode.add_argument(
        "--validate-only",
        action="store_true",
        help="valida semana e configuração sem consultar a API nem gravar arquivos",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        load_env_file()
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"Erro ao carregar {ENV_FILE.name}: {exc}", file=sys.stderr)
        return 2

    generated_at = datetime.now(report_timezone())
    manual_response = manual_response_time_path(args.week_start)
    manual_response_rows: list[dict[str, object]] | None = None
    try:
        validate_week_start(args.week_start)
        KommoConfig.from_environment()
        if manual_response.is_file():
            manual_response_rows = build_manual_response_time_rows(
                manual_response, args.week_start, generated_at
            )
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"Erro de validação: {exc}", file=sys.stderr)
        return 2

    month_reference = applicable_month(args.week_start, generated_at.date())
    if args.validate_only:
        status = week_status(args.week_start, generated_at.date())
        monthly_status = month_reference or "não aplicável"
        print(
            "Validação concluída com sucesso: "
            f"semana={args.week_start.isoformat()}, situação={status}, "
            f"mês fechado={monthly_status}."
        )
        return 0

    identification_destination = output_path(args.week_start)
    if should_overwrite(identification_destination, force=args.force):
        record = build_identification(args.week_start, generated_at)
        try:
            write_csv_atomic(identification_destination, record)
        except OSError as exc:
            print(f"Erro ao gravar o CSV: {exc}", file=sys.stderr)
            return 1
        print(f"CSV gerado com sucesso: {identification_destination}")
    else:
        print("Arquivo de identificação preservado.")

    if not month_reference:
        calendar_month = closing_month(args.week_start)
        if calendar_month:
            print(
                "Itens mensais ainda não aplicáveis: "
                f"o mês {calendar_month} não terminou."
            )
        else:
            print("Itens mensais 4.2, 4.3, 4.13 e 4.14 não aplicáveis nesta semana.")
    else:
        monthly_targets = {
            "distribution": monthly_distribution_path(args.week_start),
            "stages": global_stages_path(args.week_start),
            "weeks": report_output_path(args.week_start, MONTHLY_WEEKS_FILENAME),
            "summary": report_output_path(args.week_start, MONTHLY_SUMMARY_FILENAME),
        }
        monthly_selected: dict[str, bool] = {}
        for key, destination in monthly_targets.items():
            monthly_selected[key] = should_overwrite(destination, force=args.force)
            if not monthly_selected[key]:
                print(f"Arquivo preservado: {destination}")

        if any(monthly_selected.values()):
            print(
                f"Consultando a Kommo em modo somente leitura "
                f"para o mês {month_reference}..."
            )
            try:
                snapshot = load_monthly_snapshot(month_reference)
                if monthly_selected["distribution"]:
                    lead_count = generate_monthly_distribution(
                        monthly_targets["distribution"],
                        snapshot,
                        month_reference,
                        generated_at,
                    )
                    print(
                        f"CSV gerado com sucesso: {monthly_targets['distribution']} "
                        f"({lead_count} leads consolidados)"
                    )
                if monthly_selected["stages"]:
                    stage_lead_count = generate_global_stages(
                        monthly_targets["stages"],
                        snapshot,
                        month_reference,
                        generated_at,
                    )
                    print(
                        f"CSV gerado com sucesso: {monthly_targets['stages']} "
                        f"({stage_lead_count} leads consolidados)"
                    )
                if monthly_selected["weeks"]:
                    month_week_rows = build_monthly_week_rows(
                        snapshot, month_reference, args.week_start, generated_at
                    )
                    if sum(int(row["novos_leads"]) for row in month_week_rows) != len(
                        snapshot.created_leads
                    ):
                        raise KommoApiError(
                            "As semanas do mês não fecham com o total mensal."
                        )
                    write_csv_rows_atomic(
                        monthly_targets["weeks"],
                        MONTHLY_WEEKS_FIELDS,
                        month_week_rows,
                    )
                    print(f"CSV gerado com sucesso: {monthly_targets['weeks']}")
                if monthly_selected["summary"]:
                    summary_rows = build_monthly_summary_rows(
                        snapshot, month_reference, generated_at
                    )
                    write_csv_rows_atomic(
                        monthly_targets["summary"],
                        MONTHLY_SUMMARY_FIELDS,
                        summary_rows,
                    )
                    print(f"CSV gerado com sucesso: {monthly_targets['summary']}")
            except (KommoApiError, OSError, ValueError) as exc:
                print(f"Erro ao gerar o consolidado mensal: {exc}", file=sys.stderr)
                return 1

    if week_status(args.week_start, generated_at.date()) == "futura":
        print("Itens semanais não aplicáveis: a semana informada é futura.")
        return 0

    weekly_targets = {
        "conversion": weekly_conversion_path(args.week_start),
        "movement": report_output_path(args.week_start, WEEKLY_MOVEMENT_FILENAME),
        "movement_method": report_output_path(
            args.week_start, MOVEMENT_METHOD_FILENAME
        ),
        "new_leads": report_output_path(args.week_start, WEEKLY_NEW_LEADS_FILENAME),
        "consultant_stages": report_output_path(
            args.week_start, CONSULTANT_STAGES_FILENAME
        ),
        "lost": report_output_path(args.week_start, LOST_COMPOSITION_FILENAME),
        "closure_events": report_output_path(
            args.week_start, CLOSURE_EVENTS_FILENAME
        ),
    }
    weekly_selected: dict[str, bool] = {}
    for key, destination in weekly_targets.items():
        weekly_selected[key] = should_overwrite(destination, force=args.force)
        if not weekly_selected[key]:
            print(f"Arquivo preservado: {destination}")

    if any(weekly_selected.values()):
        print("Consultando a Kommo em modo somente leitura para as duas semanas...")
        try:
            weekly_snapshot = load_weekly_snapshot(args.week_start)
            if weekly_selected["conversion"]:
                previous_total, current_total = generate_weekly_conversion(
                    weekly_targets["conversion"],
                    weekly_snapshot,
                    args.week_start,
                    generated_at,
                )
                print(
                    f"CSV gerado com sucesso: {weekly_targets['conversion']} "
                    f"({previous_total} leads anteriores; {current_total} atuais)"
                )
            if weekly_selected["movement"] or weekly_selected["movement_method"]:
                movement_rows, method_row = build_weekly_movement_rows(
                    weekly_snapshot, args.week_start, generated_at
                )
                if weekly_selected["movement"]:
                    write_csv_rows_atomic(
                        weekly_targets["movement"],
                        WEEKLY_MOVEMENT_FIELDS,
                        movement_rows,
                    )
                    print(f"CSV gerado com sucesso: {weekly_targets['movement']}")
                if weekly_selected["movement_method"]:
                    write_csv_rows_atomic(
                        weekly_targets["movement_method"],
                        MOVEMENT_METHOD_FIELDS,
                        [method_row],
                    )
                    print(
                        f"CSV gerado com sucesso: {weekly_targets['movement_method']}"
                    )
            if weekly_selected["new_leads"]:
                new_lead_rows = build_weekly_new_leads_rows(
                    weekly_snapshot, args.week_start, generated_at
                )
                write_csv_rows_atomic(
                    weekly_targets["new_leads"],
                    WEEKLY_NEW_LEADS_FIELDS,
                    new_lead_rows,
                )
                print(f"CSV gerado com sucesso: {weekly_targets['new_leads']}")
            if weekly_selected["consultant_stages"]:
                consultant_rows = build_consultant_stage_rows(
                    weekly_snapshot, args.week_start, generated_at
                )
                write_csv_rows_atomic(
                    weekly_targets["consultant_stages"],
                    CONSULTANT_STAGES_FIELDS,
                    consultant_rows,
                )
                print(
                    f"CSV gerado com sucesso: {weekly_targets['consultant_stages']}"
                )
            if weekly_selected["lost"]:
                lost_rows = build_lost_composition_rows(
                    weekly_snapshot, args.week_start, generated_at
                )
                write_csv_rows_atomic(
                    weekly_targets["lost"], LOST_COMPOSITION_FIELDS, lost_rows
                )
                print(f"CSV gerado com sucesso: {weekly_targets['lost']}")
            if weekly_selected["closure_events"]:
                closure_rows = build_closure_event_rows(
                    weekly_snapshot, args.week_start, generated_at
                )
                write_csv_rows_atomic(
                    weekly_targets["closure_events"],
                    CLOSURE_EVENTS_FIELDS,
                    closure_rows,
                )
                print(
                    f"CSV gerado com sucesso: {weekly_targets['closure_events']}"
                )
        except (KommoApiError, OSError, ValueError) as exc:
            print(f"Erro ao gerar os consolidados semanais: {exc}", file=sys.stderr)
            return 1

    response_destination = report_output_path(args.week_start, RESPONSE_TIME_FILENAME)
    if should_overwrite(response_destination, force=args.force):
        try:
            if manual_response_rows is not None:
                print(f"Usando o tempo de resposta informado manualmente: {manual_response}")
                response_rows = manual_response_rows
            else:
                print("Verificando a disponibilidade do tempo de primeira resposta...")
                response_rows = build_response_time_rows(args.week_start, generated_at)
            write_csv_rows_atomic(
                response_destination, RESPONSE_TIME_FIELDS, response_rows
            )
            print(f"CSV gerado com sucesso: {response_destination}")
        except (KommoApiError, OSError, ValueError) as exc:
            print(f"Erro ao verificar o tempo de resposta: {exc}", file=sys.stderr)
            return 1
    else:
        print(f"Arquivo preservado: {response_destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
