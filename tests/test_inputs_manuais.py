import tempfile
import unittest
from datetime import date, datetime, timezone
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

    def test_three_independent_analyses_are_written_and_reused(self) -> None:
        calls: list[int] = []

        def fake_analyzer(path: Path, slot: int, model: str, prompt: str) -> str:
            calls.append(slot)
            return f"**Resumo do que aparece**\n\nAnálise independente {slot}."

        with tempfile.TemporaryDirectory() as input_directory, tempfile.TemporaryDirectory() as output_directory:
            input_root = Path(input_directory)
            output_root = Path(output_directory)
            self.create_images(input_root, 3)
            result = attendance.process_attendances(
                date(2026, 8, 17),
                input_root=input_root,
                output_root=output_root,
                force=True,
                analyze_fn=fake_analyzer,
            )
            self.assertFalse(result.reused)
            self.assertEqual(sorted(calls), [1, 2, 3])
            self.assertIn("Atendimento 3", result.combined_path.read_text(encoding="utf-8"))
            calls.clear()
            reused = attendance.process_attendances(
                date(2026, 8, 17),
                input_root=input_root,
                output_root=output_root,
                analyze_fn=fake_analyzer,
            )
            self.assertTrue(reused.reused)
            self.assertEqual(calls, [])

    def test_changed_image_invalidates_manifest(self) -> None:
        def fake_analyzer(path: Path, slot: int, model: str, prompt: str) -> str:
            return f"Análise {slot}"

        with tempfile.TemporaryDirectory() as input_directory, tempfile.TemporaryDirectory() as output_directory:
            input_root = Path(input_directory)
            output_root = Path(output_directory)
            week_dir = self.create_images(input_root, 3)
            attendance.process_attendances(
                date(2026, 8, 17),
                input_root=input_root,
                output_root=output_root,
                force=True,
                analyze_fn=fake_analyzer,
            )
            (week_dir / "02.png").write_bytes(PNG_BYTES + b"changed")
            with self.assertRaises(attendance.ManualAttendanceError):
                attendance.process_attendances(
                    date(2026, 8, 17),
                    input_root=input_root,
                    output_root=output_root,
                    validate_only=True,
                    analyze_fn=fake_analyzer,
                )


if __name__ == "__main__":
    unittest.main()
