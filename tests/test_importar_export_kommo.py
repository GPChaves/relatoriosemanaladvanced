import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

import pandas as pd

import importar_export_kommo as importer


class ImportKommoExportTests(unittest.TestCase):
    week_start = date(2026, 8, 17)
    pipeline_name = "Pipeline Oficina"

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.source = self.root / "kommo.xlsx"
        self.output_root = self.root / "outputs"
        self.manual_path = self.root / "manual" / "tempo_resposta.csv"
        self._write_source()
        self._write_manual()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _write_source(self) -> None:
        rows = [
            {
                "Lead usuário responsável": "Alice",
                "Etapa do lead": "Serviço iniciado",
                "Funil de vendas": self.pipeline_name,
                "Data Criada": "10/08/2026 09:00",
                "Última modificação": "23/08/2026 18:00",
                "Data Fechada": "23/08/2026 17:00",
            },
            {
                "Lead usuário responsável": "Bruno",
                "Etapa do lead": "Perdido (Orçamento)",
                "Funil de vendas": self.pipeline_name,
                "Data Criada": "11/08/2026 09:00",
                "Última modificação": "16/08/2026 18:00",
                "Data Fechada": "16/08/2026 17:00",
            },
            {
                "Lead usuário responsável": "Alice",
                "Etapa do lead": "Novo lead",
                "Funil de vendas": self.pipeline_name,
                "Data Criada": "17/08/2026 09:00",
                "Última modificação": "23/08/2026 18:00",
                "Data Fechada": "",
            },
            {
                "Lead usuário responsável": "Carla",
                "Etapa do lead": "Serviço iniciado",
                "Funil de vendas": self.pipeline_name,
                "Data Criada": "18/08/2026 09:00",
                "Última modificação": "23/08/2026 18:00",
                "Data Fechada": "23/08/2026 17:00",
            },
            {
                "Lead usuário responsável": "Advanced Mecânica",
                "Etapa do lead": "Perdido (Sem retorno)",
                "Funil de vendas": self.pipeline_name,
                "Data Criada": "19/08/2026 09:00",
                "Última modificação": "23/08/2026 18:00",
                "Data Fechada": "23/08/2026 17:00",
            },
            {
                "Lead usuário responsável": "Ignorado",
                "Etapa do lead": "Novo lead",
                "Funil de vendas": "Outro pipeline",
                "Data Criada": "20/08/2026 09:00",
                "Última modificação": "23/08/2026 18:00",
                "Data Fechada": "",
            },
        ]
        pd.DataFrame(rows).to_excel(self.source, index=False)

    def _write_manual(self) -> None:
        self.manual_path.parent.mkdir(parents=True, exist_ok=True)
        self.manual_path.write_text(
            "responsavel_nome,tempo_medio_minutos_anterior,"
            "tempo_medio_minutos_atual\n"
            "Alice,5,4\n"
            "Carla,7,6\n",
            encoding="utf-8",
        )

    def _build(self, **kwargs: object) -> Path:
        with mock.patch.object(
            importer, "manual_response_time_path", return_value=self.manual_path
        ):
            return importer.build_outputs(
                self.source,
                self.week_start,
                self.output_root,
                pipeline_name=self.pipeline_name,
                **kwargs,
            )

    def test_uses_configured_pipeline_and_dynamic_responsible_names(self) -> None:
        output_dir = self._build()

        conversion = pd.read_csv(output_dir / "04_conversao_responsavel.csv")
        self.assertEqual(
            set(conversion["responsavel_nome"]),
            {"Alice", "Bruno", "Carla", importer.UNASSIGNED_RESPONSIBLE},
        )
        self.assertEqual(set(conversion["pipeline_nome"]), {self.pipeline_name})
        self.assertEqual(
            set(conversion["universo"]),
            {"leads_fechados_no_periodo_por_data_de_fechamento"},
        )
        alice = conversion[conversion["responsavel_nome"] == "Alice"].iloc[0]
        self.assertEqual(alice["total_leads_atual"], 1)

        new_leads = pd.read_csv(output_dir / "07_novos_leads_semana.csv")
        self.assertNotIn("Advanced Mecânica", set(new_leads["responsavel_nome"]))
        self.assertIn(importer.UNASSIGNED_RESPONSIBLE, set(new_leads["responsavel_nome"]))
        self.assertNotIn("Ignorado", set(new_leads["responsavel_nome"]))
        self.assertEqual(new_leads["total_novos_leads_anterior"].iloc[0], 2)
        self.assertEqual(new_leads["total_novos_leads_atual"].iloc[0], 3)

        closures = pd.read_csv(output_dir / "10_eventos_fechamento.csv")
        self.assertEqual(len(closures), 4)
        self.assertEqual(set(closures["considerado_no_indicador"]), {"sim"})

    def test_missing_manual_input_leaves_no_partial_outputs(self) -> None:
        missing_manual = self.root / "nao-existe.csv"
        with mock.patch.object(
            importer, "manual_response_time_path", return_value=missing_manual
        ):
            with self.assertRaisesRegex(ValueError, "Arquivo manual não encontrado"):
                importer.build_outputs(
                    self.source,
                    self.week_start,
                    self.output_root,
                    pipeline_name=self.pipeline_name,
                )
        self.assertFalse(self.output_root.exists())

    def test_invalid_close_date_is_rejected_before_writing_outputs(self) -> None:
        frame = pd.read_excel(self.source)
        frame.loc[0, "Data Fechada"] = "data inválida"
        frame.to_excel(self.source, index=False)

        with self.assertRaisesRegex(ValueError, "Data Fechada.*data inválida"):
            self._build()

        self.assertFalse(self.output_root.exists())

    def test_existing_output_requires_force_and_preserves_other_artifacts(self) -> None:
        output_dir = self._build()
        narrative = output_dir / "generativos" / "leitura.md"
        narrative.parent.mkdir()
        narrative.write_text("preservar", encoding="utf-8")

        with self.assertRaisesRegex(FileExistsError, "--force"):
            self._build()
        self.assertEqual(narrative.read_text(encoding="utf-8"), "preservar")

        forced_output = self._build(force=True)
        self.assertEqual(forced_output, output_dir)
        self.assertEqual(narrative.read_text(encoding="utf-8"), "preservar")

    def test_month_closing_week_is_rejected_with_actionable_error(self) -> None:
        closing_week = date(2026, 8, 31)
        with self.assertRaisesRegex(ValueError, r"relatorio\.py.*API"):
            importer.build_outputs(
                self.source,
                closing_week,
                self.output_root,
                pipeline_name=self.pipeline_name,
            )
        self.assertFalse(self.output_root.exists())

    def test_parser_accepts_pipeline_name_and_force(self) -> None:
        args = importer.build_parser().parse_args(
            [
                "--source",
                str(self.source),
                "--week-start",
                self.week_start.isoformat(),
                "--pipeline-name",
                self.pipeline_name,
                "--force",
            ]
        )
        self.assertEqual(args.pipeline_name, self.pipeline_name)
        self.assertTrue(args.force)


if __name__ == "__main__":
    unittest.main()
