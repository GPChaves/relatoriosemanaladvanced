from __future__ import annotations

import argparse
import re
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
    manual_response_time_path,
    parse_week_start,
    report_timezone,
    write_csv_rows_atomic,
)


ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT_ROOT = ROOT / "outputs"
PIPELINE_NAME = "Funil de vendas"
CONSULTANT_NAMES = ("Milena", "Vitor")


def pct(part: int, total: int) -> float:
    return round(part / total * 100, 1) if total else 0.0


def pp(current: float, previous: float) -> float:
    return round(current - previous, 1)


def normalized_responsible(value: object) -> str:
    text = str(value or "").strip()
    if not text or text.casefold() in {"nan", "advanced mecânica"}:
        return "Sem consultor definido"
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


def week_slice(frame: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
    lower = pd.Timestamp(datetime.combine(start, time.min))
    upper = pd.Timestamp(datetime.combine(end, time.max))
    return frame[frame["Data Criada"].between(lower, upper)].copy()


def write_csv(path: Path, fields: Sequence[str], rows: list[dict[str, object]]) -> None:
    write_csv_rows_atomic(path, list(fields), rows)


def build_outputs(source: Path, week_start: date, output_root: Path) -> Path:
    frame = pd.read_excel(source)
    required = {"Lead usuário responsável", "Etapa do lead", "Funil de vendas", "Data Criada"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError("Colunas ausentes no export da Kommo: " + ", ".join(sorted(missing)))
    frame["Data Criada"] = pd.to_datetime(frame["Data Criada"], dayfirst=True, errors="coerce")
    frame = frame[frame["Funil de vendas"].astype(str).str.casefold() == PIPELINE_NAME.casefold()].copy()
    frame["responsavel"] = frame["Lead usuário responsável"].map(normalized_responsible)
    frame["categoria"] = frame["Etapa do lead"].map(stage_category)

    nominal_end = week_start + timedelta(days=6)
    current_candidates = frame[frame["Data Criada"].dt.date.between(week_start, nominal_end)]
    if current_candidates.empty:
        raise ValueError("O Excel não contém leads criados na semana solicitada.")
    coverage_end = min(nominal_end, current_candidates["Data Criada"].max().date())
    day_span = (coverage_end - week_start).days
    previous_start = week_start - timedelta(days=7)
    previous_end = previous_start + timedelta(days=day_span)
    previous = week_slice(frame, previous_start, previous_end)
    current = week_slice(frame, week_start, coverage_end)
    status = "completa" if coverage_end == nominal_end else "parcial"
    extracted_at = datetime.now(report_timezone())
    stamp = extracted_at.isoformat(timespec="seconds")
    output_dir = output_root / str(week_start.year) / week_start.isoformat()
    output_dir.mkdir(parents=True, exist_ok=True)

    identification_fields = [
        "titulo", "data_inicial", "data_final", "fuso_horario", "situacao_semana",
        "fecha_mes", "mes_fechado", "data_hora_geracao",
    ]
    write_csv(
        output_dir / "01_identificacao_periodo.csv",
        identification_fields,
        [{
            "titulo": "Relatório de Desempenho Comercial",
            "data_inicial": week_start.isoformat(),
            "data_final": coverage_end.isoformat(),
            "fuso_horario": "America/Sao_Paulo",
            "situacao_semana": status,
            "fecha_mes": "não",
            "mes_fechado": "",
            "data_hora_geracao": stamp,
        }],
    )

    total_previous = len(previous)
    total_current = len(current)
    responsible_order = sorted(
        set(previous["responsavel"]) | set(current["responsavel"]),
        key=lambda name: (name == "Sem consultor definido", name.casefold()),
    )
    new_lead_rows: list[dict[str, object]] = []
    for responsible in responsible_order:
        previous_count = int((previous["responsavel"] == responsible).sum())
        current_count = int((current["responsavel"] == responsible).sum())
        previous_share = pct(previous_count, total_previous)
        current_share = pct(current_count, total_current)
        new_lead_rows.append({
            "pipeline_id": "", "pipeline_nome": PIPELINE_NAME, "responsavel_id": "",
            "responsavel_nome": responsible,
            "novos_leads_anterior": previous_count, "novos_leads_atual": current_count,
            "variacao_absoluta_responsavel": current_count - previous_count,
            "participacao_anterior": previous_share, "participacao_atual": current_share,
            "variacao_pp": pp(current_share, previous_share),
            "total_novos_leads_anterior": total_previous,
            "total_novos_leads_atual": total_current,
            "variacao_total_absoluta": total_current - total_previous,
            "situacao_semana_atual": status, "data_hora_extracao": stamp,
        })
    write_csv(output_dir / "07_novos_leads_semana.csv", WEEKLY_NEW_LEADS_FIELDS, new_lead_rows)

    consultants = [
        responsible for responsible in responsible_order
        if any(name.casefold() in responsible.casefold() for name in CONSULTANT_NAMES)
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
        conversion_rows.append({
            "pipeline_id": "", "pipeline_nome": PIPELINE_NAME, "responsavel_id": "",
            "responsavel_nome": responsible, "universo": "leads_criados_no_periodo",
            "semana_anterior_inicio": previous_start.isoformat(),
            "semana_anterior_fim": previous_end.isoformat(),
            "total_leads_anterior": previous_count,
            "servicos_iniciados_anterior": previous_services,
            "taxa_conversao_anterior": previous_rate,
            "semana_atual_inicio": week_start.isoformat(),
            "semana_atual_fim": coverage_end.isoformat(),
            "total_leads_atual": current_count,
            "servicos_iniciados_atual": current_services,
            "taxa_conversao_atual": current_rate,
            "variacao_pp": pp(current_rate, previous_rate),
            "situacao_semana_atual": status,
            "observacao_maturacao": "Comparação entre períodos com a mesma quantidade de dias.",
            "data_hora_extracao": stamp,
        })
    write_csv(output_dir / "04_conversao_responsavel.csv", WEEKLY_CONVERSION_FIELDS, conversion_rows)

    categories = sorted(set(previous["categoria"]) | set(current["categoria"]), key=str.casefold)
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
            loss_reason = category.removeprefix("Perdido — ") if category.startswith("Perdido — ") else ""
            stage_rows.append({
                "pipeline_id": "", "pipeline_nome": PIPELINE_NAME, "responsavel_id": "",
                "responsavel_nome": responsible, "categoria_relatorio": category,
                "status_id": "", "etapa_crm": category, "loss_reason_id": "",
                "motivo_perda_crm": loss_reason,
                "quantidade_anterior": previous_count, "percentual_anterior": previous_rate,
                "quantidade_atual": current_count, "percentual_atual": current_rate,
                "variacao_pp": pp(current_rate, previous_rate),
                "total_responsavel_anterior": previous_total_person,
                "total_responsavel_atual": current_total_person,
                "situacao_semana_atual": status, "data_hora_extracao": stamp,
            })
    write_csv(output_dir / "08_etapas_por_consultor.csv", CONSULTANT_STAGES_FIELDS, stage_rows)

    previous_losses = previous[previous["Etapa do lead"].map(is_lost)]
    current_losses = current[current["Etapa do lead"].map(is_lost)]
    previous_loss_counts = Counter(previous_losses["categoria"])
    current_loss_counts = Counter(current_losses["categoria"])
    total_previous_lost = len(previous_losses)
    total_current_lost = len(current_losses)
    loss_rows: list[dict[str, object]] = []
    for category in sorted(set(previous_loss_counts) | set(current_loss_counts), key=str.casefold):
        previous_count = previous_loss_counts[category]
        current_count = current_loss_counts[category]
        previous_rate = pct(previous_count, total_previous_lost)
        current_rate = pct(current_count, total_current_lost)
        reason = category.removeprefix("Perdido — ") if category.startswith("Perdido — ") else "Motivo não informado"
        loss_rows.append({
            "pipeline_id": "", "pipeline_nome": PIPELINE_NAME, "loss_reason_id": "",
            "motivo_perda": reason, "quantidade_anterior": previous_count,
            "percentual_anterior": previous_rate, "quantidade_atual": current_count,
            "percentual_atual": current_rate, "variacao_pp": pp(current_rate, previous_rate),
            "total_perdidos_anterior": total_previous_lost,
            "total_perdidos_atual": total_current_lost,
            "situacao_semana_atual": status, "data_hora_extracao": stamp,
        })
    write_csv(output_dir / "11_composicao_leads_perdidos.csv", LOST_COMPOSITION_FIELDS, loss_rows)

    movement_fields = ["status_dado", "motivo_indisponibilidade", *WEEKLY_MOVEMENT_FIELDS]
    movement_row = {field: "" for field in movement_fields}
    movement_row.update({
        "status_dado": "indisponivel",
        "motivo_indisponibilidade": "O arquivo não guarda o histórico completo de movimentações.",
        "situacao_semana_atual": status,
        "data_hora_extracao": stamp,
    })
    write_csv(output_dir / "05_movimentacao_semanal.csv", movement_fields, [movement_row])

    method_row = {field: "" for field in MOVEMENT_METHOD_FIELDS}
    method_row.update({
        "universo": "não disponível", "unidade_contagem": "não disponível",
        "nota_comparabilidade": "A fotografia exportada não permite reconstruir o histórico de movimentações.",
        "data_hora_extracao": stamp,
    })
    write_csv(output_dir / "06_nota_metodologica_movimentacao.csv", MOVEMENT_METHOD_FIELDS, [method_row])

    manual_path = manual_response_time_path(week_start)
    response_rows = build_manual_response_time_rows(manual_path, week_start, extracted_at)
    for row in response_rows:
        row["situacao_semana_atual"] = status
    write_csv(output_dir / "09_tempo_medio_resposta.csv", RESPONSE_TIME_FIELDS, response_rows)
    return output_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Consolida um export XLSX da Kommo em CSVs semanais.")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--week-start", type=parse_week_start, required=True)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output_dir = build_outputs(args.source.resolve(), args.week_start, args.output_root.resolve())
    print(f"Consolidados gerados: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
