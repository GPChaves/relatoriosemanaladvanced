from __future__ import annotations

import argparse
import base64
import hashlib
import json
import mimetypes
import os
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Callable, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from relatorio import load_env_file, parse_week_start, report_timezone


ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT_ROOT = ROOT / "entradas_manuais" / "atendimentos"
DEFAULT_OUTPUT_ROOT = ROOT / "outputs"
SUPPORTED_SUFFIXES = {".png", ".jpg", ".jpeg"}
EXPECTED_IMAGE_COUNT = 3
MANIFEST_NAME = "manifest.json"
COMBINED_NAME = "04_16_amostragem_qualitativa.md"
PROMPT_VERSION = "2026-08-18.1"
DEFAULT_MODEL = "gpt-5.6-terra"
PROMPT_PATH = ROOT / "prompts" / "generativos" / "04_16_analise_atendimento_individual.prompt.md"


class ManualAttendanceError(ValueError):
    pass


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


def image_data_url(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def extract_response_text(payload: dict[str, object]) -> str:
    direct = payload.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()
    parts: list[str] = []
    output = payload.get("output")
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if isinstance(block, dict) and block.get("type") == "output_text":
                    text = block.get("text")
                    if isinstance(text, str) and text.strip():
                        parts.append(text.strip())
    if not parts:
        raise ManualAttendanceError("A API não devolveu texto para a análise do atendimento.")
    return "\n\n".join(parts)


def load_individual_prompt() -> str:
    if PROMPT_PATH.is_file():
        prompt = PROMPT_PATH.read_text(encoding="utf-8").strip()
        if prompt:
            return prompt
    return INDIVIDUAL_PROMPT.strip()


def analyze_image_with_openai(path: Path, slot: int, model: str, prompt: str) -> str:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ManualAttendanceError(
            "OPENAI_API_KEY não foi definida em env.txt. Ela é necessária para analisar os três prints."
        )
    payload = {
        "model": model,
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_url": image_data_url(path), "detail": "high"},
                ],
            }
        ],
    }
    request = Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=240) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:600]
        raise ManualAttendanceError(f"Erro da OpenAI ao analisar o atendimento {slot}: HTTP {exc.code} - {detail}") from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ManualAttendanceError(f"Falha ao analisar o atendimento {slot}: {exc}") from exc
    if not isinstance(result, dict):
        raise ManualAttendanceError(f"Resposta inválida da OpenAI no atendimento {slot}.")
    return extract_response_text(result)


def combined_markdown(images: Sequence[Path], analyses: Sequence[str]) -> str:
    sections = [
        "## Revisão da qualidade dos atendimentos",
        "",
        "> Foram analisados exatamente três prints, cada um por um agente independente. A amostra ajuda a encontrar pontos práticos, mas não representa sozinha todo o trabalho da equipe.",
    ]
    for index, (image_path, analysis) in enumerate(zip(images, analyses), 1):
        sections.extend(
            [
                "",
                f"### Atendimento {index}",
                "",
                analysis.strip(),
            ]
        )
    sections.extend(
        [
            "",
            "> Nomes, telefones, placas e outros dados pessoais não são repetidos no relatório. Os prints originais também não são inseridos no PDF.",
            "",
        ]
    )
    return "\n".join(sections)


def expected_manifest(images: Sequence[Path], model: str, prompt: str) -> dict[str, object]:
    return {
        "version": 1,
        "prompt_version": PROMPT_VERSION,
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "model": model,
        "images": [
            {"slot": index, "filename": path.name, "sha256": sha256_file(path)}
            for index, path in enumerate(images, 1)
        ],
    }


def artifacts_are_current(
    analysis_dir: Path,
    combined_path: Path,
    expected: dict[str, object],
) -> bool:
    manifest_path = analysis_dir / MANIFEST_NAME
    if not manifest_path.is_file() or not combined_path.is_file():
        return False
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    for key in ("version", "prompt_version", "prompt_sha256", "model", "images"):
        if manifest.get(key) != expected.get(key):
            return False
    return all((analysis_dir / f"{index:02d}_analise.md").is_file() for index in range(1, 4))


def confirm_reanalysis(paths: Sequence[Path], input_fn: Callable[[str], str] = input) -> bool:
    existing = [path for path in paths if path.exists()]
    if not existing:
        return True
    print("As análises abaixo já existem ou estão desatualizadas:")
    for path in existing:
        print(f"  - {path}")
    answer = input_fn("Deseja analisar novamente e sobrescrever esses arquivos? [s/N]: ")
    return answer.strip().casefold() in {"s", "sim", "y", "yes"}


def process_attendances(
    week_start: date,
    *,
    input_root: Path = DEFAULT_INPUT_ROOT,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    force: bool = False,
    validate_only: bool = False,
    input_fn: Callable[[str], str] = input,
    analyze_fn: Callable[[Path, int, str, str], str] | None = None,
) -> AttendanceArtifacts:
    input_dir = attendance_input_dir(input_root, week_start)
    images = find_attendance_images(input_dir)
    generative_dir = attendance_output_dir(output_root, week_start)
    analysis_dir = generative_dir / "atendimentos"
    combined_path = generative_dir / COMBINED_NAME
    load_env_file()
    model = os.environ.get("OPENAI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    prompt = load_individual_prompt()
    expected = expected_manifest(images, model, prompt)
    if artifacts_are_current(analysis_dir, combined_path, expected):
        return AttendanceArtifacts(input_dir, analysis_dir, combined_path, images, True)
    if validate_only:
        raise ManualAttendanceError(
            "Os prints existem, mas as três análises estão ausentes ou não correspondem às imagens atuais."
        )

    targets = [analysis_dir / f"{index:02d}_analise.md" for index in range(1, 4)]
    targets.extend([analysis_dir / MANIFEST_NAME, combined_path])
    if not force and not confirm_reanalysis(targets, input_fn):
        raise ManualAttendanceError("Análises existentes preservadas pelo usuário.")

    analyzer = analyze_fn or analyze_image_with_openai
    analyses: list[str | None] = [None] * EXPECTED_IMAGE_COUNT
    with ThreadPoolExecutor(max_workers=EXPECTED_IMAGE_COUNT) as executor:
        futures = {
            executor.submit(analyzer, path, index, model, prompt): index
            for index, path in enumerate(images, 1)
        }
        for future in as_completed(futures):
            index = futures[future]
            result = future.result().strip()
            if not result:
                raise ManualAttendanceError(f"O agente do atendimento {index} devolveu texto vazio.")
            analyses[index - 1] = result
    final_analyses = [item for item in analyses if item is not None]
    if len(final_analyses) != EXPECTED_IMAGE_COUNT:
        raise ManualAttendanceError("Nem todas as três análises foram concluídas.")

    generative_dir.mkdir(parents=True, exist_ok=True)
    analysis_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="atendimentos_", dir=generative_dir) as temporary:
        temporary_dir = Path(temporary)
        temp_analysis_dir = temporary_dir / "atendimentos"
        temp_analysis_dir.mkdir()
        for index, text in enumerate(final_analyses, 1):
            (temp_analysis_dir / f"{index:02d}_analise.md").write_text(
                text.rstrip() + "\n", encoding="utf-8"
            )
        manifest = dict(expected)
        manifest["week_start"] = week_start.isoformat()
        manifest["generated_at"] = datetime.now(report_timezone()).isoformat(timespec="seconds")
        (temp_analysis_dir / MANIFEST_NAME).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        temp_combined = temporary_dir / COMBINED_NAME
        temp_combined.write_text(combined_markdown(images, final_analyses), encoding="utf-8")
        for index in range(1, 4):
            os.replace(temp_analysis_dir / f"{index:02d}_analise.md", analysis_dir / f"{index:02d}_analise.md")
        os.replace(temp_analysis_dir / MANIFEST_NAME, analysis_dir / MANIFEST_NAME)
        os.replace(temp_combined, combined_path)
    return AttendanceArtifacts(input_dir, analysis_dir, combined_path, images, False)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analisa exatamente três prints de atendimento com agentes independentes."
    )
    parser.add_argument("--week-start", required=True, type=parse_week_start, metavar="AAAA-MM-DD")
    parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--force", action="store_true", help="Sobrescreve análises existentes.")
    parser.add_argument("--validate-only", action="store_true", help="Só valida prints, hashes e saídas.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = process_attendances(
            args.week_start,
            input_root=args.input_root.resolve(),
            output_root=args.output_root.resolve(),
            force=args.force,
            validate_only=args.validate_only,
        )
    except (ManualAttendanceError, OSError, ValueError) as exc:
        print(f"Erro nos atendimentos manuais: {exc}", file=sys.stderr)
        return 2
    status = "já estavam atuais" if result.reused else "foram geradas"
    print(f"As três análises {status}: {result.analysis_dir}")
    print(f"Análise consolidada: {result.combined_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
