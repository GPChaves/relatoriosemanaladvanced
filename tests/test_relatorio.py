import csv
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import relatorio


RESPONSIBLE_FIELD_ID = 900


def lead_with_custom_responsible(
    lead_id: int,
    responsible_name: str | None,
    **values: object,
) -> dict[str, object]:
    lead: dict[str, object] = {
        "id": lead_id,
        "responsible_user_id": 999,
        **values,
    }
    if responsible_name is not None:
        lead["custom_fields_values"] = [
            {
                "field_id": RESPONSIBLE_FIELD_ID,
                "values": [{"value": responsible_name}],
            }
        ]
    return lead


def terminal_event(
    event_id: int,
    lead_id: int,
    timestamp: int,
    status_id: int,
    *,
    created_by: int = 777,
) -> dict[str, object]:
    return {
        "id": event_id,
        "entity_id": lead_id,
        "created_at": timestamp,
        "created_by": created_by,
        "type": "lead_status_changed",
        "value_after": [
            {
                "lead_status": {
                    "id": status_id,
                    "pipeline_id": 123,
                }
            }
        ],
    }


class PeriodIdentificationTests(unittest.TestCase):
    def test_complete_week_without_month_close(self) -> None:
        record = relatorio.build_identification(
            date(2026, 8, 17),
            datetime(2026, 8, 24, 9, 30, tzinfo=timezone(timedelta(hours=-3))),
        )
        self.assertEqual(record.data_final, "2026-08-23")
        self.assertEqual(record.situacao_semana, "completa")
        self.assertEqual(record.fecha_mes, "não")
        self.assertEqual(record.mes_fechado, "")

    def test_partial_week(self) -> None:
        self.assertEqual(
            relatorio.week_status(date(2026, 8, 17), date(2026, 8, 20)),
            "parcial",
        )

    def test_future_week(self) -> None:
        self.assertEqual(
            relatorio.week_status(date(2026, 8, 24), date(2026, 8, 20)),
            "futura",
        )

    def test_week_that_closes_month(self) -> None:
        self.assertEqual(relatorio.closing_month(date(2026, 8, 31)), "2026-08")

    def test_month_is_not_applicable_during_last_day(self) -> None:
        self.assertEqual(
            relatorio.applicable_month(date(2026, 8, 31), date(2026, 8, 31)),
            "",
        )

    def test_month_is_applicable_after_it_has_ended(self) -> None:
        self.assertEqual(
            relatorio.applicable_month(date(2026, 8, 31), date(2026, 9, 1)),
            "2026-08",
        )

    def test_month_applicability_handles_year_boundary(self) -> None:
        self.assertEqual(
            relatorio.applicable_month(date(2026, 12, 28), date(2027, 1, 1)),
            "2026-12",
        )

    def test_month_boundaries_in_december(self) -> None:
        self.assertEqual(
            relatorio.month_boundaries("2026-12"),
            (date(2026, 12, 1), date(2027, 1, 1)),
        )

    def test_existing_file_requires_explicit_yes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "existing.csv"
            path.write_text("original", encoding="utf-8")
            self.assertFalse(relatorio.confirm_overwrite(path, lambda _: "não"))
            self.assertTrue(relatorio.confirm_overwrite(path, lambda _: "sim"))

    def test_force_bypasses_interactive_confirmation(self) -> None:
        with mock.patch.object(relatorio, "confirm_overwrite") as confirmation:
            self.assertTrue(relatorio.should_overwrite(Path("existing.csv"), force=True))
        confirmation.assert_not_called()

    def test_week_start_must_be_monday(self) -> None:
        with self.assertRaisesRegex(ValueError, "segunda-feira"):
            relatorio.validate_week_start(date(2026, 8, 18))

    def test_csv_is_written_with_expected_columns(self) -> None:
        record = relatorio.build_identification(
            date(2026, 8, 17),
            datetime(2026, 8, 24, 9, 30, tzinfo=timezone(timedelta(hours=-3))),
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.csv"
            relatorio.write_csv_atomic(path, record)
            with path.open(encoding="utf-8-sig", newline="") as file:
                rows = list(csv.DictReader(file))

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["data_inicial"], "2026-08-17")
        self.assertEqual(rows[0]["data_final"], "2026-08-23")


class CommandLineTests(unittest.TestCase):
    def test_parser_exposes_non_interactive_modes(self) -> None:
        force = relatorio.build_parser().parse_args(
            ["--week-start", "2026-08-17", "--force"]
        )
        validate = relatorio.build_parser().parse_args(
            ["--week-start", "2026-08-17", "--validate-only"]
        )

        self.assertTrue(force.force)
        self.assertFalse(force.validate_only)
        self.assertTrue(validate.validate_only)
        self.assertFalse(validate.force)

    def test_parser_accepts_explicit_native_responsible_source(self) -> None:
        args = relatorio.build_parser().parse_args(
            [
                "--week-start",
                "2026-08-17",
                "--responsible-source",
                "responsible-user-id",
                "--force",
            ]
        )

        self.assertEqual(args.responsible_source, "responsible-user-id")

    def test_validate_only_does_not_query_or_write(self) -> None:
        config = relatorio.KommoConfig(
            base_url="https://example.kommo.com", token="token"
        )
        with (
            mock.patch.object(relatorio, "load_env_file"),
            mock.patch.object(
                relatorio.KommoConfig, "from_environment", return_value=config
            ),
            mock.patch.object(relatorio, "load_monthly_snapshot") as monthly,
            mock.patch.object(relatorio, "load_weekly_snapshot") as weekly,
            mock.patch.object(relatorio, "write_csv_atomic") as write_one,
            mock.patch.object(relatorio, "write_csv_rows_atomic") as write_rows,
        ):
            exit_code = relatorio.main(
                ["--week-start", "2026-08-17", "--validate-only"]
            )

        self.assertEqual(exit_code, 0)
        monthly.assert_not_called()
        weekly.assert_not_called()
        write_one.assert_not_called()
        write_rows.assert_not_called()

    def test_invalid_week_returns_usage_exit_code_before_writing(self) -> None:
        config = relatorio.KommoConfig(
            base_url="https://example.kommo.com", token="token"
        )
        with (
            mock.patch.object(relatorio, "load_env_file"),
            mock.patch.object(
                relatorio.KommoConfig, "from_environment", return_value=config
            ),
            mock.patch.object(relatorio, "write_csv_atomic") as writer,
        ):
            exit_code = relatorio.main(
                ["--week-start", "2026-08-18", "--validate-only"]
            )

        self.assertEqual(exit_code, 2)
        writer.assert_not_called()

    def test_validate_only_rejects_invalid_manual_response_before_api(self) -> None:
        config = relatorio.KommoConfig(
            base_url="https://example.kommo.com", token="token"
        )
        with tempfile.TemporaryDirectory() as directory:
            manual = Path(directory) / "tempo_resposta.csv"
            manual.write_text(
                "responsavel_nome;conversas_anterior;tempo_medio_minutos_anterior;"
                "conversas_atual;tempo_medio_minutos_atual\nAna;1;-2;1;3\n",
                encoding="utf-8",
            )
            with (
                mock.patch.object(relatorio, "load_env_file"),
                mock.patch.object(
                    relatorio.KommoConfig, "from_environment", return_value=config
                ),
                mock.patch.object(
                    relatorio, "manual_response_time_path", return_value=manual
                ),
                mock.patch.object(relatorio, "load_weekly_snapshot") as weekly,
                mock.patch.object(relatorio, "write_csv_atomic") as writer,
            ):
                exit_code = relatorio.main(
                    ["--week-start", "2026-08-17", "--validate-only"]
                )

        self.assertEqual(exit_code, 2)
        weekly.assert_not_called()
        writer.assert_not_called()


class MonthlyDistributionTests(unittest.TestCase):
    def test_responsible_custom_field_must_be_unique(self) -> None:
        with mock.patch.object(
            relatorio,
            "iter_kommo_collection",
            return_value=iter(
                [
                    {"id": 1, "name": "Usuário responsável"},
                    {"id": 2, "name": "usuário RESPONSÁVEL"},
                ]
            ),
        ):
            with self.assertRaisesRegex(relatorio.KommoApiError, "exatamente um"):
                relatorio.fetch_responsible_custom_field(mock.Mock())

    def test_multiple_custom_responsible_values_are_rejected(self) -> None:
        lead = {
            "id": 123,
            "custom_fields_values": [
                {
                    "field_id": RESPONSIBLE_FIELD_ID,
                    "values": [{"value": "Ana"}, {"value": "Carlos"}],
                }
            ],
        }
        with self.assertRaisesRegex(relatorio.KommoApiError, "mais de um valor"):
            relatorio.lead_custom_responsible_name(
                lead, RESPONSIBLE_FIELD_ID
            )

    def test_native_responsible_source_uses_responsible_user_id(self) -> None:
        lead = {"id": 123, "responsible_user_id": 7}
        users = {7: {"name": "Milena - Advanced Mecânica Especializada"}}

        self.assertEqual(
            relatorio.lead_responsible_name(
                lead,
                users,
                responsible_field_id=None,
                responsible_source=relatorio.RESPONSIBLE_SOURCE_NATIVE,
            ),
            "Milena",
        )

    def test_distribution_uses_only_custom_responsible_field(self) -> None:
        leads = {
            1: lead_with_custom_responsible(1, "Ana"),
            2: lead_with_custom_responsible(2, "Ana"),
            3: lead_with_custom_responsible(3, "Carlos"),
        }
        pipeline = {"id": 123, "name": "Comercial"}
        extracted_at = datetime(
            2026, 9, 1, 9, 0, tzinfo=timezone(timedelta(hours=-3))
        )
        snapshot = relatorio.MonthlySnapshot(
            pipeline=pipeline,
            users={999: {"name": "Usuário padrão ignorado"}},
            loss_reasons=[],
            leads=list(leads.values()),
            outcome_events=[
                terminal_event(1, 1, 1, 142),
                terminal_event(2, 2, 2, 143),
                terminal_event(3, 3, 3, 142),
            ],
            lead_details=leads,
            responsible_field_id=RESPONSIBLE_FIELD_ID,
        )

        rows = relatorio.build_monthly_distribution_rows(
            snapshot, "2026-08", extracted_at
        )

        self.assertEqual(rows[0]["responsavel_nome"], "Ana")
        self.assertEqual(rows[0]["quantidade_leads"], 2)
        self.assertEqual(rows[0]["participacao_percentual"], 66.7)
        self.assertEqual(rows[1]["usuario_ativo"], "não aplicável")
        self.assertEqual(rows[1]["total_leads_mes"], 3)

    def test_responsible_name_omits_advanced_suffix(self) -> None:
        self.assertEqual(
            relatorio.compact_responsible_name(
                "Milena - Advanced Mecânica Especializada"
            ),
            "Milena",
        )
        self.assertEqual(relatorio.compact_responsible_name("Advanced Mecânica"), "Advanced Mecânica")
        self.assertEqual(
            relatorio.compact_responsible_name(
                "Vitor - Advanced Mecanica Especializada..."
            ),
            "Vitor",
        )
        self.assertEqual(
            relatorio.normalize_report_responsible_name("Advanced Mecanica"),
            relatorio.UNASSIGNED_RESPONSIBLE,
        )

    def test_missing_custom_responsible_is_explicit(self) -> None:
        lead = lead_with_custom_responsible(1, None)
        snapshot = relatorio.MonthlySnapshot(
            pipeline={"id": 123, "name": "Comercial"},
            users={},
            loss_reasons=[],
            leads=[lead],
            outcome_events=[terminal_event(1, 1, 1, 142)],
            lead_details={1: lead},
            responsible_field_id=RESPONSIBLE_FIELD_ID,
        )
        rows = relatorio.build_monthly_distribution_rows(
            snapshot,
            "2026-08",
            datetime(2026, 9, 1, tzinfo=timezone.utc),
        )
        self.assertEqual(rows[0]["responsavel_id"], "")
        self.assertEqual(
            rows[0]["responsavel_nome"], relatorio.UNASSIGNED_RESPONSIBLE
        )

    def test_main_active_pipeline_is_selected(self) -> None:
        class FakeClient:
            def get_json(self, path, params=None):
                self.path = path
                return {
                    "_embedded": {
                        "pipelines": [
                            {"id": 1, "is_main": False, "is_archive": False},
                            {"id": 2, "is_main": True, "is_archive": False},
                            {"id": 3, "is_main": True, "is_archive": True},
                        ]
                    }
                }

        client = FakeClient()
        selected = relatorio.select_main_pipeline(client)
        self.assertEqual(selected["id"], 2)
        self.assertEqual(client.path, "/api/v4/leads/pipelines")


class GlobalStagesTests(unittest.TestCase):
    def test_categories_follow_current_kommo_metadata(self) -> None:
        snapshot = relatorio.MonthlySnapshot(
            pipeline={
                "id": 123,
                "name": "Comercial",
                "_embedded": {
                    "statuses": [
                        {"id": 10, "name": "Etapa renomeada", "sort": 10},
                        {"id": 11, "name": "Etapa recém-criada", "sort": 20},
                        {"id": 142, "name": "Serviço iniciado", "sort": 900},
                        {"id": 143, "name": "Perdido", "sort": 1000},
                    ]
                },
            },
            users={1: {"name": "Ana"}},
            loss_reasons=[{"id": 50, "name": "Motivo renomeado", "sort": 10}],
            leads=[],
            outcome_events=[
                terminal_event(1, 1, 1, 142),
                terminal_event(2, 2, 2, 143),
            ],
            lead_details={
                1: lead_with_custom_responsible(1, "Ana", status_id=10),
                2: lead_with_custom_responsible(
                    2, "Ana", status_id=143, loss_reason_id=50
                ),
            },
            responsible_field_id=RESPONSIBLE_FIELD_ID,
        )

        rows = relatorio.build_global_stage_rows(
            snapshot,
            "2026-08",
            datetime(2026, 9, 1, tzinfo=timezone.utc),
        )
        categories = {row["categoria_relatorio"] for row in rows}

        self.assertNotIn("Etapa renomeada", categories)
        self.assertNotIn("Etapa recém-criada", categories)
        self.assertIn("Serviço iniciado", categories)
        self.assertIn("Perdido — Motivo renomeado", categories)
        self.assertEqual(sum(row["quantidade_leads"] for row in rows), 2)

    def test_unknown_loss_reason_is_not_discarded(self) -> None:
        snapshot = relatorio.MonthlySnapshot(
            pipeline={
                "id": 123,
                "name": "Comercial",
                "_embedded": {
                    "statuses": [{"id": 143, "name": "Perdido", "sort": 10}]
                },
            },
            users={1: {"name": "Ana"}},
            loss_reasons=[],
            leads=[],
            outcome_events=[terminal_event(1, 1, 1, 143)],
            lead_details={
                1: lead_with_custom_responsible(
                    1,
                    "Ana",
                    status_id=143,
                    loss_reason_id=999,
                    _embedded={"loss_reason": {"id": 999, "name": "Novo motivo"}},
                )
            },
            responsible_field_id=RESPONSIBLE_FIELD_ID,
        )

        rows = relatorio.build_global_stage_rows(
            snapshot,
            "2026-08",
            datetime(2026, 9, 1, tzinfo=timezone.utc),
        )
        populated = [row for row in rows if row["quantidade_leads"] == 1]
        self.assertEqual(populated[0]["categoria_relatorio"], "Perdido — Novo motivo")
        self.assertEqual(populated[0]["loss_reason_id"], 999)


class LeadPeriodFetchTests(unittest.TestCase):
    def test_fetch_period_leads_filters_created_at_for_new_leads(self) -> None:
        local_tz = timezone(timedelta(hours=-3))
        start = datetime(2026, 8, 17, tzinfo=local_tz)
        inside = int(datetime(2026, 8, 18, 12, tzinfo=local_tz).timestamp())
        outside = int(datetime(2026, 8, 24, 12, tzinfo=local_tz).timestamp())
        captured: dict[str, object] = {}

        def fake_iter(client, path, key, params):
            captured.update(params)
            return iter(
                [
                    {"id": 1, "pipeline_id": 123, "created_at": inside},
                    {"id": 2, "pipeline_id": 123, "created_at": outside},
                ]
            )

        with mock.patch.object(relatorio, "iter_kommo_collection", side_effect=fake_iter):
            leads = list(
                relatorio.fetch_period_leads(
                    mock.Mock(),
                    123,
                    date(2026, 8, 17),
                    date(2026, 8, 24),
                    local_tz,
                    date_field="created_at",
                )
            )

        self.assertEqual([lead["id"] for lead in leads], [1])
        self.assertEqual(captured["filter[created_at][from]"], int(start.timestamp()))
        self.assertNotIn("filter[updated_at][from]", captured)

    def test_terminal_event_query_filters_destination_stage(self) -> None:
        captured: list[dict[str, object]] = []

        def fake_events(client, start, end, tz, **kwargs):
            captured.append(kwargs)
            status_id = int(kwargs["target_status_id"])
            return [terminal_event(status_id, status_id, 1, status_id)]

        with mock.patch.object(relatorio, "fetch_period_events", side_effect=fake_events):
            events = relatorio.fetch_terminal_events(
                mock.Mock(),
                123,
                date(2026, 8, 17),
                date(2026, 8, 24),
                timezone.utc,
            )

        self.assertEqual({item["target_status_id"] for item in captured}, {142, 143})
        self.assertTrue(all(item["event_type"] == "lead_status_changed" for item in captured))
        self.assertEqual(len(events), 2)


class WeeklyConversionTests(unittest.TestCase):
    def test_conversion_and_percentage_point_variation(self) -> None:
        local_tz = timezone(timedelta(hours=-3))

        def timestamp(year, month, day):
            return int(datetime(year, month, day, 12, tzinfo=local_tz).timestamp())

        snapshot = relatorio.WeeklySnapshot(
            pipeline={"id": 123, "name": "Comercial"},
            users={999: {"name": "Usuário padrão ignorado"}},
            leads=[],
            outcome_events=[
                terminal_event(1, 1, timestamp(2026, 8, 10), 142),
                terminal_event(2, 2, timestamp(2026, 8, 11), 143),
                terminal_event(3, 3, timestamp(2026, 8, 17), 142),
                terminal_event(4, 4, timestamp(2026, 8, 18), 143),
                terminal_event(5, 5, timestamp(2026, 8, 18), 142),
            ],
            lead_details={
                1: lead_with_custom_responsible(1, "Ana"),
                2: lead_with_custom_responsible(2, "Ana"),
                3: lead_with_custom_responsible(3, "Ana"),
                4: lead_with_custom_responsible(4, "Ana"),
                5: lead_with_custom_responsible(5, "Carlos"),
            },
            responsible_field_id=RESPONSIBLE_FIELD_ID,
        )
        rows = relatorio.build_weekly_conversion_rows(
            snapshot,
            date(2026, 8, 17),
            datetime(2026, 8, 20, 9, tzinfo=local_tz),
        )

        ana = next(row for row in rows if row["responsavel_nome"] == "Ana")
        carlos = next(row for row in rows if row["responsavel_nome"] == "Carlos")
        self.assertEqual(ana["taxa_conversao_anterior"], 50.0)
        self.assertEqual(ana["taxa_conversao_atual"], 50.0)
        self.assertEqual(ana["variacao_pp"], 0.0)
        self.assertEqual(ana["universo"], "leads_com_ultima_transicao_terminal_na_semana")
        self.assertEqual(ana["situacao_semana_atual"], "parcial")
        self.assertEqual(carlos["taxa_conversao_anterior"], "N/C")
        self.assertEqual(carlos["variacao_pp"], "N/C")

    def test_won_status_uses_system_id_not_stage_name(self) -> None:
        local_tz = timezone(timedelta(hours=-3))
        snapshot = relatorio.WeeklySnapshot(
            pipeline={"id": 123, "name": "Comercial"},
            users={999: {"name": "Usuário padrão ignorado"}},
            leads=[],
            outcome_events=[
                terminal_event(
                    1,
                    1,
                    int(datetime(2026, 8, 17, 12, tzinfo=local_tz).timestamp()),
                    142,
                )
            ],
            lead_details={1: lead_with_custom_responsible(1, "Ana")},
            responsible_field_id=RESPONSIBLE_FIELD_ID,
        )
        rows = relatorio.build_weekly_conversion_rows(
            snapshot,
            date(2026, 8, 17),
            datetime(2026, 8, 24, 9, tzinfo=local_tz),
        )
        self.assertEqual(rows[0]["servicos_iniciados_atual"], 1)
        self.assertEqual(rows[0]["taxa_conversao_atual"], 100.0)

    def test_latest_terminal_transition_wins_without_closed_at_reconciliation(self) -> None:
        local_tz = timezone(timedelta(hours=-3))
        first = int(datetime(2026, 8, 17, 10, tzinfo=local_tz).timestamp())
        second = int(datetime(2026, 8, 18, 10, tzinfo=local_tz).timestamp())
        lead = lead_with_custom_responsible(1, "Ana", closed_at=0)
        snapshot = relatorio.WeeklySnapshot(
            pipeline={"id": 123, "name": "Comercial"},
            users={},
            leads=[lead],
            outcome_events=[
                terminal_event(1, 1, first, 143),
                terminal_event(2, 1, second, 142),
            ],
            lead_details={1: lead},
            responsible_field_id=RESPONSIBLE_FIELD_ID,
        )

        rows = relatorio.build_weekly_conversion_rows(
            snapshot,
            date(2026, 8, 17),
            datetime(2026, 8, 24, 9, tzinfo=local_tz),
        )
        audit = relatorio.build_closure_event_rows(
            snapshot,
            date(2026, 8, 17),
            datetime(2026, 8, 24, 9, tzinfo=local_tz),
        )

        self.assertEqual(rows[0]["total_leads_atual"], 1)
        self.assertEqual(rows[0]["servicos_iniciados_atual"], 1)
        self.assertEqual(
            [row["considerado_no_indicador"] for row in audit], ["não", "sim"]
        )


class RemainingConsolidationsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.local_tz = timezone(timedelta(hours=-3))
        self.pipeline = {
            "id": 123,
            "name": "Comercial",
            "_embedded": {
                "statuses": [
                    {"id": 10, "name": "Novo", "sort": 10},
                    {"id": 20, "name": "Agendado", "sort": 20},
                    {"id": 142, "name": "Serviço iniciado", "sort": 100},
                    {"id": 143, "name": "Perdido", "sort": 110},
                ]
            },
        }
        self.users = {1: {"name": "Ana"}, 2: {"name": "Carlos"}}
        self.reasons = [{"id": 50, "name": "Preço", "sort": 10}]

    def ts(self, year, month, day, hour=12):
        return int(
            datetime(year, month, day, hour, tzinfo=self.local_tz).timestamp()
        )

    def test_movement_deduplicates_user_and_lead(self) -> None:
        snapshot = relatorio.WeeklySnapshot(
            pipeline=self.pipeline,
            users=self.users,
            leads=[],
            events=[
                {"created_at": self.ts(2026, 8, 17), "entity_id": 100, "created_by": 1, "type": "lead_status_changed"},
                {"created_at": self.ts(2026, 8, 18), "entity_id": 100, "created_by": 1, "type": "common_note_added"},
                {"created_at": self.ts(2026, 8, 18), "entity_id": 100, "created_by": 2, "type": "common_note_added"},
                {"created_at": self.ts(2026, 8, 18), "entity_id": 101, "created_by": 0, "type": "lead_added"},
            ],
            lead_details={100: lead_with_custom_responsible(100, "Ana")},
            responsible_field_id=RESPONSIBLE_FIELD_ID,
        )
        rows, method = relatorio.build_weekly_movement_rows(
            snapshot,
            date(2026, 8, 17),
            datetime(2026, 8, 20, tzinfo=self.local_tz),
        )
        self.assertEqual(sum(row["atendimentos_semana_atual"] for row in rows), 1)
        self.assertEqual(rows[0]["responsavel_nome"], "Ana")
        self.assertEqual(rows[0]["leads_unicos_atual"], 1)
        self.assertEqual(method["eventos_sem_usuario_excluidos_atual"], 1)

    def test_weekly_new_leads_and_stage_totals_close(self) -> None:
        closed_leads = [
            lead_with_custom_responsible(10, "Ana", status_id=142),
            lead_with_custom_responsible(11, "Carlos", status_id=143, loss_reason_id=50),
        ]
        created_leads = [
            lead_with_custom_responsible(20, "Ana", created_at=self.ts(2026, 8, 10)),
            lead_with_custom_responsible(21, "Ana", created_at=self.ts(2026, 8, 17)),
            lead_with_custom_responsible(22, "Carlos", created_at=self.ts(2026, 8, 18)),
        ]
        snapshot = relatorio.WeeklySnapshot(
            pipeline=self.pipeline,
            users=self.users,
            leads=closed_leads,
            created_leads=created_leads,
            loss_reasons=self.reasons,
            outcome_events=[
                terminal_event(1, 10, self.ts(2026, 8, 17), 142),
                terminal_event(2, 11, self.ts(2026, 8, 18), 143),
            ],
            lead_details={lead["id"]: lead for lead in [*closed_leads, *created_leads]},
            responsible_field_id=RESPONSIBLE_FIELD_ID,
        )
        new_rows = relatorio.build_weekly_new_leads_rows(
            snapshot, date(2026, 8, 17), datetime(2026, 8, 20, tzinfo=self.local_tz)
        )
        stage_rows = relatorio.build_consultant_stage_rows(
            snapshot, date(2026, 8, 17), datetime(2026, 8, 20, tzinfo=self.local_tz)
        )
        self.assertEqual(sum(row["novos_leads_atual"] for row in new_rows), 2)
        self.assertEqual(sum(row["quantidade_atual"] for row in stage_rows), 2)

    def test_lost_composition_uses_lost_denominator(self) -> None:
        snapshot = relatorio.WeeklySnapshot(
            pipeline=self.pipeline,
            users=self.users,
            leads=[],
            loss_reasons=self.reasons,
            outcome_events=[
                terminal_event(1, 1, self.ts(2026, 8, 17), 143),
                terminal_event(2, 2, self.ts(2026, 8, 18), 143),
            ],
            lead_details={
                1: lead_with_custom_responsible(1, "Ana", status_id=143, loss_reason_id=50),
                2: lead_with_custom_responsible(2, "Carlos", status_id=143, loss_reason_id=None),
            },
            responsible_field_id=RESPONSIBLE_FIELD_ID,
        )
        rows = relatorio.build_lost_composition_rows(
            snapshot, date(2026, 8, 17), datetime(2026, 8, 20, tzinfo=self.local_tz)
        )
        populated = [row for row in rows if row["quantidade_atual"]]
        self.assertEqual(len(populated), 2)
        self.assertEqual(sum(row["percentual_atual"] for row in populated), 100.0)
        self.assertEqual(populated[0]["total_perdidos_atual"], 2)

    def test_monthly_weeks_and_summary_reconcile(self) -> None:
        leads = [
            {"created_at": self.ts(2026, 7, 1), "status_id": 142},
            {"created_at": self.ts(2026, 7, 15), "status_id": 20},
            {"created_at": self.ts(2026, 7, 31), "status_id": 143},
        ]
        snapshot = relatorio.MonthlySnapshot(
            pipeline=self.pipeline,
            users=self.users,
            loss_reasons=self.reasons,
            leads=[
                {**lead, "updated_at": self.ts(2026, 7, index + 1)}
                for index, lead in enumerate(leads)
            ],
            created_leads=leads,
        )
        extracted = datetime(2026, 8, 1, tzinfo=self.local_tz)
        week_rows = relatorio.build_monthly_week_rows(
            snapshot, "2026-07", date(2026, 7, 27), extracted
        )
        summary = relatorio.build_monthly_summary_rows(
            snapshot, "2026-07", extracted
        )[0]
        self.assertEqual(sum(row["novos_leads"] for row in week_rows), 3)
        self.assertEqual(summary["novos_leads"], 3)
        self.assertEqual(
            summary["servicos_iniciados"]
            + summary["agendados"]
            + summary["perdidos"]
            + summary["em_andamento"],
            3,
        )
        self.assertEqual(week_rows[0]["variacao_servicos_iniciados_pp"], "N/A")


if __name__ == "__main__":
    unittest.main()
