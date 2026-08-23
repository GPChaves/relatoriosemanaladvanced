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
    parse_week_start,
    report_timezone,
    write_csv_rows_atomic,
)


ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT_ROOT = ROOT / "outputs"
DEFAULT_PIPELINE_NAME = "Funil de vendas"
UNASSIGNED_RESPONSIBLE = "Sem consultor definido"


def pct(part: int, total: int) -> float:
    return round(part / total * 100, 1) if total else 0.0


def pp(current: float, previous: float) -> float:
    return round(current - previous, 1)


def normalized_responsible(value: object) -> str:
    text = str(value or "").strip()
    if not text or text.casefold() in {"nan", "advanced mecânica"}:
        return UNASSIGNED_RESPONSIBLE
    return text


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


def period_slice(frame: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
    lower = pd.Timestamp(datetime.combine(start, time.min))
    upper = pd.Timestamp(datetime.combine(end, time.max))
    return frame[frame["Data Criada"].between(lower, upper)].copy()


def write_csv(path: Path, fields: Sequence[str], rows: list[dict[str, object]]) -> None:
    write_csv_rows_atomic(path, list(fields), rows)


def _preflight_source(
    source: Path,
    week_start: date,
    pipeline_name: str,
    period_days: int,
) -> tuple[pd.DataFrame, pd.DataFrame, date, date, date]:
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
        "Última modificação",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(
            "Colunas ausentes no export da Kommo: " + ", ".join(sorted(missing))
        )

    frame["Data Criada"] = pd.to_datetime(
        frame["Data Criada"], dayfirst=True, errors="coerce"
    )
    frame["Última modificação"] = pd.to_datetime(
        frame["Última modificação"], dayfirst=True, errors="coerce"
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
    frame["responsavel"] = frame["Lead usuário responsável"].map(
        normalized_responsible
    )
    frame["categoria"] = frame["Etapa do lead"].map(stage_category)

    current_end = week_start + timedelta(days=period_days - 1)
    previous_start = week_start - timedelta(days=7)
    previous_end = previous_start + timedelta(days=period_days - 1)
    latest_update = frame["Última modificação"].max()
    if pd.isna(latest_update) or latest_update.date() < current_end:
        raise ValueError(
            "O export parece ter sido gerado antes do fim do período solicitado."
        )

    previous = period_slice(frame, previous_start, previous_end)
    current = period_slice(frame, week_start, current_end)
    if current.empty:
        raise ValueError("O Excel não contém leads criados no período solicitado.")
    return previous, current, current_end, previous_start, previous_end


def _build_artifacts(
    previous: pd.DataFrame,
    current: pd.DataFrame,
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

    total_previous = len(previous)
    total_current = len(current)
    responsible_order = sorted(
        set(previous["responsavel"]) | set(current["responsavel"]),
        key=lambda name: (name == UNASSIGNED_RESPONSIBLE, name.casefold()),
    )
    new_lead_rows: list[dict[str, object]] = []
    for responsible in responsible_order:
        previous_count = int((previous["responsavel"] == responsible).sum())
        current_count = int((current["responsavel"] == responsible).sum())
        previous_share = pct(previous_count, total_previous)
        current_share = pct(current_count, total_current)
        new_lead_rows.append(
            {
                "pipeline_id": "",
                "pipeline_nome": pipeline_name,
                "responsavel_id": "",
                "responsavel_nome": responsible,
                "novos_leads_anterior": previous_count,
                "novos_leads_atual": current_count,
                "variacao_absoluta_responsavel": current_count - previous_count,
                "participacao_anterior": previous_share,
                "participacao_atual": current_share,
                "variacao_pp": pp(current_share, previous_share),
                "total_novos_leads_anterior": total_previous,
                "total_novos_leads_atual": total_current,
                "variacao_total_absoluta": total_current - total_previous,
                "situacao_semana_atual": "completa",
                "data_hora_extracao": stamp,
            }
        )
    artifacts.append(("07_novos_leads_semana.csv", WEEKLY_NEW_LEADS_FIELDS, new_lead_rows))

    consultants = [
        responsible
        for responsible in responsible_order
        if responsible != UNASSIGNED_RESPONSIBLE
    ]
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
                "universo": "leads_criados_no_periodo",
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
                    "Comparação entre períodos com a mesma quantidade de dias."
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

    previous_losses = previous[previous["Etapa do lead"].map(is_lost)]
    current_losses = current[current["Etapa do lead"].map(is_lost)]
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
                "O arquivo não guarda o histórico completo de movimentações."
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
                "A fotografia exportada não permite reconstruir o histórico de movimentações."
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
    previous, current, current_end, previous_start, previous_end = _preflight_source(
        source, week_start, pipeline_name, period_days
    )

    extracted_at = datetime.now(report_timezone())
    response_rows = build_manual_response_time_rows(
        manual_response_time_path(week_start), week_start, extracted_at
    )
    artifacts = _build_artifacts(
        previous,
        current,
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
