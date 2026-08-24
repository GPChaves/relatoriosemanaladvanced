from __future__ import annotations

import unittest

import baixar_conversas_kommo as downloader


class FakeClient:
    def __init__(self, pages: dict[tuple[str, int], dict[str, object]]) -> None:
        self.pages = pages
        self.calls: list[tuple[str, dict[str, object]]] = []

    def get_json(
        self, path: str, params: dict[str, object] | None = None
    ) -> dict[str, object] | None:
        effective = dict(params or {})
        self.calls.append((path, effective))
        page = int(effective.get("page", 1))
        return self.pages.get((path, page), {"_embedded": {}})


class ConversationDownloaderTests(unittest.TestCase):
    def test_fetch_lead_talks_uses_required_entity_filters(self) -> None:
        client = FakeClient(
            {
                ("/api/v4/talks", 1): {
                    "_embedded": {
                        "talks": [
                            {
                                "talk_id": 20,
                                "entity_id": 65510668,
                                "created_at": 20,
                            },
                            {
                                "talk_id": 10,
                                "entity_id": 65510668,
                                "created_at": 10,
                            },
                            {
                                "talk_id": 99,
                                "entity_id": 1,
                                "created_at": 1,
                            },
                        ]
                    }
                }
            }
        )

        talks = downloader.fetch_lead_talks(client, 65510668)  # type: ignore[arg-type]

        self.assertEqual([talk["talk_id"] for talk in talks], [10, 20])
        _, params = client.calls[0]
        self.assertEqual(params["filter[entity_id]"], 65510668)
        self.assertEqual(params["filter[entity_type]"], "lead")

    def test_render_transcript_preserves_complete_multiline_text(self) -> None:
        talks = [
            (
                {"talk_id": 3193},
                [
                    {
                        "id": "1",
                        "created_at": 1786462354,
                        "type": "incoming",
                        "author": {"type": "contact"},
                        "message": {
                            "type": "text",
                            "text": "Primeira linha\nSegunda linha",
                        },
                    },
                    {
                        "id": "2",
                        "created_at": 1786462414,
                        "type": "outgoing",
                        "author": {"type": "internal", "user_id": 7},
                        "message": {"type": "text", "text": "Resposta integral"},
                    },
                ],
            )
        ]

        rendered = downloader.render_transcript(
            65510668,
            talks,
            {7: {"name": "Consultor Teste"}},
        )

        self.assertIn("Cliente: Primeira linha\nSegunda linha", rendered)
        self.assertIn("Consultor Teste: Resposta integral", rendered)
        self.assertIn("Talk ID: 3193", rendered)

    def test_extract_text_keeps_text_and_caption(self) -> None:
        text = downloader.extract_text(
            {
                "message": {
                    "type": "picture",
                    "text": "Descrição",
                    "caption": "Legenda",
                }
            }
        )

        self.assertEqual(text, "Descrição\nLegenda")

    def test_message_without_text_gets_explicit_placeholder(self) -> None:
        rendered = downloader.render_transcript(
            1,
            [
                (
                    {"talk_id": 2},
                    [
                        {
                            "type": "incoming",
                            "author": {"type": "contact"},
                            "message": {"type": "picture"},
                        }
                    ],
                )
            ],
            {},
        )

        self.assertIn("[mensagem do tipo picture sem texto]", rendered)


if __name__ == "__main__":
    unittest.main()
