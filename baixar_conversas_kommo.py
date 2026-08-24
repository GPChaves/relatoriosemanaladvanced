from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Iterable, Iterator, Mapping, Sequence

from relatorio import (
    ENV_FILE,
    PROJECT_ROOT,
    KommoApiError,
    KommoConfig,
    KommoReadOnlyClient,
    embedded_collection,
    fetch_users,
    load_env_file,
    report_timezone,
)


DEFAULT_LEAD_IDS = (65510668, 65437406, 65529742)
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "tmp" / "conversas_kommo"
PAGE_LIMIT = 100


def positive_lead_id(value: str) -> int:
    try:
        lead_id = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("o ID do lead deve ser um número inteiro") from exc
    if lead_id <= 0:
        raise argparse.ArgumentTypeError("o ID do lead deve ser positivo")
    return lead_id


def unique_ids(values: Iterable[int]) -> list[int]:
    return list(dict.fromkeys(values))


def iter_collection(
    client: KommoReadOnlyClient,
    path: str,
    collection_name: str,
    params: Mapping[str, object] | None = None,
) -> Iterator[dict[str, object]]:
    page = 1
    while True:
        page_params = dict(params or {})
        page_params.update({"limit": PAGE_LIMIT, "page": page})
        payload = client.get_json(path, page_params)
        items = embedded_collection(payload, collection_name)
        yield from items
        if len(items) < PAGE_LIMIT:
            return
        page += 1


def fetch_lead_talks(
    client: KommoReadOnlyClient, lead_id: int
) -> list[dict[str, object]]:
    talks = list(
        iter_collection(
            client,
            "/api/v4/talks",
            "talks",
            {
                "filter[entity_id]": lead_id,
                "filter[entity_type]": "lead",
            },
        )
    )
    talks = [talk for talk in talks if talk.get("entity_id") == lead_id]
    talks.sort(
        key=lambda talk: (
            talk.get("created_at") if isinstance(talk.get("created_at"), int) else 0,
            talk.get("talk_id") if isinstance(talk.get("talk_id"), int) else 0,
        )
    )
    return talks


def fetch_talk_messages(
    client: KommoReadOnlyClient, talk_id: int
) -> list[dict[str, object]]:
    messages = list(
        iter_collection(
            client,
            f"/api/v4/talks/{talk_id}/messages",
            "messages",
        )
    )
    messages.sort(
        key=lambda message: (
            message.get("created_at")
            if isinstance(message.get("created_at"), int)
            else 0,
            str(message.get("id", "")),
        )
    )
    return messages


def extract_text(message: Mapping[str, object]) -> str | None:
    payload = message.get("message")
    if isinstance(payload, str):
        return payload
    if not isinstance(payload, Mapping):
        return None

    parts: list[str] = []
    for key in ("text", "caption"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            parts.append(value)

    content = payload.get("content")
    if isinstance(content, str) and content and content not in parts:
        parts.append(content)
    elif isinstance(content, Mapping):
        for key in ("text", "caption"):
            value = content.get(key)
            if isinstance(value, str) and value and value not in parts:
                parts.append(value)

    return "\n".join(parts) if parts else None


def message_kind(message: Mapping[str, object]) -> str:
    payload = message.get("message")
    if isinstance(payload, Mapping):
        value = payload.get("type")
        if isinstance(value, str) and value:
            return value
    value = message.get("type")
    return value if isinstance(value, str) and value else "desconhecida"


def author_label(
    message: Mapping[str, object], users: Mapping[int, Mapping[str, object]]
) -> str:
    author = message.get("author")
    author_type = ""
    user_id: int | None = None
    if isinstance(author, Mapping):
        value = author.get("type")
        author_type = value if isinstance(value, str) else ""
        for key in ("user_id", "id"):
            value = author.get(key)
            if isinstance(value, int):
                user_id = value
                break

    if author_type == "internal":
        user = users.get(user_id) if user_id is not None else None
        name = user.get("name") if isinstance(user, Mapping) else None
        return str(name).strip() if isinstance(name, str) and name.strip() else "Consultor"
    if author_type in {"contact", "external"}:
        return "Cliente"
    if author_type in {"bot", "system"}:
        return "Automação"

    direction = message.get("type")
    if direction == "incoming":
        return "Cliente"
    if direction == "outgoing":
        return "Consultor"
    return "Sistema"


def timestamp_label(message: Mapping[str, object]) -> str:
    created_at = message.get("created_at")
    if not isinstance(created_at, int):
        return "data desconhecida"
    return datetime.fromtimestamp(created_at, report_timezone()).strftime(
        "%d/%m/%Y %H:%M:%S"
    )


def render_transcript(
    lead_id: int,
    talks_with_messages: Sequence[tuple[Mapping[str, object], Sequence[Mapping[str, object]]]],
    users: Mapping[int, Mapping[str, object]],
) -> str:
    lines = [f"Lead ID: {lead_id}", ""]
    for talk_index, (talk, messages) in enumerate(talks_with_messages, 1):
        talk_id = talk.get("talk_id", "não identificado")
        lines.extend([f"=== Conversa {talk_index} | Talk ID: {talk_id} ===", ""])
        for message in messages:
            text = extract_text(message)
            if text is None:
                text = f"[mensagem do tipo {message_kind(message)} sem texto]"
            lines.append(
                f"[{timestamp_label(message)}] {author_label(message, users)}: {text}"
            )
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        newline="\n",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as temporary:
        temporary.write(content)
        temporary_path = Path(temporary.name)
    os.replace(temporary_path, path)


def export_lead(
    client: KommoReadOnlyClient,
    lead_id: int,
    users: Mapping[int, Mapping[str, object]],
    output_dir: Path,
    *,
    raw_json: bool,
) -> tuple[Path, int, int]:
    talks = fetch_lead_talks(client, lead_id)
    if not talks:
        raise KommoApiError(f"Nenhuma conversa foi encontrada para o lead {lead_id}.")

    talks_with_messages: list[
        tuple[Mapping[str, object], Sequence[Mapping[str, object]]]
    ] = []
    total_messages = 0
    for talk in talks:
        talk_id = talk.get("talk_id")
        if not isinstance(talk_id, int):
            raise KommoApiError(
                f"A Kommo retornou uma conversa sem talk_id para o lead {lead_id}."
            )
        messages = fetch_talk_messages(client, talk_id)
        total_messages += len(messages)
        talks_with_messages.append((talk, messages))

    if total_messages == 0:
        raise KommoApiError(f"A conversa do lead {lead_id} não possui mensagens.")

    transcript_path = output_dir / f"lead_{lead_id}.txt"
    write_text_atomic(
        transcript_path,
        render_transcript(lead_id, talks_with_messages, users),
    )

    if raw_json:
        raw_path = output_dir / f"lead_{lead_id}.json"
        raw_payload = {
            "lead_id": lead_id,
            "talks": [
                {"talk": dict(talk), "messages": [dict(item) for item in messages]}
                for talk, messages in talks_with_messages
            ],
        }
        write_text_atomic(
            raw_path,
            json.dumps(raw_payload, ensure_ascii=False, indent=2) + "\n",
        )

    return transcript_path, len(talks), total_messages


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Baixa o texto integral das conversas de leads da Kommo. "
            "O script é independente e não faz parte do pipeline do relatório."
        )
    )
    parser.add_argument(
        "--lead-id",
        action="append",
        type=positive_lead_id,
        dest="lead_ids",
        help=(
            "ID de um lead. Repita a opção para vários leads. "
            "Sem esta opção, usa os três leads selecionados."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Pasta de saída (padrão: {DEFAULT_OUTPUT_DIR}).",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=ENV_FILE,
        help=f"Arquivo com KOMMO_BASE_URL e KOMMO_TOKEN (padrão: {ENV_FILE}).",
    )
    parser.add_argument(
        "--raw-json",
        action="store_true",
        help="Também salva a resposta integral da API em JSON para auditoria.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    lead_ids = unique_ids(args.lead_ids or DEFAULT_LEAD_IDS)

    try:
        load_env_file(args.env_file)
        client = KommoReadOnlyClient(KommoConfig.from_environment())
        account = client.get_json("/api/v4/account")
        if account is None or not isinstance(account.get("id"), int):
            raise KommoApiError("Não foi possível validar a conta Kommo.")
        users = fetch_users(client)

        for lead_id in lead_ids:
            path, talk_count, message_count = export_lead(
                client,
                lead_id,
                users,
                args.output_dir.resolve(),
                raw_json=args.raw_json,
            )
            print(
                f"Lead {lead_id}: {talk_count} conversa(s), "
                f"{message_count} mensagem(ns) -> {path.resolve()}"
            )
        return 0
    except KommoApiError as exc:
        if exc.status_code == 403:
            print(
                "Erro: a integração Kommo não possui o escopo "
                "'External chat history', necessário para ler as mensagens.",
                file=sys.stderr,
            )
        else:
            print(f"Erro ao consultar a Kommo: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
