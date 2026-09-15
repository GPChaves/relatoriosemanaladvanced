from __future__ import annotations

import re
import unicodedata


PRODUCTION_PROVENANCE_MARKERS = (
    "informado manualmente",
    "manualmente",
    "fonte manual",
    "entrada manual",
    "material recebido",
    "material fornecido",
    "material disponibilizado",
    "dados recebidos",
    "dados fornecidos",
    "dados disponibilizados",
    "informacoes recebidas",
    "informacoes fornecidas",
    "informacoes disponibilizadas",
    "conteudo recebido",
    "conteudo fornecido",
    "conteudo disponibilizado",
    "automacao",
    "automatizado",
    "inteligencia artificial",
    "ia generativa",
    "subagente",
    "agente de ia",
    "gerado por ia",
    "prompt",
    "via api",
    "api da kommo",
    "xlsx",
    "arquivo interno",
    ".csv",
    ".md",
    "script python",
)

VAGUE_LIMITATION_MARKERS = (
    "dados insuficientes",
    "informacoes insuficientes",
    "nao foi possivel verificar",
    "nao foi possivel analisar",
    "nao foi possivel aferir",
)

AUTHOR_LIMITATION_MARKERS = (
    "nao tive como aferir",
    "nao tive como verificar",
    "nao tive como analisar",
    "nao consegui aferir",
    "nao consegui verificar",
    "nao consegui analisar",
)

IMPERSONAL_STYLE_MARKERS = (
    "identificou-se",
    "observou-se",
    "constatou-se",
    "verificou-se",
)

INACCESSIBLE_CONTENT_MARKERS = (
    "audio inacessivel",
    "audio indisponivel",
    "audio nao analisado",
    "audio nao pode ser analisado",
    "audio nao pude analisar",
    "audio sem transcricao",
    "anexo inacessivel",
    "anexo indisponivel",
    "anexo nao analisado",
    "imagem inacessivel",
    "imagem indisponivel",
    "imagem nao analisada",
    "documento inacessivel",
    "documento indisponivel",
    "documento nao analisado",
    "conteudo inacessivel",
    "conteudo indisponivel",
    "conteudo nao analisado",
)

CONTENT_MODALITY_MARKERS = ("audio", "anexo", "imagem", "documento", "conteudo")
ACCESS_LIMIT_MARKERS = (
    "inacessivel",
    "indisponivel",
    "nao analisado",
    "nao analisada",
    "nao pude analisar",
    "nao consegui analisar",
    "nao consegui ouvir",
    "nao tive acesso",
    "nao tenho acesso",
    "sem transcricao",
)

UNSUPPORTED_FAILURE_MARKERS = (
    "duvida ficou sem resposta",
    "duvida nao foi respondida",
    "pergunta ficou sem resposta",
    "pergunta nao foi respondida",
    "faltou responder",
    "faltou esclarecer",
    "faltou tirar a duvida",
    "questao ficou sem resposta",
    "questao nao foi respondida",
    "deixou a duvida sem resposta",
    "deixou a pergunta sem resposta",
    "deixou a questao sem resposta",
    "cliente ficou sem resposta",
    "resposta nao foi dada",
    "ausencia de resposta",
    "sem esclarecimento",
    "nao respondeu o cliente",
    "nao esclareceu",
    "nao tirou a duvida",
    "descontar pontos",
    "desconto de pontos",
    "reduzir a nota",
    "nota menor",
    "penalizar o atendimento",
    "deveria ter respondido",
    "precisa responder",
    "deve responder",
    "ponto negativo",
    "classificacao negativa",
)

PERSISTENT_DOUBT_MARKERS = (
    "cliente: continuo sem entender",
    "cliente: ainda nao entendi",
    "cliente diz que continua sem entender",
    "cliente continuou sem entender",
    "cliente disse que continuava sem entender",
    "cliente voltou a dizer que nao entendeu",
    "cliente repetiu a pergunta",
    "cliente refez a pergunta",
    "duvida persistiu",
    "pergunta foi repetida depois",
)

PLACEHOLDER_CONTENT_PATTERN = re.compile(
    r"\?.{0,500}(?:\[|<|\()?\s*(?:audio|anexo|imagem|documento)"
    r"(?:[^\n]{0,80})(?:nao transcrit|inacess|indispon|omitid|removid|sem conteudo)",
    re.DOTALL,
)


def normalize_for_policy(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    without_accents = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    return re.sub(r"\s+", " ", without_accents).strip()


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def _has_concrete_reason(text: str) -> bool:
    return bool(
        re.search(
            r"\b(?:porque|pois|ja que|sem (?:os |as |um |uma )?|quando )\b",
            text,
        )
    )


def narrative_policy_violations(
    text: str, *, source_text: str | None = None
) -> tuple[str, ...]:
    """Retorna violações objetivas; decisões semânticas continuam nos prompts."""

    normalized = normalize_for_policy(text)
    violations: list[str] = []

    exposed = [
        marker for marker in PRODUCTION_PROVENANCE_MARKERS if marker in normalized
    ]
    if exposed:
        violations.append(
            "expõe bastidores ou trata a base como material recebido: "
            + ", ".join(exposed)
        )

    vague = [marker for marker in VAGUE_LIMITATION_MARKERS if marker in normalized]
    if vague:
        violations.append(
            "descreve uma limitação de forma vaga ou impessoal; escreva na voz de quem "
            "assina, informando o que não pôde ser aferido e o motivo concreto"
        )
    elif _contains_any(normalized, AUTHOR_LIMITATION_MARKERS) and not _has_concrete_reason(
        normalized
    ):
        violations.append(
            "descreve uma limitação sem o motivo concreto que afeta a análise"
        )

    impersonal = [marker for marker in IMPERSONAL_STYLE_MARKERS if marker in normalized]
    if impersonal:
        violations.append(
            "usa construção burocrática incompatível com o tom natural 3/10: "
            + ", ".join(impersonal)
        )

    normalized_source = normalize_for_policy(source_text or "")
    inaccessible_after_question = bool(
        source_text and PLACEHOLDER_CONTENT_PATTERN.search(normalized_source)
    )
    analysis_declares_inaccessible = _contains_any(
        normalized, INACCESSIBLE_CONTENT_MARKERS
    ) or (
        _contains_any(normalized, CONTENT_MODALITY_MARKERS)
        and _contains_any(normalized, ACCESS_LIMIT_MARKERS)
    )
    claims_failure = _contains_any(normalized, UNSUPPORTED_FAILURE_MARKERS)
    persistent_doubt = _contains_any(
        normalized_source if source_text is not None else normalized,
        PERSISTENT_DOUBT_MARKERS,
    )
    if (
        (inaccessible_after_question or analysis_declares_inaccessible)
        and claims_failure
        and not persistent_doubt
    ):
        violations.append(
            "transforma conteúdo inacessível em falha de atendimento; ausência de "
            "evidência não permite crítica, penalização nem recomendação corretiva"
        )

    return tuple(violations)
