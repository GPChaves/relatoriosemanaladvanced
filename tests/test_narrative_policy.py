from __future__ import annotations

import unittest

from narrative_policy import narrative_policy_violations


class NarrativePolicyTests(unittest.TestCase):
    def test_relevant_limitation_is_natural_and_concrete(self) -> None:
        text = (
            "## Tempo de resposta\n\n"
            "Não tive como aferir o tempo de resposta porque a conversa não registra "
            "os horários das mensagens."
        )

        self.assertEqual(narrative_policy_violations(text), ())

    def test_relevant_limitation_requires_authorial_voice_and_concrete_reason(self) -> None:
        impersonal = (
            "## Tempo de resposta\n\n"
            "Não foi possível aferir o tempo de resposta porque faltam os horários."
        )
        unexplained = (
            "## Tempo de resposta\n\nNão tive como aferir o tempo de resposta."
        )

        self.assertTrue(narrative_policy_violations(impersonal))
        self.assertTrue(narrative_policy_violations(unexplained))

    def test_irrelevant_limitation_can_be_omitted(self) -> None:
        text = (
            "## Atendimento\n\n"
            "O cliente explicou o serviço e recebeu uma orientação objetiva sobre o próximo passo."
        )

        self.assertEqual(narrative_policy_violations(text), ())

    def test_question_followed_by_inaccessible_audio_is_not_penalized(self) -> None:
        source = (
            "Cliente: O serviço fica pronto hoje?\n"
            "[áudio não transcrito]\n"
            "Cliente: Obrigado."
        )
        neutral_analysis = (
            "## Atendimento — Cliente — Lead 1\n\n"
            "Depois da pergunta, há uma mensagem de áudio e o cliente agradece."
        )
        unsupported_criticism = (
            "## Atendimento — Cliente — Lead 1\n\n"
            "O áudio não pôde ser analisado, mas faltou responder à pergunta do cliente."
        )

        self.assertEqual(
            narrative_policy_violations(neutral_analysis, source_text=source), ()
        )
        self.assertTrue(
            any(
                "conteúdo inacessível" in violation
                for violation in narrative_policy_violations(
                    unsupported_criticism, source_text=source
                )
            )
        )
        invented_persistence = (
            "## Atendimento — Cliente — Lead 1\n\n"
            "Não tive acesso ao áudio. Faltou responder, e a dúvida persistiu."
        )
        self.assertTrue(
            narrative_policy_violations(invented_persistence, source_text=source)
        )

    def test_explicit_persistent_doubt_supports_proportional_analysis(self) -> None:
        source = (
            "Cliente: O serviço fica pronto hoje?\n"
            "[áudio não transcrito]\n"
            "Cliente: continuo sem entender qual é o prazo."
        )
        analysis = (
            "## Atendimento — Cliente — Lead 1\n\n"
            "A dúvida persistiu: depois do áudio, o cliente disse que continuava sem "
            "entender o prazo."
        )

        self.assertEqual(
            narrative_policy_violations(analysis, source_text=source), ()
        )

    def test_professional_tone_accepts_level_three_and_rejects_bureaucratic_form(self) -> None:
        natural = "## Continuidade\n\nO atendimento ficou sem continuidade."
        bureaucratic = (
            "## Continuidade\n\n"
            "Identificou-se ausência de continuidade no atendimento."
        )

        self.assertEqual(narrative_policy_violations(natural), ())
        self.assertTrue(
            any(
                "tom natural 3/10" in violation
                for violation in narrative_policy_violations(bureaucratic)
            )
        )

    def test_external_source_framing_is_rejected(self) -> None:
        text = (
            "## Limitação\n\n"
            "O material recebido não permitiu analisar o atendimento."
        )

        self.assertTrue(
            any(
                "material recebido" in violation
                for violation in narrative_policy_violations(text)
            )
        )


if __name__ == "__main__":
    unittest.main()
