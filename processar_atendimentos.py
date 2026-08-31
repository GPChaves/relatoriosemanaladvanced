from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import tempfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable, Sequence

from relatorio import parse_week_start


ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT_ROOT = ROOT / "entradas_manuais" / "atendimentos"
DEFAULT_MANAGER_INPUT_ROOT = ROOT / "entradas_manuais" / "avaliacao_gestor"
DEFAULT_OUTPUT_ROOT = ROOT / "outputs"
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg"}
TEXT_SUFFIXES = {".txt"}
SUPPORTED_SUFFIXES = IMAGE_SUFFIXES | TEXT_SUFFIXES
EXPECTED_ATTENDANCE_COUNT = 3
# Compatibilidade com integrações anteriores.
EXPECTED_IMAGE_COUNT = EXPECTED_ATTENDANCE_COUNT
MANIFEST_NAME = "manifest.json"
METADATA_NAME = "atendimentos.csv"
COMBINED_NAME = "04_16_amostragem_qualitativa.md"
PROMPT_VERSION = "2026-08-29.1"
PROMPT_PATH = ROOT / "prompts" / "generativos" / "04_16_analise_atendimento_individual.prompt.md"


class ManualAttendanceError(ValueError):
    pass


@dataclass(frozen=True)
class AttendanceSource:
    slot: int
    path: Path
    sha256: str
    analysis_path: Path
    customer_name: str
    lead_id: int

    @property
    def source_type(self) -> str:
        return "text" if self.path.suffix.casefold() in TEXT_SUFFIXES else "image"

    @property
    def report_title(self) -> str:
        return f"## Atendimento — {self.customer_name} — Lead {self.lead_id}"


AttendanceImage = AttendanceSource


@dataclass(frozen=True)
class AttendancePreparation:
    week_start: date
    input_dir: Path
    analysis_dir: Path
    combined_path: Path
    sources: tuple[AttendanceSource, ...]
    manager_assessment_path: Path | None = None

    @property
    def source_paths(self) -> tuple[Path, ...]:
        return tuple(source.path for source in self.sources)

    @property
    def images(self) -> tuple[AttendanceSource, ...]:
        """Compatibilidade: antes todas as fontes eram imagens."""
        return self.sources

    @property
    def image_paths(self) -> tuple[Path, ...]:
        return self.source_paths


@dataclass(frozen=True)
class AttendanceArtifacts:
    input_dir: Path
    analysis_dir: Path
    combined_path: Path
    source_paths: tuple[Path, ...]
    reused: bool

    @property
    def image_paths(self) -> tuple[Path, ...]:
        """Compatibilidade: contém todas as fontes, inclusive textos."""
        return self.source_paths


INDIVIDUAL_PROMPT = """Você é um analista comercial especializado em oficinas mecânicas.
Analise somente a fonte fornecida. Ela representa um único atendimento e pode ser um print
ou uma transcrição parcial da conversa. Não use nem suponha informações de outros casos.
O envelope fornece CLIENTE_NOME e LEAD_ID. Use esses valores no título obrigatório.

Avalie, com linguagem simples para o dono de uma oficina:
- entendimento da necessidade, veículo e serviço pedido;
- qualidade das perguntas técnicas e da investigação do problema;
- clareza da explicação e segurança técnica, sem inventar diagnóstico;
- proatividade para remover obstáculos e conduzir o cliente ao próximo passo;
- técnica de conversão: proposta de valor, agendamento, urgência legítima e fechamento;
- tratamento de objeções de preço, prazo, distância, confiança ou disponibilidade;
- follow-up e clareza do próximo passo;
- coerência entre a conversa e o encerramento ou etapa do CRM, quando isso estiver visível.

Regras obrigatórias:
- Separe fato observado de hipótese. Se a imagem estiver cortada/ilegível ou o texto estiver incompleto, diga exatamente o limite.
- Além de CLIENTE_NOME no título, não reproduza telefone, placa, endereço ou outros dados pessoais.
- Não faça julgamento geral do consultor com base em um único atendimento.
- Não invente falas, valores, defeitos, serviços ou etapas que não estejam visíveis.
- Seja prático, específico e respeitoso.

Entregue em Markdown usando exatamente esta estrutura:
## Atendimento — CLIENTE_NOME — Lead LEAD_ID

**Resumo do que aparece**
Um parágrafo curto.

**Pontos fortes**
- até 3 itens.

**O que pode melhorar**
- até 3 itens.

**Melhor próximo passo**
Uma ação objetiva.

**Exemplo de resposta melhor**
Uma mensagem curta que o consultor poderia enviar, somente se o contexto visível permitir.

**Limite da análise**
Uma frase sobre o que a fonte não permite concluir.
"""


def attendance_input_dir(input_root: Path, week_start: date) -> Path:
    return input_root / week_start.isoformat()


def attendance_output_dir(output_root: Path, week_start: date) -> Path:
    return output_root / f"{week_start.year:04d}" / week_start.isoformat() / "generativos"


def optional_manager_assessment_path(
    manager_input_root: Path, week_start: date
) -> Path | None:
    path = manager_input_root / week_start.isoformat() / "avaliacao.md"
    if not path.exists():
        return None
    if not path.is_file():
        raise ManualAttendanceError(f"A avaliação opcional do gestor não é um arquivo: {path}")
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ManualAttendanceError(
            f"A avaliação opcional do gestor deve estar em UTF-8: {path}"
        ) from exc
    if not text.strip():
        raise ManualAttendanceError(f"A avaliação opcional do gestor está vazia: {path}")
    if "\x00" in text:
        raise ManualAttendanceError(
            f"A avaliação opcional do gestor contém bytes nulos: {path}"
        )
    return path


def find_attendance_sources(directory: Path) -> tuple[Path, ...]:
    if not directory.is_dir():
        raise ManualAttendanceError(f"Pasta dos atendimentos não encontrada: {directory}")
    sources = tuple(
        sorted(
            (
                path
                for path in directory.iterdir()
                if path.is_file() and path.suffix.casefold() in SUPPORTED_SUFFIXES
            ),
            key=lambda path: path.name.casefold(),
        )
    )
    if len(sources) != EXPECTED_ATTENDANCE_COUNT:
        raise ManualAttendanceError(
            f"A pasta {directory} deve conter exatamente 3 atendimentos em PNG, JPG ou TXT; "
            f"foram encontrados {len(sources)}."
        )
    for path in sources:
        validate_attendance_source(path)
    return sources


def find_attendance_images(directory: Path) -> tuple[Path, ...]:
    """Compatibilidade: retorna as três fontes, que agora também podem ser TXT."""
    return find_attendance_sources(directory)


def validate_attendance_source(path: Path) -> None:
    if path.suffix.casefold() in TEXT_SUFFIXES:
        validate_text_source(path)
    else:
        validate_image_signature(path)


def validate_image_signature(path: Path) -> None:
    data = path.read_bytes()[:16]
    suffix = path.suffix.casefold()
    valid = data.startswith(b"\x89PNG\r\n\x1a\n") if suffix == ".png" else data.startswith(b"\xff\xd8\xff")
    if not valid:
        raise ManualAttendanceError(f"O arquivo não parece ser uma imagem {suffix}: {path}")


def validate_text_source(path: Path) -> None:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ManualAttendanceError(f"A conversa em texto deve estar em UTF-8: {path}") from exc
    if not text.strip():
        raise ManualAttendanceError(f"A conversa em texto está vazia: {path}")
    if "\x00" in text:
        raise ManualAttendanceError(f"A conversa em texto contém bytes nulos: {path}")


def load_attendance_metadata(directory: Path) -> dict[int, tuple[str, int]]:
    path = directory / METADATA_NAME
    if not path.is_file():
        raise ManualAttendanceError(
            f"Metadados dos atendimentos não encontrados: {path}. "
            "Informe atendimento, cliente_nome e lead_id."
        )
    try:
        raw = path.read_text(encoding="utf-8-sig")
        dialect = csv.Sniffer().sniff(raw[:4096], delimiters=";,")
        rows = list(csv.DictReader(raw.splitlines(), dialect=dialect))
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        raise ManualAttendanceError(f"Metadados dos atendimentos inválidos: {path}") from exc
    required = {"atendimento", "cliente_nome", "lead_id"}
    if not rows or not required.issubset(rows[0]):
        raise ManualAttendanceError(
            f"{path} deve conter as colunas atendimento, cliente_nome e lead_id."
        )
    metadata: dict[int, tuple[str, int]] = {}
    for row in rows:
        try:
            slot = int(str(row.get("atendimento") or "").strip())
            lead_id = int(str(row.get("lead_id") or "").strip())
        except ValueError as exc:
            raise ManualAttendanceError(
                f"Atendimento e lead_id devem ser inteiros em {path}."
            ) from exc
        customer_name = str(row.get("cliente_nome") or "").strip()
        if slot not in {1, 2, 3} or slot in metadata:
            raise ManualAttendanceError(
                f"{path} deve ter uma única linha para cada atendimento 1, 2 e 3."
            )
        if not customer_name or lead_id <= 0:
            raise ManualAttendanceError(
                f"O atendimento {slot} precisa de cliente_nome e lead_id positivo."
            )
        metadata[slot] = (customer_name, lead_id)
    if set(metadata) != {1, 2, 3}:
        raise ManualAttendanceError(
            f"{path} deve ter uma única linha para cada atendimento 1, 2 e 3."
        )
    return metadata


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_individual_prompt() -> str:
    if PROMPT_PATH.is_file():
        prompt = PROMPT_PATH.read_text(encoding="utf-8").strip()
        if prompt:
            return prompt
    return INDIVIDUAL_PROMPT.strip()


def prepare_attendances(
    week_start: date,
    *,
    input_root: Path = DEFAULT_INPUT_ROOT,
    manager_input_root: Path = DEFAULT_MANAGER_INPUT_ROOT,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    create_output_dirs: bool = True,
) -> AttendancePreparation:
    """Valida três fontes de atendimento e devolve o contrato dos subagentes."""
    input_dir = attendance_input_dir(input_root, week_start)
    source_paths = find_attendance_sources(input_dir)
    metadata = load_attendance_metadata(input_dir)
    generative_dir = attendance_output_dir(output_root, week_start)
    analysis_dir = generative_dir / "atendimentos"
    combined_path = generative_dir / COMBINED_NAME
    manager_assessment = optional_manager_assessment_path(
        manager_input_root, week_start
    )
    if create_output_dirs:
        analysis_dir.mkdir(parents=True, exist_ok=True)
    sources = tuple(
        AttendanceSource(
            index,
            path,
            sha256_file(path),
            analysis_dir / f"{index:02d}_analise.md",
            metadata[index][0],
            metadata[index][1],
        )
        for index, path in enumerate(source_paths, 1)
    )
    return AttendancePreparation(
        week_start,
        input_dir,
        analysis_dir,
        combined_path,
        sources,
        manager_assessment,
    )


def preparation_payload(preparation: AttendancePreparation) -> dict[str, object]:
    return {
        "week_start": preparation.week_start.isoformat(),
        "input_dir": str(preparation.input_dir),
        "analysis_dir": str(preparation.analysis_dir),
        "combined_path": str(preparation.combined_path),
        "prompt_path": str(PROMPT_PATH),
        "prompt_version": PROMPT_VERSION,
        "avaliacao_gestor_path": (
            str(preparation.manager_assessment_path)
            if preparation.manager_assessment_path is not None
            else None
        ),
        "sources": [
            {
                "slot": source.slot,
                "type": source.source_type,
                "path": str(source.path),
                "sha256": source.sha256,
                "analysis_path": str(source.analysis_path),
                "cliente_nome": source.customer_name,
                "lead_id": source.lead_id,
                "titulo_obrigatorio": source.report_title,
            }
            for source in preparation.sources
        ],
    }


def validate_markdown_file(path: Path, description: str) -> str:
    if not path.is_file():
        raise ManualAttendanceError(f"{description} não encontrado: {path}")
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ManualAttendanceError(f"{description} deve estar em UTF-8: {path}") from exc
    if not text.strip():
        raise ManualAttendanceError(f"{description} está vazio: {path}")
    if "\x00" in text:
        raise ManualAttendanceError(f"{description} contém bytes nulos: {path}")
    return text


def expected_manifest(preparation: AttendancePreparation) -> dict[str, object]:
    prompt = load_individual_prompt()
    analyses = []
    for source in preparation.sources:
        analysis = validate_markdown_file(
            source.analysis_path, f"Análise do atendimento {source.slot}"
        )
        first_line = next(
            (line.strip() for line in analysis.splitlines() if line.strip()), ""
        )
        if first_line != source.report_title:
            raise ManualAttendanceError(
                f"A análise do atendimento {source.slot} deve começar com "
                f"{source.report_title!r}."
            )
        analyses.append(
            {
                "slot": source.slot,
                "filename": source.analysis_path.name,
                "sha256": sha256_file(source.analysis_path),
            }
        )
    combined = validate_markdown_file(
        preparation.combined_path, "Análise qualitativa consolidada"
    )
    for source in preparation.sources:
        consolidated_title = source.report_title.replace("## ", "### ", 1)
        if consolidated_title not in combined:
            raise ManualAttendanceError(
                "A análise qualitativa consolidada deve preservar o título "
                f"{consolidated_title!r}."
            )
    return {
        "version": 5,
        "week_start": preparation.week_start.isoformat(),
        "prompt_version": PROMPT_VERSION,
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "manager_assessment": (
            {
                "filename": preparation.manager_assessment_path.name,
                "sha256": sha256_file(preparation.manager_assessment_path),
            }
            if preparation.manager_assessment_path is not None
            else None
        ),
        "sources": [
            {
                "slot": source.slot,
                "type": source.source_type,
                "filename": source.path.name,
                "sha256": source.sha256,
                "cliente_nome": source.customer_name,
                "lead_id": source.lead_id,
            }
            for source in preparation.sources
        ],
        "analyses": analyses,
        "combined": {"filename": preparation.combined_path.name, "sha256": sha256_file(preparation.combined_path)},
    }


def _write_manifest_atomic(path: Path, manifest: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", newline="\n", prefix=f".{path.name}.", suffix=".tmp",
        dir=path.parent, delete=False,
    ) as stream:
        temporary_path = Path(stream.name)
        json.dump(manifest, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    try:
        os.replace(temporary_path, path)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise


def _as_artifacts(preparation: AttendancePreparation, *, reused: bool) -> AttendanceArtifacts:
    return AttendanceArtifacts(
        preparation.input_dir, preparation.analysis_dir, preparation.combined_path,
        preparation.source_paths, reused,
    )


def finalize_attendances(
    week_start: date,
    *,
    input_root: Path = DEFAULT_INPUT_ROOT,
    manager_input_root: Path = DEFAULT_MANAGER_INPUT_ROOT,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> AttendanceArtifacts:
    preparation = prepare_attendances(
        week_start,
        input_root=input_root,
        manager_input_root=manager_input_root,
        output_root=output_root,
    )
    manifest = expected_manifest(preparation)
    _write_manifest_atomic(preparation.analysis_dir / MANIFEST_NAME, manifest)
    return _as_artifacts(preparation, reused=False)


def artifacts_are_current(analysis_dir: Path, combined_path: Path, expected: dict[str, object]) -> bool:
    manifest_path = analysis_dir / MANIFEST_NAME
    if not manifest_path.is_file() or not combined_path.is_file():
        return False
    try:
        actual = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False
    return actual == expected


def validate_attendance_artifacts(
    week_start: date,
    *,
    input_root: Path = DEFAULT_INPUT_ROOT,
    manager_input_root: Path = DEFAULT_MANAGER_INPUT_ROOT,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> AttendanceArtifacts:
    preparation = prepare_attendances(
        week_start,
        input_root=input_root,
        manager_input_root=manager_input_root,
        output_root=output_root,
        create_output_dirs=False,
    )
    try:
        expected = expected_manifest(preparation)
    except ManualAttendanceError as exc:
        raise ManualAttendanceError(
            f"Artefatos dos atendimentos incompletos. Execute subagentes externos e depois 'finalize': {exc}"
        ) from exc
    if not artifacts_are_current(preparation.analysis_dir, preparation.combined_path, expected):
        raise ManualAttendanceError(
            "O manifesto dos atendimentos está ausente ou desatualizado. Execute 'finalize' depois "
            "que os subagentes escreverem as três análises e o consolidado."
        )
    return _as_artifacts(preparation, reused=True)


def process_attendances(
    week_start: date,
    *,
    input_root: Path = DEFAULT_INPUT_ROOT,
    manager_input_root: Path = DEFAULT_MANAGER_INPUT_ROOT,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    force: bool = False,
    validate_only: bool = False,
    input_fn: Callable[[str], str] = input,
) -> AttendanceArtifacts:
    """Compatibilidade com o gerador: apenas valida artefatos feitos externamente."""
    del force, validate_only, input_fn
    return validate_attendance_artifacts(
        week_start,
        input_root=input_root,
        manager_input_root=manager_input_root,
        output_root=output_root,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepara e valida três atendimentos em imagem ou texto analisados por subagentes."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command, help_text in (
        ("prepare", "Valida três fontes e imprime tipos, caminhos e hashes para os subagentes."),
        ("finalize", "Valida os Markdown gerados e registra o manifesto."),
        ("validate", "Confere se fontes, análises e manifesto continuam atuais."),
    ):
        command_parser = subparsers.add_parser(command, help=help_text)
        command_parser.add_argument("--week-start", required=True, type=parse_week_start, metavar="AAAA-MM-DD")
        command_parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT_ROOT)
        command_parser.add_argument(
            "--manager-input-root", type=Path, default=DEFAULT_MANAGER_INPUT_ROOT
        )
        command_parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    common = {
        "input_root": args.input_root.resolve(),
        "manager_input_root": args.manager_input_root.resolve(),
        "output_root": args.output_root.resolve(),
    }
    try:
        if args.command == "prepare":
            preparation = prepare_attendances(args.week_start, **common)
            print(json.dumps(preparation_payload(preparation), ensure_ascii=False, indent=2))
            return 0
        if args.command == "finalize":
            result = finalize_attendances(args.week_start, **common)
            print(f"Manifesto registrado: {result.analysis_dir / MANIFEST_NAME}")
            return 0
        result = validate_attendance_artifacts(args.week_start, **common)
    except (ManualAttendanceError, OSError, ValueError) as exc:
        print(f"Erro nos atendimentos manuais: {exc}", file=sys.stderr)
        return 2
    print(f"Artefatos atuais: {result.analysis_dir}")
    print(f"Consolidado atual: {result.combined_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
