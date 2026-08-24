import csv
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
        self.assertNotIn("04_18_limitacoes_proximos_passos.md", names)
        self.assertNotIn("13_analise_quantitativa_mes.csv", names)
        self.assertNotIn("04_13_leitura_gerencial_mes.md", names)

    def test_closing_week_requires_monthly_outputs(self) -> None:
        paths = final.expected_output_paths(Path("outputs"), date(2026, 7, 27))
        names = {path.name for path in paths}
        self.assertIn("13_analise_quantitativa_mes.csv", names)
        self.assertIn("14_resumo_consolidado_mes.csv", names)
        self.assertIn("04_13_leitura_gerencial_mes.md", names)
        self.assertEqual(final.closing_month_for_week(date(2026, 7, 27)), "2026-07")

    def test_monthly_outputs_wait_until_month_is_really_closed(self) -> None:
        week_start = date(2026, 8, 31)
        self.assertIsNone(final.closing_month_for_week(week_start, date(2026, 8, 31)))
        self.assertEqual(
            final.closing_month_for_week(week_start, date(2026, 9, 1)), "2026-08"
        )

    def test_every_required_weekly_narrative_is_rendered(self) -> None:
        rendered = {filename for _, _, filename in final.MANAGEMENT_NARRATIVES}
        self.assertEqual(rendered, set(final.WEEKLY_MARKDOWN_FILES))
        self.assertNotIn(
            ("11.", "Próximos pontos de acompanhamento", "04_18_limitacoes_proximos_passos.md"),
            final.MANAGEMENT_NARRATIVES,
        )

    def test_validation_lists_every_missing_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = final.validate_outputs(Path(directory), date(2026, 8, 17))
        self.assertFalse(result.ok)
        self.assertEqual(len(result.missing), len(final.WEEKLY_CSV_FILES) + len(final.WEEKLY_MARKDOWN_FILES))

    def test_validation_rejects_internal_production_provenance(self) -> None:
        week_start = date(2026, 8, 17)
        with tempfile.TemporaryDirectory() as directory:
            output_root = Path(directory)
            paths = final.expected_output_paths(output_root, week_start)
            for path in paths:
                path.parent.mkdir(parents=True, exist_ok=True)
                if path.suffix == ".csv":
                    path.write_text("campo\nvalor\n", encoding="utf-8")
                else:
                    path.write_text("## Seção\n\nAnálise objetiva.", encoding="utf-8")
            identification = final.week_output_dir(output_root, week_start) / "01_identificacao_periodo.csv"
            identification.write_text(
                "data_inicial,data_final\n2026-08-17,2026-08-23\n",
                encoding="utf-8",
            )
            bad = final.week_output_dir(output_root, week_start) / "generativos" / final.WEEKLY_MARKDOWN_FILES[0]
            bad.write_text(
                "## Seção\n\nEste dado foi informado manualmente.",
                encoding="utf-8",
            )

            result = final.validate_outputs(output_root, week_start)

        self.assertTrue(
            any("detalhes internos de produção" in problem for problem in result.invalid)
        )

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

    def test_comparison_change_shows_count_and_percentage(self) -> None:
        self.assertEqual(final.count_change(80, 56), "-24 (-30,0%)")
        self.assertEqual(final.count_change(0, 1), "+1")

    def test_dynamic_stage_labels_are_normalized(self) -> None:
        self.assertTrue(final.label_key("Perdido — Orçamento").startswith("perdido"))
        self.assertIn("servico iniciado", final.label_key("Serviço iniciado"))

    def test_markdown_fourth_level_heading_is_rendered_without_hashes(self) -> None:
        final.register_fonts()
        flowables = final.markdown_flowables(
            "## Seção\n\n#### Resumo do que aparece\n\nTexto.",
            final.build_styles(),
        )
        rendered_text = [getattr(flowable, "text", "") for flowable in flowables]
        self.assertIn("Resumo do que aparece", rendered_text)
        self.assertNotIn("#### Resumo do que aparece", rendered_text)

    def test_numbered_markdown_list_is_kept_together(self) -> None:
        final.register_fonts()
        flowables = final.markdown_flowables(
            "## Seção\n\n### Lista\n\n1. Primeiro\n2. Segundo",
            final.build_styles(),
        )
        self.assertEqual(len(flowables), 1)
        self.assertEqual(type(flowables[0]).__name__, "KeepTogether")

    def test_executive_summary_uses_closed_leads_as_conversion_denominator(self) -> None:
        def write_csv(path: Path, row: dict[str, object]) -> None:
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(row))
                writer.writeheader()
                writer.writerow(row)

        with tempfile.TemporaryDirectory() as directory:
            week_dir = Path(directory)
            write_csv(
                week_dir / "07_novos_leads_semana.csv",
                {"total_novos_leads_anterior": 80, "total_novos_leads_atual": 100},
            )
            write_csv(
                week_dir / "04_conversao_responsavel.csv",
                {
                    "total_leads_anterior": 10,
                    "total_leads_atual": 20,
                    "servicos_iniciados_anterior": 2,
                    "servicos_iniciados_atual": 10,
                },
            )
            write_csv(week_dir / "05_movimentacao_semanal.csv", {"status_dado": "indisponivel"})
            write_csv(
                week_dir / "11_composicao_leads_perdidos.csv",
                {
                    "motivo_perda": "Orçamento",
                    "total_perdidos_anterior": 1,
                    "total_perdidos_atual": 2,
                    "quantidade_atual": 2,
                },
            )

            final.register_fonts()
            _, cards = final.executive_summary(week_dir, final.build_styles())

        self.assertEqual(cards[1][1], "50,0%")
        self.assertEqual(cards[3][0], "Leads fechados")
        self.assertEqual(cards[3][1], "20")

    def test_generate_pdf_smoke_with_all_weekly_narratives(self) -> None:
        def write_csv(path: Path, row: dict[str, object]) -> None:
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(row))
                writer.writeheader()
                writer.writerow(row)

        with tempfile.TemporaryDirectory() as directory:
            week_dir = Path(directory)
            write_csv(
                week_dir / "01_identificacao_periodo.csv",
                {
                    "titulo": "Relatório de Desempenho Comercial",
                    "data_inicial": "2026-08-17",
                    "data_final": "2026-08-23",
                    "situacao_semana": "completa",
                },
            )
            write_csv(
                week_dir / "04_conversao_responsavel.csv",
                {
                    "responsavel_nome": "Ana",
                    "total_leads_anterior": 10,
                    "servicos_iniciados_anterior": 2,
                    "total_leads_atual": 12,
                    "servicos_iniciados_atual": 3,
                },
            )
            write_csv(
                week_dir / "05_movimentacao_semanal.csv",
                {
                    "status_dado": "disponivel",
                    "responsavel_nome": "Ana",
                    "atendimentos_semana_anterior": 8,
                    "atendimentos_semana_atual": 9,
                    "total_pares_usuario_lead_anterior": 8,
                    "total_pares_usuario_lead_atual": 9,
                    "leads_unicos_anterior": 7,
                    "leads_unicos_atual": 8,
                },
            )
            write_csv(week_dir / "06_nota_metodologica_movimentacao.csv", {"nota": "Teste"})
            write_csv(
                week_dir / "07_novos_leads_semana.csv",
                {
                    "responsavel_nome": "Ana",
                    "novos_leads_anterior": 10,
                    "novos_leads_atual": 12,
                    "total_novos_leads_anterior": 10,
                    "total_novos_leads_atual": 12,
                },
            )
            write_csv(
                week_dir / "08_etapas_por_consultor.csv",
                {
                    "responsavel_nome": "Ana",
                    "categoria_relatorio": "Serviço iniciado",
                    "quantidade_anterior": 2,
                    "quantidade_atual": 3,
                },
            )
            write_csv(
                week_dir / "09_tempo_medio_resposta.csv",
                {"status_dado": "indisponivel", "motivo_indisponibilidade": "Teste"},
            )
            write_csv(
                week_dir / "11_composicao_leads_perdidos.csv",
                {
                    "motivo_perda": "Orçamento",
                    "quantidade_anterior": 1,
                    "percentual_anterior": 100,
                    "quantidade_atual": 1,
                    "percentual_atual": 100,
                    "total_perdidos_anterior": 1,
                    "total_perdidos_atual": 1,
                },
            )
            generative_dir = week_dir / "generativos"
            generative_dir.mkdir()
            for name in final.WEEKLY_MARKDOWN_FILES:
                (generative_dir / name).write_text(
                    f"## {name.removesuffix('.md')}\n\nTexto validado para o teste.\n",
                    encoding="utf-8",
                )
            output = week_dir / "report.pdf"
            final.generate_pdf(week_dir, output, date(2026, 8, 17))
            self.assertGreater(output.stat().st_size, 1_000)
            self.assertEqual(output.read_bytes()[:4], b"%PDF")


if __name__ == "__main__":
    unittest.main()
