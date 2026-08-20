import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

import processar_atendimentos as attendance
import relatorio


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

    def test_counts_are_optional_in_manual_input(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tempo_resposta.csv"
            path.write_text(
                "responsavel_nome;tempo_medio_minutos_anterior;tempo_medio_minutos_atual\n"
                "Vitor;9;8\nMilena;5;12\n",
                encoding="utf-8",
            )
            rows = relatorio.build_manual_response_time_rows(
                path,
                date(2026, 8, 10),
                datetime(2026, 8, 18, tzinfo=timezone.utc),
            )
        self.assertEqual(rows[0]["conversas_anterior"], "N/C")
        self.assertEqual(rows[0]["variacao_minutos"], -1.0)
        self.assertEqual(rows[1]["variacao_minutos"], 7.0)

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
    def create_conversations(self, root: Path, count: int) -> Path:
        week_dir = root / "2026-08-17"
        week_dir.mkdir(parents=True)
        for index in range(1, count + 1):
            (week_dir / f"{index:02d}.txt").write_text(
                f"Cliente: Preciso revisar o carro {index}.\nOficina: Qual é o modelo?\n",
                encoding="utf-8",
            )
        return week_dir

    def test_exactly_three_conversations_are_required(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            week_dir = self.create_conversations(root, 2)
            with self.assertRaises(attendance.ManualAttendanceError):
                attendance.find_attendance_conversations(week_dir)

    def test_sensitive_data_is_redacted_before_analysis(self) -> None:
        source = (
            "[13/08/2026 09:10] João Silva: Meu nome é João Silva, telefone (11) 98765-4321.\n"
            "[13/08/2026 09:11] Milena: A placa é ABC1D23 e o e-mail é joao@example.com.\n"
            "Endereço: Rua das Flores, 10\n"
        )
        sanitized = attendance.redact_sensitive_data(source)
        self.assertNotIn("João Silva", sanitized)
        self.assertNotIn("98765-4321", sanitized)
        self.assertNotIn("ABC1D23", sanitized)
        self.assertNotIn("joao@example.com", sanitized)
        self.assertNotIn("Rua das Flores", sanitized)
        self.assertIn("[TELEFONE REMOVIDO]", sanitized)
        self.assertIn("PARTICIPANTE", sanitized)

    def test_three_independent_analyses_are_written_and_reused(self) -> None:
        calls: list[int] = []

        def fake_analyzer(conversation: str, slot: int, model: str, prompt: str) -> str:
            calls.append(slot)
            return f"**Resumo do que aparece**\n\nAnálise independente {slot}."

        with tempfile.TemporaryDirectory() as input_directory, tempfile.TemporaryDirectory() as output_directory:
            input_root = Path(input_directory)
            output_root = Path(output_directory)
            self.create_conversations(input_root, 3)
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

    def test_changed_conversation_invalidates_manifest(self) -> None:
        def fake_analyzer(conversation: str, slot: int, model: str, prompt: str) -> str:
            return f"Análise {slot}"

        with tempfile.TemporaryDirectory() as input_directory, tempfile.TemporaryDirectory() as output_directory:
            input_root = Path(input_directory)
            output_root = Path(output_directory)
            week_dir = self.create_conversations(input_root, 3)
            attendance.process_attendances(
                date(2026, 8, 17),
                input_root=input_root,
                output_root=output_root,
                force=True,
                analyze_fn=fake_analyzer,
            )
            (week_dir / "02.txt").write_text("Cliente: conversa alterada", encoding="utf-8")
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
