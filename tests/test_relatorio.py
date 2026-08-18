import csv
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import relatorio


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


class MonthlyDistributionTests(unittest.TestCase):
    def test_distribution_is_grouped_by_current_responsible(self) -> None:
        leads = [
            {"responsible_user_id": 10},
            {"responsible_user_id": 10},
            {"responsible_user_id": 20},
        ]
        users = {
            10: {"name": "Ana", "rights": {"is_active": True}},
            20: {"name": "Carlos", "rights": {"is_active": False}},
        }
        pipeline = {"id": 123, "name": "Comercial"}
        extracted_at = datetime(
            2026, 9, 1, 9, 0, tzinfo=timezone(timedelta(hours=-3))
        )

        rows = relatorio.build_monthly_distribution_rows(
            leads, users, pipeline, "2026-08", extracted_at
        )

        self.assertEqual(rows[0]["responsavel_nome"], "Ana")
        self.assertEqual(rows[0]["quantidade_leads"], 2)
        self.assertEqual(rows[0]["participacao_percentual"], 66.7)
        self.assertEqual(rows[1]["usuario_ativo"], "não")
        self.assertEqual(rows[1]["total_leads_mes"], 3)

    def test_unknown_responsible_is_preserved_in_output(self) -> None:
        rows = relatorio.build_monthly_distribution_rows(
            [{"responsible_user_id": 999}],
            {},
            {"id": 123, "name": "Comercial"},
            "2026-08",
            datetime(2026, 9, 1, tzinfo=timezone.utc),
        )
        self.assertEqual(rows[0]["responsavel_id"], 999)
        self.assertEqual(rows[0]["usuario_ativo"], "desconhecido")
        self.assertIn("999", rows[0]["responsavel_nome"])

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
                        {"id": 143, "name": "Perdido", "sort": 1000},
                    ]
                },
            },
            users={1: {"name": "Ana"}},
            loss_reasons=[{"id": 50, "name": "Motivo renomeado", "sort": 10}],
            leads=[
                {"responsible_user_id": 1, "status_id": 10, "loss_reason_id": None},
                {"responsible_user_id": 1, "status_id": 143, "loss_reason_id": 50},
            ],
        )

        rows = relatorio.build_global_stage_rows(
            snapshot,
            "2026-08",
            datetime(2026, 9, 1, tzinfo=timezone.utc),
        )
        categories = {row["categoria_relatorio"] for row in rows}

        self.assertIn("Etapa renomeada", categories)
        self.assertIn("Etapa recém-criada", categories)
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
            leads=[
                {
                    "responsible_user_id": 1,
                    "status_id": 143,
                    "loss_reason_id": 999,
                    "_embedded": {"loss_reason": {"id": 999, "name": "Novo motivo"}},
                }
            ],
        )

        rows = relatorio.build_global_stage_rows(
            snapshot,
            "2026-08",
            datetime(2026, 9, 1, tzinfo=timezone.utc),
        )
        populated = [row for row in rows if row["quantidade_leads"] == 1]
        self.assertEqual(populated[0]["categoria_relatorio"], "Perdido — Novo motivo")
        self.assertEqual(populated[0]["loss_reason_id"], 999)


class WeeklyConversionTests(unittest.TestCase):
    def test_conversion_and_percentage_point_variation(self) -> None:
        local_tz = timezone(timedelta(hours=-3))

        def timestamp(year, month, day):
            return int(datetime(year, month, day, 12, tzinfo=local_tz).timestamp())

        snapshot = relatorio.WeeklySnapshot(
            pipeline={"id": 123, "name": "Comercial"},
            users={1: {"name": "Ana"}, 2: {"name": "Carlos"}},
            leads=[
                {"created_at": timestamp(2026, 8, 10), "responsible_user_id": 1, "status_id": 142},
                {"created_at": timestamp(2026, 8, 11), "responsible_user_id": 1, "status_id": 10},
                {"created_at": timestamp(2026, 8, 17), "responsible_user_id": 1, "status_id": 142},
                {"created_at": timestamp(2026, 8, 18), "responsible_user_id": 1, "status_id": 10},
                {"created_at": timestamp(2026, 8, 18), "responsible_user_id": 2, "status_id": 142},
            ],
        )
        rows = relatorio.build_weekly_conversion_rows(
            snapshot,
            date(2026, 8, 17),
            datetime(2026, 8, 20, 9, tzinfo=local_tz),
        )

        ana = next(row for row in rows if row["responsavel_id"] == 1)
        carlos = next(row for row in rows if row["responsavel_id"] == 2)
        self.assertEqual(ana["taxa_conversao_anterior"], 50.0)
        self.assertEqual(ana["taxa_conversao_atual"], 50.0)
        self.assertEqual(ana["variacao_pp"], 0.0)
        self.assertEqual(ana["situacao_semana_atual"], "parcial")
        self.assertEqual(carlos["taxa_conversao_anterior"], "N/C")
        self.assertEqual(carlos["variacao_pp"], "N/C")

    def test_won_status_uses_system_id_not_stage_name(self) -> None:
        local_tz = timezone(timedelta(hours=-3))
        snapshot = relatorio.WeeklySnapshot(
            pipeline={"id": 123, "name": "Comercial"},
            users={1: {"name": "Ana"}},
            leads=[
                {
                    "created_at": int(
                        datetime(2026, 8, 17, 12, tzinfo=local_tz).timestamp()
                    ),
                    "responsible_user_id": 1,
                    "status_id": 142,
                }
            ],
        )
        rows = relatorio.build_weekly_conversion_rows(
            snapshot,
            date(2026, 8, 17),
            datetime(2026, 8, 24, 9, tzinfo=local_tz),
        )
        self.assertEqual(rows[0]["servicos_iniciados_atual"], 1)
        self.assertEqual(rows[0]["taxa_conversao_atual"], 100.0)


if __name__ == "__main__":
    unittest.main()
