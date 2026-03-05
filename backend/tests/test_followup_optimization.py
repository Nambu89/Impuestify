"""
Tests for follow-up detection and query contextualization.

These are pure heuristic functions with no external dependencies,
so no mocks needed.
"""
import pytest
from app.utils.followup_detector import classify_followup
from app.utils.query_contextualizer import contextualize_query


# === Shared fixtures ===

IRPF_HISTORY = [
    {"role": "user", "content": "¿Cuánto IRPF pago si gano 40000 euros en Madrid?"},
    {"role": "assistant", "content": "Con unos ingresos brutos de 40.000€ en Madrid, el IRPF aproximado sería de 8.500€. Esto incluye el tramo estatal y el autonómico de la Comunidad de Madrid."},
]

DEDUCTION_HISTORY = [
    {"role": "user", "content": "¿Qué deducciones por alquiler hay en Cataluña?"},
    {"role": "assistant", "content": "En Cataluña puedes deducirte el 10% de las cantidades pagadas en alquiler de vivienda habitual, con un máximo de 300€."},
]


# === classify_followup tests ===

class TestClassifyFollowup:
    """Test follow-up type classification."""

    def test_no_history_is_new_topic(self):
        assert classify_followup("¿Cuánto IRPF pago?", []) == "new_topic"

    def test_single_message_is_new_topic(self):
        history = [{"role": "user", "content": "hola"}]
        assert classify_followup("¿Cuánto IRPF pago?", history) == "new_topic"

    # --- Clarifications ---

    def test_explicame_mejor(self):
        assert classify_followup("explícame mejor", IRPF_HISTORY) == "clarification"

    def test_no_entiendo(self):
        assert classify_followup("no entiendo", IRPF_HISTORY) == "clarification"

    def test_que_quiere_decir(self):
        assert classify_followup("¿qué quiere decir eso?", IRPF_HISTORY) == "clarification"

    def test_y_eso_question(self):
        assert classify_followup("¿y eso?", IRPF_HISTORY) == "clarification"

    def test_short_pronoun_reference(self):
        assert classify_followup("¿y esos tramos?", IRPF_HISTORY) == "clarification"

    def test_resume(self):
        assert classify_followup("resúmeme lo anterior", IRPF_HISTORY) == "clarification"

    def test_mas_detalle(self):
        assert classify_followup("más detalle por favor", IRPF_HISTORY) == "clarification"

    # --- Modifications ---

    def test_y_si_cobro_mas(self):
        assert classify_followup("y si cobro 80000€?", IRPF_HISTORY) == "modification"

    def test_y_esos_6000(self):
        assert classify_followup("y esos 6000€?", IRPF_HISTORY) == "modification"

    def test_y_si_vivo_en_otra_ccaa(self):
        result = classify_followup("y si vivo en Cataluña?", IRPF_HISTORY)
        assert result == "modification"

    def test_entonces_con_numero(self):
        assert classify_followup("entonces con 50000€ sería menos?", IRPF_HISTORY) == "modification"

    # --- New topics ---

    def test_completely_different_question(self):
        assert classify_followup(
            "¿Cuándo tengo que presentar el modelo 303 de IVA trimestral?",
            IRPF_HISTORY
        ) == "new_topic"

    def test_long_question_with_multiple_keywords(self):
        assert classify_followup(
            "¿Puedo deducirme el alquiler de vivienda habitual en la declaración de la renta si vivo en Andalucía y tengo hipoteca?",
            IRPF_HISTORY
        ) == "new_topic"


# === contextualize_query tests ===

class TestContextualizeQuery:
    """Test query expansion with conversation context."""

    def test_adds_ccaa_from_history(self):
        result = contextualize_query("y esos 6000€?", IRPF_HISTORY)
        assert "madrid" in result.lower() or "Madrid" in result

    def test_adds_fiscal_concept_from_history(self):
        result = contextualize_query("y esos 6000€?", IRPF_HISTORY)
        assert "irpf" in result.lower()

    def test_preserves_original_query(self):
        result = contextualize_query("y esos 6000€?", IRPF_HISTORY)
        assert "6000€" in result

    def test_no_duplicates_if_already_in_query(self):
        result = contextualize_query("IRPF en Madrid con 50000€", IRPF_HISTORY)
        # Should not duplicate "Madrid" or "IRPF"
        assert result.lower().count("madrid") == 1
        assert result.lower().count("irpf") == 1

    def test_empty_history_returns_original(self):
        result = contextualize_query("y esos 6000€?", [])
        assert result == "y esos 6000€?"

    def test_uses_last_rag_query(self):
        result = contextualize_query(
            "y el alquiler?",
            DEDUCTION_HISTORY,
            last_rag_query="deducciones alquiler Cataluña"
        )
        # Should pick up "cataluña" or "deducciones" from last_rag_query or history
        lower = result.lower()
        assert "cataluña" in lower or "cataluna" in lower

    def test_deduction_context_preserved(self):
        result = contextualize_query("¿y si son 400€ al mes?", DEDUCTION_HISTORY)
        lower = result.lower()
        assert "alquiler" in lower or "cataluña" in lower or "cataluna" in lower or "deducción" in lower or "deduccion" in lower
