from __future__ import annotations

import argparse
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
DEFAULT_OUTPUT_ROOT = ROOT / "outputs"
SUPPORTED_SUFFIXES = {".png", ".jpg", ".jpeg"}
EXPECTED_IMAGE_COUNT = 3
MANIFEST_NAME = "manifest.json"
COMBINED_NAME = "04_16_amostragem_qualitativa.md"
PROMPT_VERSION = "2026-08-18.1"
PROMPT_PATH = ROOT / "prompts" / "generativos" / "04_16_analise_atendimento_individual.prompt.md"


class ManualAttendanceError(ValueError):
    pass


@dataclass(frozen=True)
class AttendanceImage:
    slot: int
    path: Path
    sha256: str
    analysis_path: Path


@dataclass(frozen=True)
class AttendancePreparation:
    week_start: date
    input_dir: Path
    analysis_dir: Path
    combined_path: Path
    images: tuple[AttendanceImage, ...]

    @property
    def image_paths(self) -> tuple[Path, ...]:
        return tuple(image.path for image in self.images)


@dataclass(frozen=True)
class AttendanceArtifacts:
    input_dir: Path
    analysis_dir: Path
    combined_path: Path
    image_paths: tuple[Path, ...]
    reused: bool


INDIVIDUAL_PROMPT = """Você é um analista comercial especializado em oficinas mecânicas.
Analise somente o print anexado. Ele representa um único atendimento e pode mostrar apenas
parte da conversa. Não use nem suponha informações de outros casos.

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
- Separe fato visível de hipótese. Se o print estiver cortado ou ilegível, diga exatamente o limite.
- Não reproduza nome, telefone, placa, endereço ou qualquer dado pessoal que apareça na imagem.
- Não faça julgamento geral do consultor com base em um único atendimento.
- Não invente falas, valores, defeitos, serviços ou etapas que não estejam visíveis.
- Seja prático, específico e respeitoso.

Entregue em Markdown, sem título numerado, usando exatamente esta estrutura:
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
Uma frase sobre o que o print não permite concluir.
"""


def attendance_input_dir(input_root: Path, week_start: date) -> Path:
    return input_root / week_start.isoformat()


def attendance_output_dir(output_root: Path, week_start: date) -> Path:
    return output_root / f"{week_start.year:04d}" / week_start.isoformat() / "generativos"


def find_attendance_images(directory: Path) -> tuple[Path, ...]:
    if not directory.is_dir():
        raise ManualAttendanceError(f"Pasta dos atendimentos não encontrada: {directory}")
    images = tuple(
        sorted(
            (
                path
                for path in directory.iterdir()
                if path.is_file() and path.suffix.casefold() in SUPPORTED_SUFFIXES
            ),
            key=lambda path: path.name.casefold(),
        )
    )
    if len(images) != EXPECTED_IMAGE_COUNT:
        raise ManualAttendanceError(
            f"A pasta {directory} deve conter exatamente 3 prints PNG/JPG; foram encontrados {len(images)}."
        )
    for path in images:
        validate_image_signature(path)
    return images


def validate_image_signature(path: Path) -> None:
    data = path.read_bytes()[:16]
    suffix = path.suffix.casefold()
    valid = data.startswith(b"\x89PNG\r\n\x1a\n") if suffix == ".png" else data.startswith(b"\xff\xd8\xff")
    if not valid:
        raise ManualAttendanceError(f"O arquivo não parece ser uma imagem {suffix}: {path}")


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
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    create_output_dirs: bool = True,
) -> AttendancePreparation:
    """Valida os prints e devolve o contrato de arquivos para os subagentes."""
    input_dir = attendance_input_dir(input_root, week_start)
    image_paths = find_attendance_images(input_dir)
    generative_dir = attendance_output_dir(output_root, week_start)
    analysis_dir = generative_dir / "atendimentos"
    combined_path = generative_dir / COMBINED_NAME
    if create_output_dirs:
        analysis_dir.mkdir(parents=True, exist_ok=True)
    images = tuple(
        AttendanceImage(index, path, sha256_file(path), analysis_dir / f"{index:02d}_analise.md")
        for index, path in enumerate(image_paths, 1)
    )
    return AttendancePreparation(week_start, input_dir, analysis_dir, combined_path, images)


def preparation_payload(preparation: AttendancePreparation) -> dict[str, object]:
    return {
        "week_start": preparation.week_start.isoformat(),
        "input_dir": str(preparation.input_dir),
        "analysis_dir": str(preparation.analysis_dir),
        "combined_path": str(preparation.combined_path),
        "prompt_path": str(PROMPT_PATH),
        "prompt_version": PROMPT_VERSION,
        "images": [
            {
                "slot": image.slot,
                "path": str(image.path),
                "sha256": image.sha256,
                "analysis_path": str(image.analysis_path),
            }
            for image in preparation.images
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
    for image in preparation.images:
        validate_markdown_file(image.analysis_path, f"Análise do atendimento {image.slot}")
        analyses.append(
            {"slot": image.slot, "filename": image.analysis_path.name, "sha256": sha256_file(image.analysis_path)}
        )
    validate_markdown_file(preparation.combined_path, "Análise qualitativa consolidada")
    return {
        "version": 2,
        "week_start": preparation.week_start.isoformat(),
        "prompt_version": PROMPT_VERSION,
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "images": [
            {"slot": image.slot, "filename": image.path.name, "sha256": image.sha256}
            for image in preparation.images
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
        preparation.image_paths, reused,
    )


def finalize_attendances(
    week_start: date,
    *,
    input_root: Path = DEFAULT_INPUT_ROOT,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> AttendanceArtifacts:
    preparation = prepare_attendances(week_start, input_root=input_root, output_root=output_root)
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
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> AttendanceArtifacts:
    preparation = prepare_attendances(
        week_start, input_root=input_root, output_root=output_root, create_output_dirs=False,
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
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    force: bool = False,
    validate_only: bool = False,
    input_fn: Callable[[str], str] = input,
) -> AttendanceArtifacts:
    """Compatibilidade com o gerador: apenas valida artefatos feitos externamente."""
    del force, validate_only, input_fn
    return validate_attendance_artifacts(week_start, input_root=input_root, output_root=output_root)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepara e valida análises de três prints produzidas por subagentes externos."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command, help_text in (
        ("prepare", "Valida prints e imprime caminhos e hashes para os subagentes."),
        ("finalize", "Valida os Markdown gerados e registra o manifesto."),
        ("validate", "Confere se imagens, textos e manifesto continuam atuais."),
    ):
        command_parser = subparsers.add_parser(command, help=help_text)
        command_parser.add_argument("--week-start", required=True, type=parse_week_start, metavar="AAAA-MM-DD")
        command_parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT_ROOT)
        command_parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    common = {"input_root": args.input_root.resolve(), "output_root": args.output_root.resolve()}
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
