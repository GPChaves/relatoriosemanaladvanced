import json
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date, datetime, timezone
from io import StringIO
from pathlib import Path

import processar_atendimentos as attendance
import relatorio


PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"test-image"
JPG_BYTES = b"\xff\xd8\xff" + b"test-image"


class ManualResponseTimeTests(unittest.TestCase):
    def test_semicolon_csv_and_decimal_comma_are_normalized(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tempo_resposta.csv"
            path.write_text(
                "responsavel_nome;tempo_medio_minutos_anterior;"
                "tempo_medio_minutos_atual\n"
                "Milena - Advanced Mecanica Especializada;7,5;5,0\n",
                encoding="utf-8",
            )
            rows = relatorio.build_manual_response_time_rows(
                path,
                date(2026, 8, 17),
                datetime(2026, 8, 24, tzinfo=timezone.utc),
            )
        self.assertEqual(rows[0]["status_dado"], "disponivel")
        self.assertEqual(rows[0]["tempo_medio_minutos_anterior"], 7.5)
        self.assertEqual(rows[0]["tempo_medio_minutos_atual"], 5.0)
        self.assertEqual(rows[0]["variacao_minutos"], -2.5)
        self.assertEqual(rows[0]["responsavel_nome"], "Milena")
        self.assertEqual(rows[0]["conversas_anterior"], "")
        self.assertNotIn("manual", rows[0]["definicao"].casefold())

    def test_consultant_differences_excludes_response_time_input(self) -> None:
        manifest = json.loads(
            (attendance.ROOT / "prompts" / "generativos" / "manifest.json").read_text(
                encoding="utf-8"
            )
        )
        section = next(item for item in manifest["weekly"] if item["id"] == "04_17")

        self.assertNotIn("09_tempo_medio_resposta.csv", section["inputs"])
        self.assertTrue(section["manager_context"])
        self.assertTrue(manifest["attendance"]["manager_context_for_consolidation"])

    def test_duplicate_responsible_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tempo_resposta.csv"
            path.write_text(
                "responsavel_nome;tempo_medio_minutos_anterior;"
                "tempo_medio_minutos_atual\n"
                "Vitor;10;8\nVitor - Advanced Mecânica Especializada;9;7\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                relatorio.build_manual_response_time_rows(
                    path,
                    date(2026, 8, 17),
                    datetime(2026, 8, 24, tzinfo=timezone.utc),
                )


class AttendanceInputTests(unittest.TestCase):
    def write_metadata(self, week_dir: Path, count: int = 3) -> None:
        rows = ["atendimento;cliente_nome;lead_id"]
        rows.extend(
            f"{index};Cliente {index};{65000000 + index}"
            for index in range(1, count + 1)
        )
        (week_dir / attendance.METADATA_NAME).write_text(
            "\n".join(rows) + "\n", encoding="utf-8"
        )

    def create_images(self, root: Path, count: int) -> Path:
        week_dir = root / "2026-08-17"
        week_dir.mkdir(parents=True)
        for index in range(1, count + 1):
            (week_dir / f"{index:02d}.png").write_bytes(PNG_BYTES + bytes([index]))
        self.write_metadata(week_dir, count)
        return week_dir

    def create_texts(self, root: Path, count: int = 3) -> Path:
        week_dir = root / "2026-08-17"
        week_dir.mkdir(parents=True)
        for index in range(1, count + 1):
            (week_dir / f"{index:02d}.txt").write_text(
                f"Cliente: Preciso de ajuda {index}.\nConsultor: Posso verificar.\n",
                encoding="utf-8",
            )
        self.write_metadata(week_dir, count)
        return week_dir

    def create_mixed_sources(self, root: Path) -> Path:
        week_dir = root / "2026-08-17"
        week_dir.mkdir(parents=True)
        (week_dir / "01.png").write_bytes(PNG_BYTES)
        (week_dir / "02.txt").write_text(
            "Cliente: Qual é o prazo?\nConsultor: Vou confirmar.\n", encoding="utf-8"
        )
        (week_dir / "03.jpg").write_bytes(JPG_BYTES)
        self.write_metadata(week_dir)
        return week_dir

    def test_exactly_three_images_are_required(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            week_dir = self.create_images(root, 2)
            with self.assertRaises(attendance.ManualAttendanceError):
                attendance.find_attendance_images(week_dir)

    def write_agent_outputs(self, preparation: attendance.AttendancePreparation) -> None:
        for source in preparation.sources:
            source.analysis_path.write_text(
                f"{source.report_title}\n\n**Resumo do que aparece**\n\n"
                f"Análise independente {source.slot}.\n",
                encoding="utf-8",
            )
        consolidated_titles = "\n\n".join(
            source.report_title.replace("## ", "### ", 1)
            for source in preparation.sources
        )
        preparation.combined_path.write_text(
            "## Revisão da qualidade dos atendimentos\n\n"
            f"{consolidated_titles}\n",
            encoding="utf-8",
        )

    def test_prepare_returns_ordered_paths_and_hashes_without_calling_ai(self) -> None:
        with tempfile.TemporaryDirectory() as input_directory, tempfile.TemporaryDirectory() as output_directory:
            input_root = Path(input_directory)
            output_root = Path(output_directory)
            self.create_images(input_root, 3)
            preparation = attendance.prepare_attendances(
                date(2026, 8, 17),
                input_root=input_root,
                output_root=output_root,
            )

        self.assertEqual([image.slot for image in preparation.images], [1, 2, 3])
        self.assertEqual([image.path.name for image in preparation.images], ["01.png", "02.png", "03.png"])
        self.assertEqual(
            [image.analysis_path.name for image in preparation.images],
            ["01_analise.md", "02_analise.md", "03_analise.md"],
        )
        self.assertTrue(all(len(image.sha256) == 64 for image in preparation.images))
        self.assertEqual(preparation.sources[0].customer_name, "Cliente 1")
        self.assertEqual(preparation.sources[0].lead_id, 65000001)
        self.assertFalse((preparation.analysis_dir / attendance.MANIFEST_NAME).exists())
        self.assertFalse(preparation.combined_path.exists())

    def test_prepare_accepts_three_text_conversations(self) -> None:
        with tempfile.TemporaryDirectory() as input_directory, tempfile.TemporaryDirectory() as output_directory:
            input_root = Path(input_directory)
            self.create_texts(input_root)
            preparation = attendance.prepare_attendances(
                date(2026, 8, 17), input_root=input_root, output_root=Path(output_directory)
            )

        self.assertEqual([source.source_type for source in preparation.sources], ["text"] * 3)
        self.assertEqual([source.path.name for source in preparation.sources], ["01.txt", "02.txt", "03.txt"])

    def test_prepare_accepts_mixed_image_and_text_sources(self) -> None:
        with tempfile.TemporaryDirectory() as input_directory, tempfile.TemporaryDirectory() as output_directory:
            input_root = Path(input_directory)
            self.create_mixed_sources(input_root)
            preparation = attendance.prepare_attendances(
                date(2026, 8, 17), input_root=input_root, output_root=Path(output_directory)
            )
            payload = attendance.preparation_payload(preparation)

        self.assertEqual([item["type"] for item in payload["sources"]], ["image", "text", "image"])
        self.assertNotIn("images", payload)

    def test_empty_text_conversation_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            week_dir = self.create_texts(root)
            (week_dir / "02.txt").write_text("   \n", encoding="utf-8")
            with self.assertRaisesRegex(attendance.ManualAttendanceError, "vazia"):
                attendance.find_attendance_sources(week_dir)

    def test_finalize_requires_individual_and_consolidated_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as input_directory, tempfile.TemporaryDirectory() as output_directory:
            input_root = Path(input_directory)
            output_root = Path(output_directory)
            self.create_images(input_root, 3)
            preparation = attendance.prepare_attendances(
                date(2026, 8, 17),
                input_root=input_root,
                output_root=output_root,
            )
            for image in preparation.images:
                image.analysis_path.write_text(
                    f"{image.report_title}\n\nAnálise {image.slot}\n", encoding="utf-8"
                )

            with self.assertRaisesRegex(attendance.ManualAttendanceError, "consolidada"):
                attendance.finalize_attendances(
                    date(2026, 8, 17), input_root=input_root, output_root=output_root
                )
            self.assertFalse((preparation.analysis_dir / attendance.MANIFEST_NAME).exists())

    def test_administrator_account_is_not_accepted_as_consultant(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tempo_resposta.csv"
            path.write_text(
                "responsavel_nome;tempo_medio_minutos_anterior;"
                "tempo_medio_minutos_atual\nAdvanced Mecanica;10;8\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "conta administradora"):
                relatorio.build_manual_response_time_rows(
                    path,
                    date(2026, 8, 17),
                    datetime(2026, 8, 24, tzinfo=timezone.utc),
                )

    def test_prepare_command_outputs_machine_readable_contract(self) -> None:
        with tempfile.TemporaryDirectory() as input_directory, tempfile.TemporaryDirectory() as output_directory:
            input_root = Path(input_directory)
            output_root = Path(output_directory)
            self.create_images(input_root, 3)
            stdout = StringIO()
            with redirect_stdout(stdout):
                exit_code = attendance.main(
                    [
                        "prepare",
                        "--week-start", "2026-08-17",
                        "--input-root", str(input_root),
                        "--output-root", str(output_root),
                    ]
                )
            payload = json.loads(stdout.getvalue())

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["week_start"], "2026-08-17")
        self.assertEqual(len(payload["sources"]), 3)
        self.assertIsNone(payload["avaliacao_gestor_path"])
        self.assertEqual(payload["sources"][2]["analysis_path"].split("\\")[-1], "03_analise.md")
        self.assertEqual(payload["sources"][2]["titulo_obrigatorio"], "## Atendimento — Cliente 3 — Lead 65000003")

    def test_finalize_registers_deterministic_manifest_and_validate_reuses_it(self) -> None:
        with tempfile.TemporaryDirectory() as input_directory, tempfile.TemporaryDirectory() as output_directory:
            input_root = Path(input_directory)
            output_root = Path(output_directory)
            self.create_images(input_root, 3)
            preparation = attendance.prepare_attendances(
                date(2026, 8, 17), input_root=input_root, output_root=output_root
            )
            self.write_agent_outputs(preparation)
            finalized = attendance.finalize_attendances(
                date(2026, 8, 17), input_root=input_root, output_root=output_root
            )
            manifest_path = finalized.analysis_dir / attendance.MANIFEST_NAME
            first_manifest_text = manifest_path.read_text(encoding="utf-8")
            manifest = json.loads(first_manifest_text)
            self.assertEqual(manifest["version"], 5)
            self.assertEqual(len(manifest["sources"]), 3)
            self.assertEqual(len(manifest["analyses"]), 3)
            self.assertEqual(manifest["combined"]["filename"], attendance.COMBINED_NAME)

            attendance.finalize_attendances(
                date(2026, 8, 17), input_root=input_root, output_root=output_root
            )
            self.assertEqual(manifest_path.read_text(encoding="utf-8"), first_manifest_text)
            validated = attendance.validate_attendance_artifacts(
                date(2026, 8, 17), input_root=input_root, output_root=output_root
            )
            self.assertTrue(validated.reused)

    def test_optional_manager_assessment_is_exposed_and_hashed(self) -> None:
        with (
            tempfile.TemporaryDirectory() as input_directory,
            tempfile.TemporaryDirectory() as manager_directory,
            tempfile.TemporaryDirectory() as output_directory,
        ):
            input_root = Path(input_directory)
            manager_root = Path(manager_directory)
            output_root = Path(output_directory)
            self.create_images(input_root, 3)
            manager_week = manager_root / "2026-08-17"
            manager_week.mkdir(parents=True)
            assessment = manager_week / "avaliacao.md"
            assessment.write_text(
                "## Visão geral\n\nAcompanhar clareza no próximo passo.\n",
                encoding="utf-8",
            )
            preparation = attendance.prepare_attendances(
                date(2026, 8, 17),
                input_root=input_root,
                manager_input_root=manager_root,
                output_root=output_root,
            )
            payload = attendance.preparation_payload(preparation)
            self.write_agent_outputs(preparation)
            attendance.finalize_attendances(
                date(2026, 8, 17),
                input_root=input_root,
                manager_input_root=manager_root,
                output_root=output_root,
            )

            self.assertEqual(payload["avaliacao_gestor_path"], str(assessment))
            manifest = json.loads(
                (preparation.analysis_dir / attendance.MANIFEST_NAME).read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(manifest["manager_assessment"]["filename"], "avaliacao.md")

            assessment.write_text(
                "## Visão geral\n\nConteúdo alterado.\n", encoding="utf-8"
            )
            with self.assertRaises(attendance.ManualAttendanceError):
                attendance.validate_attendance_artifacts(
                    date(2026, 8, 17),
                    input_root=input_root,
                    manager_input_root=manager_root,
                    output_root=output_root,
                )

    def test_prepare_requires_customer_and_lead_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as input_directory, tempfile.TemporaryDirectory() as output_directory:
            input_root = Path(input_directory)
            week_dir = self.create_images(input_root, 3)
            (week_dir / attendance.METADATA_NAME).unlink()

            with self.assertRaisesRegex(attendance.ManualAttendanceError, "Metadados"):
                attendance.prepare_attendances(
                    date(2026, 8, 17),
                    input_root=input_root,
                    output_root=Path(output_directory),
                )

    def test_finalize_rejects_analysis_without_customer_and_lead_title(self) -> None:
        with tempfile.TemporaryDirectory() as input_directory, tempfile.TemporaryDirectory() as output_directory:
            input_root = Path(input_directory)
            output_root = Path(output_directory)
            self.create_images(input_root, 3)
            preparation = attendance.prepare_attendances(
                date(2026, 8, 17), input_root=input_root, output_root=output_root
            )
            for source in preparation.sources:
                source.analysis_path.write_text("## Atendimento\n", encoding="utf-8")
            preparation.combined_path.write_text(
                "## Amostragem qualitativa dos atendimentos\n", encoding="utf-8"
            )

            with self.assertRaisesRegex(attendance.ManualAttendanceError, "deve começar"):
                attendance.finalize_attendances(
                    date(2026, 8, 17), input_root=input_root, output_root=output_root
                )

    def test_process_attendances_only_validates_and_never_generates(self) -> None:
        with tempfile.TemporaryDirectory() as input_directory, tempfile.TemporaryDirectory() as output_directory:
            input_root = Path(input_directory)
            output_root = Path(output_directory)
            self.create_images(input_root, 3)
            with self.assertRaisesRegex(attendance.ManualAttendanceError, "subagentes externos"):
                attendance.process_attendances(
                    date(2026, 8, 17), input_root=input_root, output_root=output_root, force=True
                )

    def test_changed_image_invalidates_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as input_directory, tempfile.TemporaryDirectory() as output_directory:
            input_root = Path(input_directory)
            output_root = Path(output_directory)
            week_dir = self.create_images(input_root, 3)
            preparation = attendance.prepare_attendances(
                date(2026, 8, 17), input_root=input_root, output_root=output_root
            )
            self.write_agent_outputs(preparation)
            attendance.finalize_attendances(
                date(2026, 8, 17), input_root=input_root, output_root=output_root
            )
            (week_dir / "02.png").write_bytes(PNG_BYTES + b"changed")
            with self.assertRaises(attendance.ManualAttendanceError):
                attendance.validate_attendance_artifacts(
                    date(2026, 8, 17), input_root=input_root, output_root=output_root
                )

    def test_changed_analysis_invalidates_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as input_directory, tempfile.TemporaryDirectory() as output_directory:
            input_root = Path(input_directory)
            output_root = Path(output_directory)
            self.create_images(input_root, 3)
            preparation = attendance.prepare_attendances(
                date(2026, 8, 17), input_root=input_root, output_root=output_root
            )
            self.write_agent_outputs(preparation)
            attendance.finalize_attendances(
                date(2026, 8, 17), input_root=input_root, output_root=output_root
            )
            preparation.images[0].analysis_path.write_text("Análise alterada\n", encoding="utf-8")
            with self.assertRaises(attendance.ManualAttendanceError):
                attendance.validate_attendance_artifacts(
                    date(2026, 8, 17), input_root=input_root, output_root=output_root
                )

    def test_changed_text_source_invalidates_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as input_directory, tempfile.TemporaryDirectory() as output_directory:
            input_root = Path(input_directory)
            output_root = Path(output_directory)
            week_dir = self.create_texts(input_root)
            preparation = attendance.prepare_attendances(
                date(2026, 8, 17), input_root=input_root, output_root=output_root
            )
            self.write_agent_outputs(preparation)
            attendance.finalize_attendances(
                date(2026, 8, 17), input_root=input_root, output_root=output_root
            )
            (week_dir / "02.txt").write_text(
                "Cliente: Conteúdo alterado.\nConsultor: Nova resposta.\n", encoding="utf-8"
            )
            with self.assertRaises(attendance.ManualAttendanceError):
                attendance.validate_attendance_artifacts(
                    date(2026, 8, 17), input_root=input_root, output_root=output_root
                )


if __name__ == "__main__":
    unittest.main()
