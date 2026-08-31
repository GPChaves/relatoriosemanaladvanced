from __future__ import annotations

import argparse
import os
import re
import shutil
import tempfile
import uuid
from collections import Counter
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Sequence

import pandas as pd

from relatorio import (
    CLOSURE_EVENTS_FIELDS,
    CONSULTANT_STAGES_FIELDS,
    LOST_COMPOSITION_FIELDS,
    MOVEMENT_METHOD_FIELDS,
    RESPONSE_TIME_FIELDS,
    WEEKLY_CONVERSION_FIELDS,
    WEEKLY_MOVEMENT_FIELDS,
    WEEKLY_NEW_LEADS_FIELDS,
    build_manual_response_time_rows,
    closing_month,
    manual_response_time_path,
    normalize_report_responsible_name,
    parse_week_start,
    report_timezone,
    validate_weekly_new_leads_rows,
    write_csv_rows_atomic,
)


ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT_ROOT = ROOT / "outputs"
DEFAULT_PIPELINE_NAME = "Funil de vendas"
UNASSIGNED_RESPONSIBLE = "Sem usuário responsável"
CLOSE_DATE_ALIASES = (
    "Data Fechada",
    "Data de fechamento",
    "Data fechada",
    "Fechado em",
)
CONTACT_ID_ALIASES = (
    "ID do contato",
    "Contato ID",
    "Contact ID",
    "ID contato",
)


def pct(part: int, total: int) -> float:
    return round(part / total * 100, 1) if total else 0.0


def pp(current: float, previous: float) -> float:
    return round(current - previous, 1)


def normalized_responsible(value: object) -> str:
    text = str(value or "").strip()
    if text.casefold() == "nan":
        text = ""
    return normalize_report_responsible_name(text)


def resolve_close_date_column(columns: Sequence[object]) -> str:
    available = {str(column).strip(): str(column) for column in columns}
    matches = [available[name] for name in CLOSE_DATE_ALIASES if name in available]
    if not matches:
        raise ValueError(
            "Coluna de data de fechamento ausente no export da Kommo. "
            "Inclua uma destas colunas: " + ", ".join(CLOSE_DATE_ALIASES) + "."
        )
    if len(matches) > 1:
        raise ValueError(
            "O export contém mais de uma coluna de data de fechamento: "
            + ", ".join(matches)
            + ". Mantenha somente uma."
        )
    return matches[0]


def resolve_contact_id_column(columns: Sequence[object]) -> str:
    available = {str(column).strip(): str(column) for column in columns}
    matches = [available[name] for name in CONTACT_ID_ALIASES if name in available]
    if not matches:
        raise ValueError(
            "Não é possível identificar clientes retorno neste XLSX. Inclua uma "
            "coluna de ID estável do contato (" + ", ".join(CONTACT_ID_ALIASES) + ") "
            "ou execute relatorio.py pela API da Kommo."
        )
    if len(matches) > 1:
        raise ValueError(
            "O export contém mais de uma coluna de ID do contato: "
            + ", ".join(matches)
            + ". Mantenha somente uma."
        )
    return matches[0]


def stage_category(value: object) -> str:
    text = str(value or "").strip()
    if not text or text.casefold() == "nan":
        return "Etapa não informada"
    match = re.match(r"(?i)^perdido\s*\((.+)\)\s*$", text)
    if match:
        return f"Perdido — {match.group(1).strip()}"
    return text


def is_service(value: object) -> bool:
    return "serviço iniciado" in str(value or "").strip().casefold()


def is_lost(value: object) -> bool:
    return str(value or "").strip().casefold().startswith("perdido")


def period_slice(
    frame: pd.DataFrame, start: date, end: date, date_column: str
) -> pd.DataFrame:
    lower = pd.Timestamp(datetime.combine(start, time.min))
    upper = pd.Timestamp(datetime.combine(end, time.max))
    return frame[frame[date_column].between(lower, upper)].copy()


def write_csv(path: Path, fields: Sequence[str], rows: list[dict[str, object]]) -> None:
    write_csv_rows_atomic(path, list(fields), rows)


def _preflight_source(
    source: Path,
    week_start: date,
    pipeline_name: str,
    period_days: int,
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    date,
    date,
    date,
]:
    if not 1 <= period_days <= 7:
        raise ValueError("period_days deve estar entre 1 e 7.")
    if closing_month(week_start):
        raise ValueError(
            "A semana solicitada fecha um mês, mas a rota XLSX não gera os "
            "consolidados mensais obrigatórios. Execute relatorio.py com a API da "
            "Kommo para essa semana."
        )
    pipeline_name = pipeline_name.strip()
    if not pipeline_name:
        raise ValueError("pipeline_name não pode ser vazio.")
    if not source.is_file():
        raise ValueError(f"Export XLSX não encontrado: {source}")

    frame = pd.read_excel(source)
    required = {
        "Lead usuário responsável",
        "Etapa do lead",
        "Funil de vendas",
        "Data Criada",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(
            "Colunas ausentes no export da Kommo: " + ", ".join(sorted(missing))
        )
    close_date_column = resolve_close_date_column(frame.columns)
    contact_id_column = resolve_contact_id_column(frame.columns)

    frame["Data Criada"] = pd.to_datetime(
        frame["Data Criada"], format="mixed", dayfirst=True, errors="coerce"
    )
    raw_close_dates = frame[close_date_column].copy()
    frame[close_date_column] = pd.to_datetime(
        frame[close_date_column], format="mixed", dayfirst=True, errors="coerce"
    )
    contact_keys = frame[contact_id_column].map(
        lambda value: "" if pd.isna(value) else str(value).strip()
    )
    first_lead_by_contact = frame.groupby(contact_keys)["Data Criada"].transform("min")
    frame["cliente_retorno"] = (
        contact_keys.ne("") & first_lead_by_contact.lt(frame["Data Criada"])
    )
    frame = frame[
        frame["Funil de vendas"].astype(str).str.casefold()
        == pipeline_name.casefold()
    ].copy()
    if frame.empty:
        raise ValueError(
            f"O export não contém leads no pipeline {pipeline_name!r}. "
            "Confira --pipeline-name e gere novamente o XLSX."
        )
    raw_close_dates = raw_close_dates.loc[frame.index]
    for date_column in ("Data Criada",):
        invalid_rows = [int(index) + 2 for index in frame.index[frame[date_column].isna()]]
        if invalid_rows:
            preview = ", ".join(str(row) for row in invalid_rows[:5])
            suffix = "..." if len(invalid_rows) > 5 else ""
            raise ValueError(
                f"A coluna {date_column!r} contém data inválida nas linhas "
                f"{preview}{suffix}. Gere novamente o XLSX ou corrija essas células."
            )
    close_text = raw_close_dates.astype(str).str.strip().str.casefold()
    close_present = raw_close_dates.notna() & ~close_text.isin(
        {"", "nan", "nat", "none"}
    )
    invalid_close = close_present & frame[close_date_column].isna()
    invalid_rows = [int(index) + 2 for index in frame.index[invalid_close]]
    if invalid_rows:
        preview = ", ".join(str(row) for row in invalid_rows[:5])
        suffix = "..." if len(invalid_rows) > 5 else ""
        raise ValueError(
            f"A coluna {close_date_column!r} contém data inválida nas linhas "
            f"{preview}{suffix}. Gere novamente o XLSX ou corrija essas células."
        )
    frame["responsavel"] = frame["Lead usuário responsável"].map(
        normalized_responsible
    )
    frame["categoria"] = frame["Etapa do lead"].map(stage_category)

    current_end = week_start + timedelta(days=period_days - 1)
    previous_start = week_start - timedelta(days=7)
    previous_end = previous_start + timedelta(days=period_days - 1)
    terminal_mask = frame["Etapa do lead"].map(
        lambda value: is_service(value) or is_lost(value)
    )
    terminal = frame[terminal_mask].copy()
    terminal_without_close = terminal[terminal[close_date_column].isna()]
    if not terminal_without_close.empty:
        rows = [int(index) + 2 for index in terminal_without_close.index[:5]]
        suffix = "..." if len(terminal_without_close) > 5 else ""
        raise ValueError(
            "Leads em 'Serviço iniciado' ou 'Perdido' estão sem data de fechamento "
            f"nas linhas {', '.join(map(str, rows))}{suffix}."
        )

    previous_modified = period_slice(
        terminal, previous_start, previous_end, close_date_column
    )
    current_modified = period_slice(
        terminal, week_start, current_end, close_date_column
    )
    previous_modified["data_fechamento"] = previous_modified[close_date_column]
    current_modified["data_fechamento"] = current_modified[close_date_column]
    previous_created = period_slice(frame, previous_start, previous_end, "Data Criada")
    current_created = period_slice(frame, week_start, current_end, "Data Criada")
    return (
        previous_modified,
        current_modified,
        previous_created,
        current_created,
        current_end,
        previous_start,
        previous_end,
    )


def _build_artifacts(
    previous: pd.DataFrame,
    current: pd.DataFrame,
    previous_created: pd.DataFrame,
    current_created: pd.DataFrame,
    week_start: date,
    current_end: date,
    previous_start: date,
    previous_end: date,
    pipeline_name: str,
    response_rows: list[dict[str, object]],
    extracted_at: datetime,
) -> list[tuple[str, Sequence[str], list[dict[str, object]]]]:
    stamp = extracted_at.isoformat(timespec="seconds")
    artifacts: list[tuple[str, Sequence[str], list[dict[str, object]]]] = []

    identification_fields = [
        "titulo",
        "data_inicial",
        "data_final",
        "fuso_horario",
        "situacao_semana",
        "fecha_mes",
        "mes_fechado",
        "data_hora_geracao",
    ]
    artifacts.append(
        (
            "01_identificacao_periodo.csv",
            identification_fields,
            [
                {
                    "titulo": "Relatório de Desempenho Comercial",
                    "data_inicial": week_start.isoformat(),
                    "data_final": current_end.isoformat(),
                    "fuso_horario": "America/Sao_Paulo",
                    "situacao_semana": "completa",
                    "fecha_mes": "não",
                    "mes_fechado": "",
                    "data_hora_geracao": stamp,
                }
            ],
        )
    )

    closure_rows: list[dict[str, object]] = []
    for period, subset in (("anterior", previous), ("atual", current)):
        for index, lead in subset.iterrows():
            status_id = 142 if is_service(lead["Etapa do lead"]) else 143
            lead_id: object = f"linha_excel_{int(index) + 2}"
            for identifier_column in ("ID", "ID do lead", "Lead ID"):
                if identifier_column in subset.columns:
                    candidate = lead.get(identifier_column)
                    if pd.notna(candidate) and str(candidate).strip():
                        lead_id = candidate
                    break
            closed_at = lead["data_fechamento"]
            closure_rows.append(
                {
                    "periodo": period,
                    "lead_id": lead_id,
                    "evento_id": "",
                    "data_hora_evento": closed_at.isoformat(),
                    "status_destino_id": status_id,
                    "status_destino_nome": (
                        "Serviço iniciado" if status_id == 142 else "Perdido"
                    ),
                    "usuario_responsavel": lead["responsavel"],
                    "considerado_no_indicador": "sim",
                    "data_hora_extracao": stamp,
                }
            )
    artifacts.append(
        ("10_eventos_fechamento.csv", CLOSURE_EVENTS_FIELDS, closure_rows)
    )

    total_previous = len(previous_created)
    total_current = len(current_created)
    total_returning_previous = int(previous_created["cliente_retorno"].sum())
    total_returning_current = int(current_created["cliente_retorno"].sum())
    new_lead_responsibles = sorted(
        set(previous_created["responsavel"]) | set(current_created["responsavel"]),
        key=lambda name: (name == UNASSIGNED_RESPONSIBLE, name.casefold()),
    )
    new_lead_rows: list[dict[str, object]] = []
    for responsible in new_lead_responsibles:
        previous_count = int((previous_created["responsavel"] == responsible).sum())
        current_count = int((current_created["responsavel"] == responsible).sum())
        previous_returning = int(
            previous_created.loc[
                previous_created["responsavel"] == responsible, "cliente_retorno"
            ].sum()
        )
        current_returning = int(
            current_created.loc[
                current_created["responsavel"] == responsible, "cliente_retorno"
            ].sum()
        )
        previous_share = pct(previous_count, total_previous)
        current_share = pct(current_count, total_current)
        new_lead_rows.append(
            {
                "pipeline_id": "",
                "pipeline_nome": pipeline_name,
                "universo": "leads_criados_no_periodo",
                "metodologia_cliente_retorno": (
                    "historico_disponivel_no_export_por_id_contato"
                ),
                "responsavel_id": "",
                "responsavel_nome": responsible,
                "novos_leads_anterior": previous_count,
                "novos_leads_atual": current_count,
                "clientes_retorno_anterior": previous_returning,
                "clientes_retorno_atual": current_returning,
                "percentual_retorno_anterior": pct(
                    previous_returning, previous_count
                ),
                "percentual_retorno_atual": pct(current_returning, current_count),
                "variacao_retorno_pp": pp(
                    pct(current_returning, current_count),
                    pct(previous_returning, previous_count),
                ),
                "variacao_absoluta_responsavel": current_count - previous_count,
                "participacao_anterior": previous_share,
                "participacao_atual": current_share,
                "variacao_pp": pp(current_share, previous_share),
                "total_novos_leads_anterior": total_previous,
                "total_novos_leads_atual": total_current,
                "total_clientes_retorno_anterior": total_returning_previous,
                "total_clientes_retorno_atual": total_returning_current,
                "variacao_total_absoluta": total_current - total_previous,
                "situacao_semana_atual": "completa",
                "data_hora_extracao": stamp,
            }
        )
    validate_weekly_new_leads_rows(new_lead_rows)
    artifacts.append(("07_novos_leads_semana.csv", WEEKLY_NEW_LEADS_FIELDS, new_lead_rows))

    closed_responsibles = sorted(
        set(previous["responsavel"]) | set(current["responsavel"]),
        key=lambda name: (name == UNASSIGNED_RESPONSIBLE, name.casefold()),
    )
    consultants = closed_responsibles
    conversion_rows: list[dict[str, object]] = []
    for responsible in consultants:
        previous_person = previous[previous["responsavel"] == responsible]
        current_person = current[current["responsavel"] == responsible]
        previous_count = len(previous_person)
        current_count = len(current_person)
        previous_services = int(previous_person["Etapa do lead"].map(is_service).sum())
        current_services = int(current_person["Etapa do lead"].map(is_service).sum())
        previous_rate = pct(previous_services, previous_count)
        current_rate = pct(current_services, current_count)
        conversion_rows.append(
            {
                "pipeline_id": "",
                "pipeline_nome": pipeline_name,
                "responsavel_id": "",
                "responsavel_nome": responsible,
                "universo": "leads_fechados_no_periodo_por_data_de_fechamento",
                "semana_anterior_inicio": previous_start.isoformat(),
                "semana_anterior_fim": previous_end.isoformat(),
                "total_leads_anterior": previous_count,
                "servicos_iniciados_anterior": previous_services,
                "taxa_conversao_anterior": previous_rate,
                "semana_atual_inicio": week_start.isoformat(),
                "semana_atual_fim": current_end.isoformat(),
                "total_leads_atual": current_count,
                "servicos_iniciados_atual": current_services,
                "taxa_conversao_atual": current_rate,
                "variacao_pp": pp(current_rate, previous_rate),
                "situacao_semana_atual": "completa",
                "observacao_maturacao": (
                    "A classificação considera a data de fechamento e a etapa "
                    "terminal atual; a atribuição considera o responsável registrado no lead."
                ),
                "data_hora_extracao": stamp,
            }
        )
    artifacts.append(("04_conversao_responsavel.csv", WEEKLY_CONVERSION_FIELDS, conversion_rows))

    categories = sorted(
        set(previous["categoria"]) | set(current["categoria"]), key=str.casefold
    )
    stage_rows: list[dict[str, object]] = []
    for responsible in consultants:
        previous_person = previous[previous["responsavel"] == responsible]
        current_person = current[current["responsavel"] == responsible]
        previous_total_person = len(previous_person)
        current_total_person = len(current_person)
        for category in categories:
            previous_count = int((previous_person["categoria"] == category).sum())
            current_count = int((current_person["categoria"] == category).sum())
            previous_rate = pct(previous_count, previous_total_person)
            current_rate = pct(current_count, current_total_person)
            loss_reason = (
                category.removeprefix("Perdido — ")
                if category.startswith("Perdido — ")
                else ""
            )
            stage_rows.append(
                {
                    "pipeline_id": "",
                    "pipeline_nome": pipeline_name,
                    "universo": "leads_fechados_no_periodo_por_data_de_fechamento",
                    "responsavel_id": "",
                    "responsavel_nome": responsible,
                    "categoria_relatorio": category,
                    "status_id": "",
                    "etapa_crm": category,
                    "loss_reason_id": "",
                    "motivo_perda_crm": loss_reason,
                    "quantidade_anterior": previous_count,
                    "percentual_anterior": previous_rate,
                    "quantidade_atual": current_count,
                    "percentual_atual": current_rate,
                    "variacao_pp": pp(current_rate, previous_rate),
                    "total_responsavel_anterior": previous_total_person,
                    "total_responsavel_atual": current_total_person,
                    "situacao_semana_atual": "completa",
                    "data_hora_extracao": stamp,
                }
            )
    artifacts.append(("08_etapas_por_consultor.csv", CONSULTANT_STAGES_FIELDS, stage_rows))

    previous_losses = previous[previous["Etapa do lead"].map(is_lost).astype(bool)]
    current_losses = current[current["Etapa do lead"].map(is_lost).astype(bool)]
    previous_loss_counts = Counter(previous_losses["categoria"])
    current_loss_counts = Counter(current_losses["categoria"])
    total_previous_lost = len(previous_losses)
    total_current_lost = len(current_losses)
    loss_rows: list[dict[str, object]] = []
    for category in sorted(
        set(previous_loss_counts) | set(current_loss_counts), key=str.casefold
    ):
        previous_count = previous_loss_counts[category]
        current_count = current_loss_counts[category]
        previous_rate = pct(previous_count, total_previous_lost)
        current_rate = pct(current_count, total_current_lost)
        reason = (
            category.removeprefix("Perdido — ")
            if category.startswith("Perdido — ")
            else "Motivo não informado"
        )
        loss_rows.append(
            {
                "pipeline_id": "",
                "pipeline_nome": pipeline_name,
                "universo": "leads_fechados_com_etapa_atual_perdido",
                "loss_reason_id": "",
                "motivo_perda": reason,
                "quantidade_anterior": previous_count,
                "percentual_anterior": previous_rate,
                "quantidade_atual": current_count,
                "percentual_atual": current_rate,
                "variacao_pp": pp(current_rate, previous_rate),
                "total_perdidos_anterior": total_previous_lost,
                "total_perdidos_atual": total_current_lost,
                "situacao_semana_atual": "completa",
                "data_hora_extracao": stamp,
            }
        )
    artifacts.append(("11_composicao_leads_perdidos.csv", LOST_COMPOSITION_FIELDS, loss_rows))

    movement_fields = [
        "status_dado",
        "motivo_indisponibilidade",
        *WEEKLY_MOVEMENT_FIELDS,
    ]
    movement_row = {field: "" for field in movement_fields}
    movement_row.update(
        {
            "status_dado": "indisponivel",
            "motivo_indisponibilidade": (
                "Não há histórico completo de movimentações para este período."
            ),
            "situacao_semana_atual": "completa",
            "data_hora_extracao": stamp,
        }
    )
    artifacts.append(("05_movimentacao_semanal.csv", movement_fields, [movement_row]))

    method_row = {field: "" for field in MOVEMENT_METHOD_FIELDS}
    method_row.update(
        {
            "universo": "não disponível",
            "unidade_contagem": "não disponível",
            "nota_comparabilidade": (
                "O histórico disponível não permite reconstruir todas as movimentações."
            ),
            "data_hora_extracao": stamp,
        }
    )
    artifacts.append(
        (
            "06_nota_metodologica_movimentacao.csv",
            MOVEMENT_METHOD_FIELDS,
            [method_row],
        )
    )

    for row in response_rows:
        row["situacao_semana_atual"] = "completa"
    artifacts.append(("09_tempo_medio_resposta.csv", RESPONSE_TIME_FIELDS, response_rows))
    return artifacts


def _promote_staging(staging_dir: Path, output_dir: Path) -> None:
    if not output_dir.exists():
        os.replace(staging_dir, output_dir)
        return

    backup_dir = output_dir.with_name(
        f".{output_dir.name}.backup-{uuid.uuid4().hex}"
    )
    os.replace(output_dir, backup_dir)
    try:
        os.replace(staging_dir, output_dir)
    except Exception:
        os.replace(backup_dir, output_dir)
        raise
    shutil.rmtree(backup_dir, ignore_errors=True)


def build_outputs(
    source: Path,
    week_start: date,
    output_root: Path,
    *,
    period_days: int = 7,
    pipeline_name: str = DEFAULT_PIPELINE_NAME,
    force: bool = False,
) -> Path:
    pipeline_name = pipeline_name.strip()
    (
        previous,
        current,
        previous_created,
        current_created,
        current_end,
        previous_start,
        previous_end,
    ) = _preflight_source(source, week_start, pipeline_name, period_days)

    extracted_at = datetime.now(report_timezone())
    response_rows = build_manual_response_time_rows(
        manual_response_time_path(week_start), week_start, extracted_at
    )
    artifacts = _build_artifacts(
        previous,
        current,
        previous_created,
        current_created,
        week_start,
        current_end,
        previous_start,
        previous_end,
        pipeline_name,
        response_rows,
        extracted_at,
    )

    output_dir = output_root / str(week_start.year) / week_start.isoformat()
    if output_dir.exists() and not force:
        raise FileExistsError(
            f"A pasta de saída já existe: {output_dir}. "
            "Use --force para substituí-la de forma segura."
        )

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging_dir = Path(
        tempfile.mkdtemp(prefix=f".{week_start.isoformat()}-", dir=output_dir.parent)
    )
    try:
        if output_dir.exists():
            shutil.copytree(output_dir, staging_dir, dirs_exist_ok=True)
        for filename, fields, rows in artifacts:
            write_csv(staging_dir / filename, fields, rows)
        _promote_staging(staging_dir, output_dir)
    finally:
        if staging_dir.exists():
            shutil.rmtree(staging_dir, ignore_errors=True)
    return output_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Consolida um export XLSX da Kommo em CSVs comparativos."
    )
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--week-start", type=parse_week_start, required=True)
    parser.add_argument("--period-days", type=int, default=7)
    parser.add_argument("--pipeline-name", default=DEFAULT_PIPELINE_NAME)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Substitui uma saída existente somente após concluir toda a nova geração.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output_dir = build_outputs(
        args.source.resolve(),
        args.week_start,
        args.output_root.resolve(),
        period_days=args.period_days,
        pipeline_name=args.pipeline_name,
        force=args.force,
    )
    print(f"Consolidados gerados: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
