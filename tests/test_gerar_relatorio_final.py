import tempfile
import unittest
from datetime import date
from pathlib import Path

import gerar_relatorio_final as final


class FinalReportValidationTests(unittest.TestCase):
    def test_regular_week_does_not_require_monthly_outputs(self) -> None:
        paths = final.expected_output_paths(Path("outputs"), date(2026, 8, 17))
        names = {path.name for path in paths}
        self.assertIn("04_12_leitura_gerencial_semana.md", names)
        self.assertNotIn("13_analise_quantitativa_mes.csv", names)
        self.assertNotIn("04_13_leitura_gerencial_mes.md", names)

    def test_closing_week_requires_monthly_outputs(self) -> None:
        paths = final.expected_output_paths(Path("outputs"), date(2026, 7, 27))
        names = {path.name for path in paths}
        self.assertIn("13_analise_quantitativa_mes.csv", names)
        self.assertIn("14_resumo_consolidado_mes.csv", names)
        self.assertIn("04_13_leitura_gerencial_mes.md", names)
        self.assertEqual(final.closing_month_for_week(date(2026, 7, 27)), "2026-07")

    def test_validation_lists_every_missing_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = final.validate_outputs(Path(directory), date(2026, 8, 17))
        self.assertFalse(result.ok)
        self.assertEqual(len(result.missing), len(final.WEEKLY_CSV_FILES) + len(final.WEEKLY_MARKDOWN_FILES))

    def test_existing_pdf_requires_explicit_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.pdf"
            path.write_bytes(b"pdf")
            self.assertFalse(final.confirm_overwrite(path, lambda _: "não"))
            self.assertTrue(final.confirm_overwrite(path, lambda _: "sim"))

    def test_week_start_must_be_monday(self) -> None:
        self.assertEqual(final.parse_week_start("2026-08-17"), date(2026, 8, 17))
        with self.assertRaises(Exception):
            final.parse_week_start("2026-08-18")

    def test_report_uses_readable_print_sizes(self) -> None:
        styles = final.build_styles()
        self.assertGreaterEqual(styles["body"].fontSize, 10.5)
        self.assertGreaterEqual(styles["bullet"].fontSize, 10)
        self.assertGreaterEqual(styles["table"].fontSize, 8)
        self.assertGreaterEqual(styles["campaign_warning"].fontSize, 10)

    def test_comparison_change_shows_count_and_percentage(self) -> None:
        self.assertEqual(final.count_change(80, 56), "-24 (-30,0%)")
        self.assertEqual(final.count_change(0, 1), "+1")

    def test_response_time_uses_only_current_value_and_change_format(self) -> None:
        self.assertEqual(final.minutes(8), "8 min")
        self.assertEqual(final.minutes(-1, signed=True), "-1 min")
        self.assertEqual(final.minutes(7, signed=True), "+7 min")

    def test_dynamic_stage_labels_are_normalized(self) -> None:
        self.assertTrue(final.label_key("Perdido — Orçamento").startswith("perdido"))
        self.assertIn("servico iniciado", final.label_key("Serviço iniciado"))

    def test_google_campaign_input_path_is_week_specific(self) -> None:
        path = final.google_campaign_input_path(date(2026, 8, 10))
        self.assertEqual(path.name, "campanha_google.csv")
        self.assertEqual(path.parent.name, "2026-08-10")


if __name__ == "__main__":
    unittest.main()
