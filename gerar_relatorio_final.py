from __future__ import annotations

import argparse
import csv
import html
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable, Sequence

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (
        Flowable,
        KeepTogether,
        ListFlowable,
        ListItem,
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
except ModuleNotFoundError as exc:  # pragma: no cover - depends on local install
    raise SystemExit(
        "Dependência ausente. Instale com: python -m pip install reportlab"
    ) from exc


ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT_ROOT = ROOT / "outputs"
PDF_FILENAME = "relatorio_desempenho_final.pdf"

WEEKLY_CSV_FILES = (
    "01_identificacao_periodo.csv",
    "04_conversao_responsavel.csv",
    "05_movimentacao_semanal.csv",
    "06_nota_metodologica_movimentacao.csv",
    "07_novos_leads_semana.csv",
    "08_etapas_por_consultor.csv",
    "09_tempo_medio_resposta.csv",
    "11_composicao_leads_perdidos.csv",
)
MONTHLY_CSV_FILES = (
    "02_distribuicao_mensal_responsavel.csv",
    "03_numeros_globais_etapas.csv",
    "13_analise_quantitativa_mes.csv",
    "14_resumo_consolidado_mes.csv",
)
WEEKLY_MARKDOWN_FILES = (
    "04_08_leitura_consultores.md",
    "04_10_mudancas_significativas.md",
    "04_12_leitura_gerencial_semana.md",
    "04_15_auditoria_crm.md",
    "04_16_amostragem_qualitativa.md",
    "04_17_diferencas_consultores.md",
    "04_18_limitacoes_proximos_passos.md",
)
MONTHLY_MARKDOWN_FILES = ("04_13_leitura_gerencial_mes.md",)

NAVY = colors.HexColor("#102A43")
NAVY_2 = colors.HexColor("#183B56")
BLUE = colors.HexColor("#2F80ED")
LIME = colors.HexColor("#B8F35B")
TEAL = colors.HexColor("#19A7A0")
CORAL = colors.HexColor("#F26B5B")
INK = colors.HexColor("#172B4D")
MUTED = colors.HexColor("#60758A")
LIGHT = colors.HexColor("#F3F7FA")
LINE = colors.HexColor("#D8E2EA")
WHITE = colors.white
CONTENT_WIDTH = A4[0] - 28 * mm


@dataclass(frozen=True)
class ValidationResult:
    week_dir: Path
    expected: tuple[Path, ...]
    missing: tuple[Path, ...]
    invalid: tuple[str, ...]
    closing_month: str | None

    @property
    def ok(self) -> bool:
        return not self.missing and not self.invalid


def parse_week_start(value: str) -> date:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Use a data no formato AAAA-MM-DD.") from exc
    if parsed.weekday() != 0:
        raise argparse.ArgumentTypeError("A data inicial deve ser uma segunda-feira.")
    return parsed


def closing_month_for_week(week_start: date) -> str | None:
    for offset in range(7):
        current = week_start + timedelta(days=offset)
        following = current + timedelta(days=1)
        if following.month != current.month:
            return current.strftime("%Y-%m")
    return None


def week_output_dir(output_root: Path, week_start: date) -> Path:
    return output_root / str(week_start.year) / week_start.isoformat()


def expected_output_paths(output_root: Path, week_start: date) -> tuple[Path, ...]:
    week_dir = week_output_dir(output_root, week_start)
    names: list[Path] = [week_dir / name for name in WEEKLY_CSV_FILES]
    names.extend(week_dir / "generativos" / name for name in WEEKLY_MARKDOWN_FILES)
    if closing_month_for_week(week_start):
        names.extend(week_dir / name for name in MONTHLY_CSV_FILES)
        names.extend(week_dir / "generativos" / name for name in MONTHLY_MARKDOWN_FILES)
    return tuple(names)


def validate_outputs(output_root: Path, week_start: date) -> ValidationResult:
    week_dir = week_output_dir(output_root, week_start)
    expected = expected_output_paths(output_root, week_start)
    missing = tuple(path for path in expected if not path.is_file())
    invalid: list[str] = []

    for path in expected:
        if not path.is_file():
            continue
        if path.stat().st_size == 0:
            invalid.append(f"Arquivo vazio: {path}")
            continue
        if path.suffix.lower() == ".csv":
            try:
                with path.open("r", encoding="utf-8-sig", newline="") as handle:
                    reader = csv.reader(handle)
                    header = next(reader, None)
                if not header or not any(cell.strip() for cell in header):
                    invalid.append(f"CSV sem cabeçalho: {path}")
            except (OSError, UnicodeError, csv.Error) as exc:
                invalid.append(f"CSV ilegível: {path} ({exc})")
        elif path.suffix.lower() == ".md":
            try:
                content = path.read_text(encoding="utf-8").strip()
            except (OSError, UnicodeError) as exc:
                invalid.append(f"Markdown ilegível: {path} ({exc})")
                continue
            if not content.startswith("## "):
                invalid.append(f"Markdown sem título de seção: {path}")

    identification = week_dir / "01_identificacao_periodo.csv"
    if identification.is_file():
        rows = read_csv(identification)
        if rows:
            recorded_start = rows[0].get("data_inicial", "")
            if recorded_start != week_start.isoformat():
                invalid.append(
                    "A data de 01_identificacao_periodo.csv não corresponde à "
                    f"semana solicitada: {recorded_start!r}."
                )

    return ValidationResult(
        week_dir=week_dir,
        expected=expected,
        missing=missing,
        invalid=tuple(invalid),
        closing_month=closing_month_for_week(week_start),
    )


def confirm_overwrite(path: Path, input_fn=input) -> bool:
    if not path.exists():
        return True
    try:
        answer = input_fn(
            f"O PDF já existe: {path}\nDeseja sobrescrevê-lo? [s/N]: "
        )
    except EOFError:
        return False
    return answer.strip().casefold() in {"s", "sim", "y", "yes"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def short_name(value: str) -> str:
    return value.split(" - ", 1)[0].strip() or "Não identificado"


def as_int(value: str | int | float | None) -> int:
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def as_float(value: str | int | float | None) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def decimal_br(value: float, digits: int = 1) -> str:
    return f"{value:.{digits}f}".replace(".", ",")


def pct(value: str | int | float | None) -> str:
    return f"{decimal_br(as_float(value))}%"


def pp(value: str | int | float | None) -> str:
    number = as_float(value)
    sign = "+" if number > 0 else ""
    return f"{sign}{decimal_br(number)} p.p."


def signed_int(value: int) -> str:
    return f"{value:+d}" if value else "0"


def human_date(value: str) -> str:
    parsed = date.fromisoformat(value)
    return parsed.strftime("%d/%m/%Y")


def register_fonts() -> None:
    candidates = {
        "Arial": Path("C:/Windows/Fonts/arial.ttf"),
        "Arial-Bold": Path("C:/Windows/Fonts/arialbd.ttf"),
        "Arial-Italic": Path("C:/Windows/Fonts/ariali.ttf"),
    }
    if all(path.is_file() for path in candidates.values()):
        for name, path in candidates.items():
            if name not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(name, str(path)))
        pdfmetrics.registerFontFamily(
            "Arial", normal="Arial", bold="Arial-Bold", italic="Arial-Italic"
        )
    else:  # pragma: no cover - Windows workspace normally has Arial
        global FONT, FONT_BOLD, FONT_ITALIC
        FONT, FONT_BOLD, FONT_ITALIC = "Helvetica", "Helvetica-Bold", "Helvetica-Oblique"


FONT = "Arial"
FONT_BOLD = "Arial-Bold"
FONT_ITALIC = "Arial-Italic"


def build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "h1": ParagraphStyle(
            "ReportH1",
            parent=base["Heading1"],
            fontName=FONT_BOLD,
            fontSize=19,
            leading=23,
            textColor=NAVY,
            spaceBefore=5 * mm,
            spaceAfter=3 * mm,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "ReportH2",
            parent=base["Heading2"],
            fontName=FONT_BOLD,
            fontSize=14,
            leading=18,
            textColor=NAVY_2,
            spaceBefore=4 * mm,
            spaceAfter=2 * mm,
            keepWithNext=True,
        ),
        "h3": ParagraphStyle(
            "ReportH3",
            parent=base["Heading3"],
            fontName=FONT_BOLD,
            fontSize=11.2,
            leading=14,
            textColor=BLUE,
            spaceBefore=3 * mm,
            spaceAfter=1.5 * mm,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "ReportBody",
            parent=base["BodyText"],
            fontName=FONT,
            fontSize=9.4,
            leading=13.3,
            textColor=INK,
            spaceAfter=2.5 * mm,
        ),
        "bullet": ParagraphStyle(
            "ReportBullet",
            parent=base["BodyText"],
            fontName=FONT,
            fontSize=9.2,
            leading=12.7,
            textColor=INK,
            leftIndent=0,
            spaceAfter=1 * mm,
        ),
        "note": ParagraphStyle(
            "ReportNote",
            parent=base["BodyText"],
            fontName=FONT_ITALIC,
            fontSize=8,
            leading=10.5,
            textColor=MUTED,
            backColor=LIGHT,
            borderColor=LINE,
            borderWidth=0.6,
            borderPadding=7,
            spaceBefore=1.5 * mm,
            spaceAfter=3 * mm,
        ),
        "source": ParagraphStyle(
            "ReportSource",
            parent=base["BodyText"],
            fontName=FONT,
            fontSize=6.8,
            leading=8.5,
            textColor=MUTED,
            spaceBefore=1.3 * mm,
            spaceAfter=2.5 * mm,
        ),
        "table": ParagraphStyle(
            "ReportTable",
            parent=base["BodyText"],
            fontName=FONT,
            fontSize=7.4,
            leading=9.2,
            textColor=INK,
            alignment=TA_LEFT,
        ),
        "table_header": ParagraphStyle(
            "ReportTableHeader",
            parent=base["BodyText"],
            fontName=FONT_BOLD,
            fontSize=7.2,
            leading=8.8,
            textColor=WHITE,
            alignment=TA_LEFT,
        ),
        "center": ParagraphStyle(
            "ReportCenter",
            parent=base["BodyText"],
            fontName=FONT,
            fontSize=9,
            leading=12,
            alignment=TA_CENTER,
            textColor=INK,
        ),
    }


class KpiGrid(Flowable):
    def __init__(self, cards: Sequence[tuple[str, str, str]], accents: Sequence[colors.Color]):
        super().__init__()
        self.cards = list(cards)
        self.accents = list(accents)
        self.height = 29 * mm

    def wrap(self, avail_width: float, avail_height: float) -> tuple[float, float]:
        self.width = avail_width
        return avail_width, self.height

    def draw(self) -> None:
        count = max(1, len(self.cards))
        gap = 3 * mm
        card_width = (self.width - gap * (count - 1)) / count
        for index, (label, value, detail) in enumerate(self.cards):
            x = index * (card_width + gap)
            accent = self.accents[index % len(self.accents)]
            self.canv.setFillColor(WHITE)
            self.canv.setStrokeColor(LINE)
            self.canv.setLineWidth(0.6)
            self.canv.roundRect(x, 0, card_width, self.height, 7, fill=1, stroke=1)
            self.canv.setFillColor(accent)
            self.canv.roundRect(x, self.height - 4, card_width, 4, 4, fill=1, stroke=0)
            self.canv.setFillColor(MUTED)
            self.canv.setFont(FONT_BOLD, 7.2)
            self.canv.drawString(x + 8, self.height - 17, label.upper()[:28])
            self.canv.setFillColor(NAVY)
            self.canv.setFont(FONT_BOLD, 18)
            self.canv.drawString(x + 8, self.height - 38, value[:18])
            self.canv.setFillColor(MUTED)
            self.canv.setFont(FONT, 7.1)
            self.canv.drawString(x + 8, 8, detail[:34])


def inline_markup(text: str) -> str:
    escaped = html.escape(text.strip())
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)
    escaped = re.sub(r"`(.+?)`", r"<font color='#2F80ED'>\1</font>", escaped)
    return escaped


def table_flowable(
    headers: Sequence[str],
    rows: Sequence[Sequence[object]],
    styles: dict[str, ParagraphStyle],
    widths: Sequence[float] | None = None,
) -> Table:
    if widths is None:
        widths = [CONTENT_WIDTH / len(headers)] * len(headers)
    header_cells = [Paragraph(inline_markup(str(cell)), styles["table_header"]) for cell in headers]
    body_cells = [
        [Paragraph(inline_markup(str(cell)), styles["table"]) for cell in row]
        for row in rows
    ]
    table = Table(
        [header_cells, *body_cells],
        colWidths=list(widths),
        repeatRows=1,
        hAlign="LEFT",
        splitByRow=1,
    )
    commands: list[tuple] = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY_2),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.45, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    for row_index in range(1, len(body_cells) + 1):
        commands.append(
            ("BACKGROUND", (0, row_index), (-1, row_index), WHITE if row_index % 2 else LIGHT)
        )
    table.setStyle(TableStyle(commands))
    return table


def add_source(story: list[Flowable], styles: dict[str, ParagraphStyle], *names: str) -> None:
    story.append(Paragraph(f"Fonte: {', '.join(names)}", styles["source"]))


def add_section_title(story: list[Flowable], styles: dict[str, ParagraphStyle], title: str) -> None:
    story.append(Paragraph(inline_markup(title), styles["h1"]))


def markdown_flowables(
    content: str,
    styles: dict[str, ParagraphStyle],
    *,
    skip_first_h2: bool = True,
) -> list[Flowable]:
    lines = content.replace("\r\n", "\n").split("\n")
    output: list[Flowable] = []
    index = 0
    skipped = False
    while index < len(lines):
        raw = lines[index].rstrip()
        stripped = raw.strip()
        if not stripped:
            index += 1
            continue
        if stripped.startswith("## "):
            if skip_first_h2 and not skipped:
                skipped = True
            else:
                output.append(Paragraph(inline_markup(stripped[3:]), styles["h1"]))
            index += 1
            continue
        if stripped.startswith("### "):
            output.append(Paragraph(inline_markup(stripped[4:]), styles["h2"]))
            index += 1
            continue
        if stripped.startswith("| ") and index + 1 < len(lines) and re.match(
            r"^\s*\|?\s*:?-+", lines[index + 1]
        ):
            table_lines = [stripped]
            index += 2
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index].strip())
                index += 1
            parsed = [[cell.strip() for cell in line.strip("|").split("|")] for line in table_lines]
            if len(parsed) >= 2:
                widths = [CONTENT_WIDTH / len(parsed[0])] * len(parsed[0])
                output.append(table_flowable(parsed[0], parsed[1:], styles, widths))
                output.append(Spacer(1, 2 * mm))
            continue
        if re.match(r"^[-*]\s+", stripped):
            items: list[ListItem] = []
            while index < len(lines) and re.match(r"^\s*[-*]\s+", lines[index]):
                item_text = re.sub(r"^\s*[-*]\s+", "", lines[index]).strip()
                items.append(ListItem(Paragraph(inline_markup(item_text), styles["bullet"])))
                index += 1
            output.append(ListFlowable(items, bulletType="bullet", leftIndent=14, bulletFontName=FONT))
            output.append(Spacer(1, 1.5 * mm))
            continue
        if re.match(r"^\d+\.\s+", stripped):
            items = []
            while index < len(lines):
                if not lines[index].strip():
                    next_index = index + 1
                    if next_index < len(lines) and re.match(
                        r"^\s*\d+\.\s+", lines[next_index]
                    ):
                        index = next_index
                        continue
                    break
                if not re.match(r"^\s*\d+\.\s+", lines[index]):
                    break
                item_text = re.sub(r"^\s*\d+\.\s+", "", lines[index]).strip()
                items.append(ListItem(Paragraph(inline_markup(item_text), styles["bullet"])))
                index += 1
            output.append(ListFlowable(items, bulletType="1", leftIndent=18, bulletFontName=FONT_BOLD))
            output.append(Spacer(1, 1.5 * mm))
            continue
        if stripped.startswith(">"):
            output.append(Paragraph(inline_markup(stripped.lstrip("> ")), styles["note"]))
            index += 1
            continue

        paragraph_lines = [stripped]
        index += 1
        while index < len(lines):
            candidate = lines[index].strip()
            if not candidate or candidate.startswith(("## ", "### ", "|", ">")):
                break
            if re.match(r"^[-*]\s+|^\d+\.\s+", candidate):
                break
            paragraph_lines.append(candidate)
            index += 1
        output.append(Paragraph(inline_markup(" ".join(paragraph_lines)), styles["body"]))
    return output


def load_markdown(week_dir: Path, name: str) -> str:
    return (week_dir / "generativos" / name).read_text(encoding="utf-8")


def executive_summary(
    week_dir: Path, styles: dict[str, ParagraphStyle]
) -> tuple[list[Flowable], list[tuple[str, str, str]]]:
    leads = read_csv(week_dir / "07_novos_leads_semana.csv")
    conversion = read_csv(week_dir / "04_conversao_responsavel.csv")
    movement = read_csv(week_dir / "05_movimentacao_semanal.csv")
    losses = read_csv(week_dir / "11_composicao_leads_perdidos.csv")

    previous_leads = as_int(leads[0].get("total_novos_leads_anterior")) if leads else 0
    current_leads = as_int(leads[0].get("total_novos_leads_atual")) if leads else 0
    lead_delta = current_leads - previous_leads
    previous_total = sum(as_int(row.get("total_leads_anterior")) for row in conversion)
    current_total = sum(as_int(row.get("total_leads_atual")) for row in conversion)
    previous_services = sum(as_int(row.get("servicos_iniciados_anterior")) for row in conversion)
    current_services = sum(as_int(row.get("servicos_iniciados_atual")) for row in conversion)
    previous_rate = previous_services / previous_total * 100 if previous_total else 0
    current_rate = current_services / current_total * 100 if current_total else 0
    rate_delta = current_rate - previous_rate
    previous_lost = as_int(losses[0].get("total_perdidos_anterior")) if losses else 0
    current_lost = as_int(losses[0].get("total_perdidos_atual")) if losses else 0
    leading_loss = max(losses, key=lambda row: as_int(row.get("quantidade_atual")), default={})
    movement_previous = as_int(movement[0].get("total_pares_usuario_lead_anterior")) if movement else 0
    movement_current = as_int(movement[0].get("total_pares_usuario_lead_atual")) if movement else 0

    bullets = [
        (
            f"<b>Entrada:</b> {current_leads} novos leads na semana, "
            f"{abs(lead_delta)} {'a menos' if lead_delta < 0 else 'a mais' if lead_delta > 0 else 'sem alteração'} "
            f"que os {previous_leads} da semana anterior."
        ),
        (
            f"<b>Conversão observada:</b> {current_services} serviços iniciados em "
            f"{current_total} leads ({decimal_br(current_rate)}%), variação de {pp(rate_delta)}."
        ),
        (
            f"<b>Perdas:</b> {current_lost} leads perdidos, contra {previous_lost}; "
            f"o motivo mais frequente foi {html.escape(leading_loss.get('motivo_perda', 'não identificado'))}."
        ),
        (
            f"<b>Operação registrada:</b> {movement_current} pares usuário-lead movimentados, "
            f"ante {movement_previous}. A métrica indica atividade no CRM, não qualidade do atendimento."
        ),
    ]
    flowables: list[Flowable] = [Paragraph("Executive Summary", styles["h1"])]
    flowables.append(
        ListFlowable(
            [ListItem(Paragraph(item, styles["bullet"])) for item in bullets],
            bulletType="bullet",
            leftIndent=14,
            bulletFontName=FONT,
        )
    )
    flowables.append(Spacer(1, 3 * mm))
    cards = [
        ("Novos leads", str(current_leads), f"{signed_int(lead_delta)} vs. semana anterior"),
        ("Serviços iniciados", f"{decimal_br(current_rate)}%", pp(rate_delta)),
        ("Leads perdidos", str(current_lost), f"{signed_int(current_lost - previous_lost)} casos"),
        ("Movimentações", str(movement_current), f"{signed_int(movement_current - movement_previous)} pares"),
    ]
    return flowables, cards


def add_weekly_tables(
    story: list[Flowable], week_dir: Path, styles: dict[str, ParagraphStyle]
) -> None:
    conversion = read_csv(week_dir / "04_conversao_responsavel.csv")
    add_section_title(story, styles, "4.4 Conversão por responsável")
    story.append(
        Paragraph(
            "A tabela compara coortes de entrada; as taxas usam o estado observado na data da extração e podem mudar com a maturação.",
            styles["body"],
        )
    )
    rows = [
        [
            short_name(row.get("responsavel_nome", "")),
            row.get("total_leads_anterior", ""),
            pct(row.get("taxa_conversao_anterior")),
            row.get("total_leads_atual", ""),
            pct(row.get("taxa_conversao_atual")),
            pp(row.get("variacao_pp")),
        ]
        for row in conversion
    ]
    story.append(
        table_flowable(
            ["Responsável", "Leads ant.", "Conv. ant.", "Leads atual", "Conv. atual", "Variação"],
            rows,
            styles,
            [42 * mm, 23 * mm, 25 * mm, 24 * mm, 25 * mm, 27 * mm],
        )
    )
    add_source(story, styles, "04_conversao_responsavel.csv")

    movement = read_csv(week_dir / "05_movimentacao_semanal.csv")
    add_section_title(story, styles, "4.5 Movimentação na última semana")
    story.append(
        Paragraph(
            "Movimentação representa pares distintos de usuário e lead com eventos registrados, e não o número de mensagens ou a qualidade comercial.",
            styles["body"],
        )
    )
    movement_rows = [
        [
            short_name(row.get("responsavel_nome", "")),
            row.get("atendimentos_semana_anterior", ""),
            pct(row.get("participacao_anterior")),
            row.get("atendimentos_semana_atual", ""),
            pct(row.get("participacao_atual")),
            pp(row.get("variacao_pp")),
        ]
        for row in movement
    ]
    story.append(
        table_flowable(
            ["Usuário", "Pares ant.", "Part. ant.", "Pares atual", "Part. atual", "Variação"],
            movement_rows,
            styles,
            [42 * mm, 23 * mm, 24 * mm, 24 * mm, 25 * mm, 28 * mm],
        )
    )
    add_source(story, styles, "05_movimentacao_semanal.csv")

    methodology = read_csv(week_dir / "06_nota_metodologica_movimentacao.csv")
    if methodology:
        row = methodology[0]
        story.append(Paragraph("4.6 Nota metodológica", styles["h2"]))
        note = (
            f"{row.get('unidade_contagem', '')}. {row.get('nota_comparabilidade', '')} "
            f"Eventos sem usuário excluídos: {row.get('eventos_sem_usuario_excluidos_anterior', '0')} "
            f"na semana anterior e {row.get('eventos_sem_usuario_excluidos_atual', '0')} na atual."
        )
        story.append(Paragraph(inline_markup(note), styles["note"]))

    leads = read_csv(week_dir / "07_novos_leads_semana.csv")
    add_section_title(story, styles, "4.7 Novos leads na semana")
    lead_rows = [
        [
            short_name(row.get("responsavel_nome", "")),
            row.get("novos_leads_anterior", ""),
            pct(row.get("participacao_anterior")),
            row.get("novos_leads_atual", ""),
            pct(row.get("participacao_atual")),
            signed_int(as_int(row.get("variacao_absoluta_responsavel"))),
        ]
        for row in leads
    ]
    story.append(
        table_flowable(
            ["Responsável", "Leads ant.", "Part. ant.", "Leads atual", "Part. atual", "Variação"],
            lead_rows,
            styles,
            [42 * mm, 23 * mm, 24 * mm, 24 * mm, 25 * mm, 28 * mm],
        )
    )
    add_source(story, styles, "07_novos_leads_semana.csv")


def add_consultant_section(
    story: list[Flowable], week_dir: Path, styles: dict[str, ParagraphStyle]
) -> None:
    add_section_title(story, styles, "4.8 Análise por consultor")
    stage_rows = read_csv(week_dir / "08_etapas_por_consultor.csv")
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in stage_rows:
        grouped[row.get("responsavel_nome", "Não identificado")].append(row)
    for responsible, rows in grouped.items():
        visible = [
            row
            for row in rows
            if as_int(row.get("quantidade_anterior")) or as_int(row.get("quantidade_atual"))
        ]
        story.append(Paragraph(short_name(responsible), styles["h2"]))
        table_rows = [
            [
                row.get("categoria_relatorio", ""),
                row.get("quantidade_atual", ""),
                pct(row.get("percentual_anterior")),
                pct(row.get("percentual_atual")),
                pp(row.get("variacao_pp")),
            ]
            for row in visible
        ]
        story.append(
            table_flowable(
                ["Etapa", "Qtd. atual", "% anterior", "% atual", "Variação"],
                table_rows,
                styles,
                [65 * mm, 22 * mm, 27 * mm, 25 * mm, 27 * mm],
            )
        )
        story.append(Spacer(1, 2 * mm))
    add_source(story, styles, "08_etapas_por_consultor.csv")
    story.extend(markdown_flowables(load_markdown(week_dir, "04_08_leitura_consultores.md"), styles))


def add_response_and_losses(
    story: list[Flowable], week_dir: Path, styles: dict[str, ParagraphStyle]
) -> None:
    add_section_title(story, styles, "4.9 Tempo médio de resposta")
    response = read_csv(week_dir / "09_tempo_medio_resposta.csv")
    if response and response[0].get("status_dado") == "indisponivel":
        story.append(
            Paragraph(
                inline_markup(
                    f"Dado indisponível: {response[0].get('motivo_indisponibilidade', 'motivo não informado')}"
                ),
                styles["note"],
            )
        )
    elif response:
        response_rows = [
            [
                short_name(row.get("responsavel_nome", "")),
                row.get("tempo_medio_minutos_anterior", ""),
                row.get("tempo_medio_minutos_atual", ""),
                row.get("variacao_minutos", ""),
            ]
            for row in response
        ]
        story.append(
            table_flowable(
                ["Responsável", "Min. anterior", "Min. atual", "Variação"],
                response_rows,
                styles,
                [65 * mm, 33 * mm, 33 * mm, 35 * mm],
            )
        )
    add_source(story, styles, "09_tempo_medio_resposta.csv")

    add_section_title(story, styles, "4.10 Mudanças significativas")
    story.extend(markdown_flowables(load_markdown(week_dir, "04_10_mudancas_significativas.md"), styles))
    add_source(story, styles, "04_10_mudancas_significativas.md")

    losses = read_csv(week_dir / "11_composicao_leads_perdidos.csv")
    add_section_title(story, styles, "4.11 Composição dos leads perdidos")
    story.append(
        Paragraph(
            "As participações usam como denominador o total de leads perdidos de cada semana.",
            styles["body"],
        )
    )
    loss_rows = [
        [
            row.get("motivo_perda", ""),
            row.get("quantidade_anterior", ""),
            pct(row.get("percentual_anterior")),
            row.get("quantidade_atual", ""),
            pct(row.get("percentual_atual")),
            pp(row.get("variacao_pp")),
        ]
        for row in losses
    ]
    story.append(
        table_flowable(
            ["Motivo", "Qtd. ant.", "% ant.", "Qtd. atual", "% atual", "Variação"],
            loss_rows,
            styles,
            [58 * mm, 21 * mm, 22 * mm, 22 * mm, 22 * mm, 26 * mm],
        )
    )
    add_source(story, styles, "11_composicao_leads_perdidos.csv")


def add_monthly_section(
    story: list[Flowable], week_dir: Path, styles: dict[str, ParagraphStyle]
) -> None:
    add_section_title(story, styles, "Fechamento mensal")
    summary = read_csv(week_dir / "14_resumo_consolidado_mes.csv")
    if summary:
        row = summary[0]
        cards = [
            ("Novos leads", row.get("novos_leads", "0"), "total do mês"),
            ("Serviços iniciados", pct(row.get("taxa_servicos_iniciados")), row.get("servicos_iniciados", "0") + " casos"),
            ("Perdidos", pct(row.get("taxa_perdidos")), row.get("perdidos", "0") + " casos"),
            ("Em aberto", str(as_int(row.get("agendados")) + as_int(row.get("em_andamento"))), "agendados + andamento"),
        ]
        story.append(KpiGrid(cards, [BLUE, LIME, CORAL, TEAL]))
        story.append(Spacer(1, 4 * mm))

    distribution = read_csv(week_dir / "02_distribuicao_mensal_responsavel.csv")
    story.append(Paragraph("4.2 Distribuição mensal por responsável", styles["h2"]))
    dist_rows = [
        [
            short_name(row.get("responsavel_nome", "")),
            row.get("quantidade_leads", ""),
            pct(row.get("participacao_percentual")),
            row.get("usuario_ativo", ""),
        ]
        for row in distribution
    ]
    story.append(
        table_flowable(
            ["Responsável", "Leads", "Participação", "Usuário ativo"],
            dist_rows,
            styles,
            [76 * mm, 28 * mm, 32 * mm, 30 * mm],
        )
    )
    add_source(story, styles, "02_distribuicao_mensal_responsavel.csv")

    global_rows = read_csv(week_dir / "03_numeros_globais_etapas.csv")
    aggregate: dict[str, int] = defaultdict(int)
    total = 0
    for row in global_rows:
        amount = as_int(row.get("quantidade_leads"))
        aggregate[row.get("categoria_relatorio", "Não identificado")] += amount
        total = max(total, as_int(row.get("total_geral")))
    visible = [(name, amount) for name, amount in aggregate.items() if amount]
    visible.sort(key=lambda pair: (-pair[1], pair[0]))
    story.append(Paragraph("4.3 Números globais por etapa", styles["h2"]))
    story.append(
        table_flowable(
            ["Etapa ou motivo", "Quantidade", "% do mês"],
            [[name, amount, f"{decimal_br(amount / total * 100 if total else 0)}%"] for name, amount in visible],
            styles,
            [92 * mm, 34 * mm, 40 * mm],
        )
    )
    add_source(story, styles, "03_numeros_globais_etapas.csv")

    monthly = read_csv(week_dir / "13_analise_quantitativa_mes.csv")
    story.append(Paragraph("4.13 Evolução semanal do mês", styles["h2"]))
    monthly_rows = [
        [
            f"S{row.get('semana_numero', '')} ({human_date(row.get('periodo_inicio', ''))[:5]}-{human_date(row.get('periodo_fim', ''))[:5]})",
            row.get("novos_leads", ""),
            f"{row.get('servicos_iniciados', '')} ({pct(row.get('taxa_servicos_iniciados'))})",
            f"{row.get('agendados', '')} ({pct(row.get('taxa_agendados'))})",
            f"{row.get('perdidos', '')} ({pct(row.get('taxa_perdidos'))})",
            f"{row.get('em_andamento', '')} ({pct(row.get('taxa_em_andamento'))})",
        ]
        for row in monthly
    ]
    story.append(
        table_flowable(
            ["Período", "Leads", "Serviços", "Agendados", "Perdidos", "Andamento"],
            monthly_rows,
            styles,
            [42 * mm, 20 * mm, 31 * mm, 27 * mm, 28 * mm, 28 * mm],
        )
    )
    add_source(story, styles, "13_analise_quantitativa_mes.csv", "14_resumo_consolidado_mes.csv")
    story.extend(markdown_flowables(load_markdown(week_dir, "04_13_leitura_gerencial_mes.md"), styles))
    add_source(story, styles, "04_13_leitura_gerencial_mes.md")


def add_management_narratives(
    story: list[Flowable], week_dir: Path, styles: dict[str, ParagraphStyle]
) -> None:
    add_section_title(story, styles, "4.12 Leitura gerencial da semana")
    story.extend(markdown_flowables(load_markdown(week_dir, "04_12_leitura_gerencial_semana.md"), styles))
    add_source(story, styles, "04_12_leitura_gerencial_semana.md")

    for number, title, filename in (
        ("4.15", "Auditoria de uso do CRM", "04_15_auditoria_crm.md"),
        ("4.16", "Amostragem qualitativa dos atendimentos", "04_16_amostragem_qualitativa.md"),
        ("4.17", "Diferenças observadas entre os consultores", "04_17_diferencas_consultores.md"),
        ("4.18", "Limitações e próximos passos", "04_18_limitacoes_proximos_passos.md"),
    ):
        add_section_title(story, styles, f"{number} {title}")
        story.extend(markdown_flowables(load_markdown(week_dir, filename), styles))
        add_source(story, styles, filename)


def draw_cover(canvas, doc, identification: dict[str, str]) -> None:
    width, height = A4
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, width, height, fill=1, stroke=0)
    canvas.setFillColor(NAVY_2)
    canvas.circle(width + 18 * mm, height - 25 * mm, 62 * mm, fill=1, stroke=0)
    canvas.setFillColor(BLUE)
    canvas.circle(width - 8 * mm, height - 10 * mm, 34 * mm, fill=1, stroke=0)
    canvas.setFillColor(LIME)
    canvas.rect(20 * mm, height - 42 * mm, 22 * mm, 3.2 * mm, fill=1, stroke=0)
    canvas.setFont(FONT_BOLD, 10)
    canvas.setFillColor(LIME)
    canvas.drawString(20 * mm, height - 58 * mm, "ADVANCED MECÂNICA")
    canvas.setFont(FONT_BOLD, 30)
    canvas.setFillColor(WHITE)
    canvas.drawString(20 * mm, height - 88 * mm, "Relatório de")
    canvas.drawString(20 * mm, height - 101 * mm, "desempenho comercial")
    canvas.setFont(FONT, 13)
    canvas.setFillColor(colors.HexColor("#C9D7E3"))
    canvas.drawString(20 * mm, height - 116 * mm, "Leitura executiva do funil de vendas")

    start = identification.get("data_inicial", "")
    end = identification.get("data_final", "")
    period = f"{human_date(start)} a {human_date(end)}" if start and end else "Período não identificado"
    canvas.setFillColor(WHITE)
    canvas.roundRect(20 * mm, height - 155 * mm, 92 * mm, 22 * mm, 7, fill=1, stroke=0)
    canvas.setFillColor(NAVY)
    canvas.setFont(FONT_BOLD, 11)
    canvas.drawString(27 * mm, height - 144 * mm, "PERÍODO ANALISADO")
    canvas.setFont(FONT, 12)
    canvas.drawString(27 * mm, height - 151 * mm, period)

    status = identification.get("situacao_semana", "não informado").upper()
    canvas.setFillColor(LIME)
    canvas.roundRect(20 * mm, height - 175 * mm, 48 * mm, 10 * mm, 5, fill=1, stroke=0)
    canvas.setFillColor(NAVY)
    canvas.setFont(FONT_BOLD, 8.5)
    canvas.drawCentredString(44 * mm, height - 171.5 * mm, f"SEMANA {status}")

    canvas.setFillColor(colors.HexColor("#9FB3C5"))
    canvas.setFont(FONT, 8)
    canvas.drawString(20 * mm, 24 * mm, "Gerado automaticamente a partir dos outputs validados da Kommo")
    canvas.drawRightString(width - 20 * mm, 24 * mm, datetime.now().strftime("%d/%m/%Y %H:%M"))
    canvas.restoreState()


def draw_body_chrome(canvas, doc) -> None:
    width, height = A4
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.5)
    canvas.line(14 * mm, height - 13 * mm, width - 14 * mm, height - 13 * mm)
    canvas.setFillColor(MUTED)
    canvas.setFont(FONT_BOLD, 7.2)
    canvas.drawString(14 * mm, height - 9.5 * mm, "ADVANCED MECÂNICA  •  DESEMPENHO COMERCIAL")
    canvas.setFont(FONT, 7.2)
    canvas.drawRightString(width - 14 * mm, 9 * mm, f"Página {doc.page}")
    canvas.setStrokeColor(LINE)
    canvas.line(14 * mm, 13 * mm, width - 14 * mm, 13 * mm)
    canvas.restoreState()


def generate_pdf(week_dir: Path, output_path: Path, week_start: date) -> None:
    register_fonts()
    styles = build_styles()
    identification_rows = read_csv(week_dir / "01_identificacao_periodo.csv")
    identification = identification_rows[0] if identification_rows else {}
    story: list[Flowable] = [PageBreak()]

    summary_flowables, cards = executive_summary(week_dir, styles)
    story.extend(summary_flowables)
    story.append(KpiGrid(cards, [BLUE, LIME, CORAL, TEAL]))
    story.append(Spacer(1, 4 * mm))
    story.append(
        Paragraph(
            "Os indicadores semanais comparam leads criados nas duas semanas e refletem seu estado na data de extração. Variações de taxa são apresentadas em pontos percentuais.",
            styles["note"],
        )
    )

    add_weekly_tables(story, week_dir, styles)
    add_consultant_section(story, week_dir, styles)
    add_response_and_losses(story, week_dir, styles)
    if closing_month_for_week(week_start):
        add_monthly_section(story, week_dir, styles)
    add_management_narratives(story, week_dir, styles)

    temp_path = output_path.with_name(output_path.name + ".tmp")
    temp_path.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(
        str(temp_path),
        pagesize=A4,
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="Relatório de desempenho comercial",
        author="Advanced Mecânica",
        subject=f"Semana iniciada em {week_start.isoformat()}",
        pageCompression=1,
    )
    document.build(
        story,
        onFirstPage=lambda canvas, doc: draw_cover(canvas, doc, identification),
        onLaterPages=draw_body_chrome,
    )
    os.replace(temp_path, output_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Valida os outputs semanais e gera o PDF executivo final."
    )
    parser.add_argument(
        "--week-start",
        required=True,
        type=parse_week_start,
        help="Primeiro dia da semana no formato AAAA-MM-DD (segunda-feira).",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="Raiz das pastas de outputs.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help=f"Caminho do PDF. Padrão: pasta semanal/{PDF_FILENAME}",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Sobrescreve o PDF existente sem perguntar.",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Apenas valida os outputs, sem gerar PDF.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output_root = args.output_root.resolve()
    result = validate_outputs(output_root, args.week_start)
    print(f"Pasta verificada: {result.week_dir}")
    print(f"Arquivos obrigatórios: {len(result.expected)}")

    if not result.ok:
        print("\nNão foi possível gerar o PDF.", file=sys.stderr)
        if result.missing:
            print("\nArquivos ausentes:", file=sys.stderr)
            for path in result.missing:
                print(f"  - {path}", file=sys.stderr)
        if result.invalid:
            print("\nArquivos inválidos:", file=sys.stderr)
            for message in result.invalid:
                print(f"  - {message}", file=sys.stderr)
        return 2

    print("Validação concluída: todos os outputs aplicáveis existem e são legíveis.")
    if args.validate_only:
        return 0

    output_path = (args.output or result.week_dir / PDF_FILENAME).resolve()
    if output_path.exists() and not args.force and not confirm_overwrite(output_path):
        print("PDF existente preservado.")
        return 0

    try:
        generate_pdf(result.week_dir, output_path, args.week_start)
    except Exception as exc:
        print(f"Erro ao gerar o PDF: {exc}", file=sys.stderr)
        return 1
    print(f"PDF gerado com sucesso: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
