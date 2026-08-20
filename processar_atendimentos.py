from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
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
SUPPORTED_SUFFIXES = {".txt"}
EXPECTED_CONVERSATION_COUNT = 3
MANIFEST_NAME = "manifest.json"
COMBINED_NAME = "04_16_amostragem_qualitativa.md"
PROMPT_VERSION = "2026-08-18.2"
DEFAULT_MODEL = "gpt-5.6-terra"
PROMPT_PATH = ROOT / "prompts" / "generativos" / "04_16_analise_atendimento_individual.prompt.md"


class ManualAttendanceError(ValueError):
    pass


@dataclass(frozen=True)
class AttendanceArtifacts:
    input_dir: Path
    analysis_dir: Path
    combined_path: Path
    conversation_paths: tuple[Path, ...]
    reused: bool


INDIVIDUAL_PROMPT = """Você é um analista comercial especializado em oficinas mecânicas.
Analise somente a conversa fornecida. Ela representa um único atendimento e pode estar
incompleta. Não use nem suponha informações de outros casos.

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
- Separe fato registrado de hipótese. Se a conversa estiver incompleta, diga exatamente o limite.
- Não tente reconstruir nem reproduzir dados substituídos por marcadores como [TELEFONE REMOVIDO].
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
Uma frase sobre o que a conversa não permite concluir.
"""


def attendance_input_dir(input_root: Path, week_start: date) -> Path:
    return input_root / week_start.isoformat()


def attendance_output_dir(output_root: Path, week_start: date) -> Path:
    return output_root / f"{week_start.year:04d}" / week_start.isoformat() / "generativos"


def find_attendance_conversations(directory: Path) -> tuple[Path, ...]:
    if not directory.is_dir():
        raise ManualAttendanceError(f"Pasta dos atendimentos não encontrada: {directory}")
    conversations = tuple(
        sorted(
            (
                path
                for path in directory.iterdir()
                if path.is_file() and path.suffix.casefold() in SUPPORTED_SUFFIXES
            ),
            key=lambda path: path.name.casefold(),
        )
    )
    if len(conversations) != EXPECTED_CONVERSATION_COUNT:
        raise ManualAttendanceError(
            f"A pasta {directory} deve conter exatamente 3 conversas em TXT; foram encontradas {len(conversations)}."
        )
    for path in conversations:
        load_conversation(path)
    return conversations


def load_conversation(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ManualAttendanceError(f"A conversa deve estar salva em UTF-8: {path}") from exc
    if not text.strip():
        raise ManualAttendanceError(f"A conversa está vazia: {path}")
    if text.lstrip().casefold().startswith("cole a conversa completa aqui"):
        raise ManualAttendanceError(f"A conversa ainda contém o texto de instrução do modelo: {path}")
    if len(text) > 500_000:
        raise ManualAttendanceError(f"A conversa ultrapassa o limite de 500 mil caracteres: {path}")
    return text


SENSITIVE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("URL", re.compile(r"(?i)\b(?:https?://|www\.)\S+")),
    ("EMAIL", re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")),
    ("CNPJ", re.compile(r"(?<!\d)(?:\d{2}[.\s-]?\d{3}[.\s-]?\d{3}[\/\s-]?\d{4}[-.\s]?\d{2})(?!\d)")),
    ("CPF", re.compile(r"(?<!\d)(?:\d{3}[.\s-]?\d{3}[.\s-]?\d{3}[-.\s]?\d{2})(?!\d)")),
    ("CARTÃO", re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")),
    ("TELEFONE", re.compile(r"(?<!\d)(?:\+?55[\s.-]*)?(?:\(?\d{2}\)?[\s.-]*)?(?:9\d{4}|\d{4})[\s.-]?\d{4}(?!\d)")),
    ("PLACA", re.compile(r"(?i)(?<![A-Z0-9])[A-Z]{3}[-\s]?(?:\d{4}|\d[A-Z]\d{2})(?![A-Z0-9])")),
    ("CEP", re.compile(r"(?<!\d)\d{5}[-.\s]?\d{3}(?!\d)")),
)

SENSITIVE_FIELD = re.compile(
    r"(?im)^(\s*(?:nome(?:\s+completo)?|telefone|celular|whatsapp|e-?mail|cpf|cnpj|rg|documento|placa|renavam|chassi|cep|endereço|logradouro|chave\s+pix|pix|dados\s+bancários|conta\s+bancária|agência)\s*[:=-]\s*).+$"
)
SELF_IDENTIFICATION = re.compile(
    r"(?i)\b(meu\s+nome\s+[ée]|me\s+chamo)\s+[A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇ][\wÀ-ÿ'-]*(?:\s+[A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇ][\wÀ-ÿ'-]*){0,3}"
)
TIMESTAMP_SENDER = re.compile(
    r"(?m)^(\s*(?:\[[^\]\r\n]{4,40}\]|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}[^\r\n]{0,20}?[-–])\s*)([^:\r\n]{1,60})(:\s*)"
)
BARE_SENDER = re.compile(r"(?m)^\s*([^:\r\n]{1,50})(:\s*)")
FIELD_LABELS = {
    "assunto", "data", "endereco", "hora", "modelo", "nome", "observacao", "placa",
    "problema", "servico", "telefone", "valor", "veiculo", "versao",
}


def _speaker_label(raw: str, mapping: dict[str, str]) -> str:
    key = raw.strip().casefold()
    if "cliente" in key:
        return "CLIENTE"
    if any(word in key for word in ("atendente", "consultor", "oficina", "empresa")):
        return "OFICINA"
    if key not in mapping:
        mapping[key] = f"PARTICIPANTE {len(mapping) + 1}"
    return mapping[key]


def redact_sensitive_data(text: str) -> str:
    """Remove common personal identifiers locally, before any API request."""
    speaker_mapping: dict[str, str] = {}

    def replace_timestamp_sender(match: re.Match[str]) -> str:
        return f"{match.group(1)}{_speaker_label(match.group(2), speaker_mapping)}{match.group(3)}"

    sanitized = TIMESTAMP_SENDER.sub(replace_timestamp_sender, text)
    candidates: dict[str, int] = {}
    for match in BARE_SENDER.finditer(sanitized):
        raw = match.group(1).strip()
        key = raw.casefold()
        normalized = "".join(character for character in key if character.isalnum() or character.isspace())
        if normalized not in FIELD_LABELS and not any(character.isdigit() for character in raw):
            candidates[key] = candidates.get(key, 0) + 1

    def replace_bare_sender(match: re.Match[str]) -> str:
        raw = match.group(1).strip()
        key = raw.casefold()
        known_role = any(word in key for word in ("cliente", "atendente", "consultor", "oficina", "empresa"))
        if not known_role and candidates.get(key, 0) < 2:
            return match.group(0)
        return f"{_speaker_label(raw, speaker_mapping)}{match.group(2)}"

    sanitized = BARE_SENDER.sub(replace_bare_sender, sanitized)
    for raw_name in sorted(speaker_mapping, key=len, reverse=True):
        if len(raw_name) >= 3:
            sanitized = re.sub(re.escape(raw_name), "[NOME REMOVIDO]", sanitized, flags=re.IGNORECASE)
    sanitized = SENSITIVE_FIELD.sub(lambda match: f"{match.group(1)}[DADO REMOVIDO]", sanitized)
    sanitized = SELF_IDENTIFICATION.sub(lambda match: f"{match.group(1)} [NOME REMOVIDO]", sanitized)
    for label, pattern in SENSITIVE_PATTERNS:
        sanitized = pattern.sub(f"[{label} REMOVIDO]", sanitized)
    return sanitized


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def analyze_conversation_with_openai(conversation: str, slot: int, model: str, prompt: str) -> str:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ManualAttendanceError(
            "OPENAI_API_KEY não foi definida em env.txt. Ela é necessária para analisar as três conversas."
        )
    payload = {
        "model": model,
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_text", "text": "CONVERSA ANONIMIZADA:\n\n" + conversation},
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


def combined_markdown(conversations: Sequence[Path], analyses: Sequence[str]) -> str:
    sections = [
        "## Revisão da qualidade dos atendimentos",
        "",
        "> A revisão reúne três atendimentos da semana. A amostra ajuda a encontrar pontos práticos, mas não representa sozinha todo o trabalho da equipe.",
    ]
    for index, (_conversation_path, analysis) in enumerate(zip(conversations, analyses), 1):
        sections.extend(
            [
                "",
                f"### Atendimento {index}",
                "",
                analysis.strip(),
            ]
        )
    sections.append("")
    return "\n".join(sections)


def expected_manifest(conversations: Sequence[Path], model: str, prompt: str) -> dict[str, object]:
    return {
        "version": 1,
        "prompt_version": PROMPT_VERSION,
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "model": model,
        "conversations": [
            {"slot": index, "filename": path.name, "sha256": sha256_file(path)}
            for index, path in enumerate(conversations, 1)
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
    for key in ("version", "prompt_version", "prompt_sha256", "model", "conversations"):
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
    analyze_fn: Callable[[str, int, str, str], str] | None = None,
) -> AttendanceArtifacts:
    input_dir = attendance_input_dir(input_root, week_start)
    conversations = find_attendance_conversations(input_dir)
    generative_dir = attendance_output_dir(output_root, week_start)
    analysis_dir = generative_dir / "atendimentos"
    combined_path = generative_dir / COMBINED_NAME
    load_env_file()
    model = os.environ.get("OPENAI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    prompt = load_individual_prompt()
    expected = expected_manifest(conversations, model, prompt)
    if artifacts_are_current(analysis_dir, combined_path, expected):
        return AttendanceArtifacts(input_dir, analysis_dir, combined_path, conversations, True)
    if validate_only:
        raise ManualAttendanceError(
            "As conversas existem, mas as três análises estão ausentes ou não correspondem aos textos atuais."
        )

    targets = [analysis_dir / f"{index:02d}_analise.md" for index in range(1, 4)]
    targets.extend([analysis_dir / MANIFEST_NAME, combined_path])
    if not force and not confirm_reanalysis(targets, input_fn):
        raise ManualAttendanceError("Análises existentes preservadas pelo usuário.")

    sanitized_conversations = [redact_sensitive_data(load_conversation(path)) for path in conversations]
    analyzer = analyze_fn or analyze_conversation_with_openai
    analyses: list[str | None] = [None] * EXPECTED_CONVERSATION_COUNT
    with ThreadPoolExecutor(max_workers=EXPECTED_CONVERSATION_COUNT) as executor:
        futures = {
            executor.submit(analyzer, conversation, index, model, prompt): index
            for index, conversation in enumerate(sanitized_conversations, 1)
        }
        for future in as_completed(futures):
            index = futures[future]
            result = future.result().strip()
            if not result:
                raise ManualAttendanceError(f"O agente do atendimento {index} devolveu texto vazio.")
            analyses[index - 1] = result
    final_analyses = [item for item in analyses if item is not None]
    if len(final_analyses) != EXPECTED_CONVERSATION_COUNT:
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
        temp_combined.write_text(combined_markdown(conversations, final_analyses), encoding="utf-8")
        for index in range(1, 4):
            os.replace(temp_analysis_dir / f"{index:02d}_analise.md", analysis_dir / f"{index:02d}_analise.md")
        os.replace(temp_analysis_dir / MANIFEST_NAME, analysis_dir / MANIFEST_NAME)
        os.replace(temp_combined, combined_path)
    return AttendanceArtifacts(input_dir, analysis_dir, combined_path, conversations, False)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analisa exatamente três conversas completas com agentes independentes."
    )
    parser.add_argument("--week-start", required=True, type=parse_week_start, metavar="AAAA-MM-DD")
    parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--force", action="store_true", help="Sobrescreve análises existentes.")
    parser.add_argument("--validate-only", action="store_true", help="Só valida conversas, hashes e saídas.")
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
