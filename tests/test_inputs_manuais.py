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


class ManualResponseTimeTests(unittest.TestCase):
    def test_semicolon_csv_and_decimal_comma_are_normalized(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tempo_resposta.csv"
            path.write_text(
                "responsavel_nome;conversas_anterior;tempo_medio_minutos_anterior;"
                "conversas_atual;tempo_medio_minutos_atual\n"
                "Milena;12;7,5;10;5,0\n",
                encoding="utf-8",
            )
            rows = relatorio.build_manual_response_time_rows(
                path,
                date(2026, 8, 17),
                datetime(2026, 8, 24, tzinfo=timezone.utc),
            )
        self.assertEqual(rows[0]["status_dado"], "disponivel_manual")
        self.assertEqual(rows[0]["tempo_medio_minutos_anterior"], 7.5)
        self.assertEqual(rows[0]["tempo_medio_minutos_atual"], 5.0)
        self.assertEqual(rows[0]["variacao_minutos"], -2.5)

    def test_duplicate_responsible_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tempo_resposta.csv"
            path.write_text(
                "responsavel_nome;conversas_anterior;tempo_medio_minutos_anterior;"
                "conversas_atual;tempo_medio_minutos_atual\n"
                "Vitor;2;10;2;8\nVitor;1;9;1;7\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                relatorio.build_manual_response_time_rows(
                    path,
                    date(2026, 8, 17),
                    datetime(2026, 8, 24, tzinfo=timezone.utc),
                )


class AttendanceInputTests(unittest.TestCase):
    def create_images(self, root: Path, count: int) -> Path:
        week_dir = root / "2026-08-17"
        week_dir.mkdir(parents=True)
        for index in range(1, count + 1):
            (week_dir / f"{index:02d}.png").write_bytes(PNG_BYTES + bytes([index]))
        return week_dir

    def test_exactly_three_images_are_required(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            week_dir = self.create_images(root, 2)
            with self.assertRaises(attendance.ManualAttendanceError):
                attendance.find_attendance_images(week_dir)

    def write_agent_outputs(self, preparation: attendance.AttendancePreparation) -> None:
        for image in preparation.images:
            image.analysis_path.write_text(
                f"**Resumo do que aparece**\n\nAnálise independente {image.slot}.\n",
                encoding="utf-8",
            )
        preparation.combined_path.write_text(
            "## Revisão da qualidade dos atendimentos\n\nSíntese feita por outro subagente.\n",
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
        self.assertFalse((preparation.analysis_dir / attendance.MANIFEST_NAME).exists())
        self.assertFalse(preparation.combined_path.exists())

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
                image.analysis_path.write_text(f"Análise {image.slot}\n", encoding="utf-8")

            with self.assertRaisesRegex(attendance.ManualAttendanceError, "consolidada"):
                attendance.finalize_attendances(
                    date(2026, 8, 17), input_root=input_root, output_root=output_root
                )
            self.assertFalse((preparation.analysis_dir / attendance.MANIFEST_NAME).exists())

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
        self.assertEqual(len(payload["images"]), 3)
        self.assertEqual(payload["images"][2]["analysis_path"].split("\\")[-1], "03_analise.md")

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
            self.assertEqual(manifest["version"], 2)
            self.assertEqual(len(manifest["images"]), 3)
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


if __name__ == "__main__":
    unittest.main()
