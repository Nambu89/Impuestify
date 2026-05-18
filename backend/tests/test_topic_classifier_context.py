"""Tests for context-aware topic classifier (Bug A fix, sesion 38).

The classifier rejects ambiguous questions like "evalúa si esto es correcto"
when called bare. With a fiscal workspace attached or a fiscal turn just
above, it should accept them. Off-scope questions (cocina, código) must
still be rejected even with fiscal context — context cannot whitelist
unrelated topics.

These tests do NOT call Groq. They mock the classifier client and assert
the prompt is constructed correctly + the routing logic works.
"""

from unittest.mock import MagicMock

import pytest

from app.security.topic_classifier import (
    FiscalTopicClassifier,
    TopicCheckResult,
    TopicContext,
    _build_user_message,
    _context_hash,
    _has_fiscal_signal,
)


def _mock_groq_response(fiscal_es: bool, confidence: float = 0.95, reason: str = ""):
    """Build a Groq-shaped completion result."""
    payload = f'{{"fiscal_es": {str(fiscal_es).lower()}, "confidence": {confidence}, "reason": "{reason}"}}'
    msg = MagicMock()
    msg.content = payload
    choice = MagicMock()
    choice.message = msg
    completion = MagicMock()
    completion.choices = [choice]
    return completion


# ── Helpers ─────────────────────────────────────────────────────────────────


def test_context_hash_stable_for_equal_payloads():
    a = TopicContext(
        workspace_name="RENTA 2025",
        workspace_doc_count=6,
        workspace_file_types=["pdf", "xlsx"],
        recent_user_turns=["primera"],
    )
    b = TopicContext(
        workspace_name="renta 2025",  # different case
        workspace_doc_count=6,
        workspace_file_types=["xlsx", "pdf"],  # different order
        recent_user_turns=[" primera "],  # whitespace
    )
    assert _context_hash(a) == _context_hash(b)


def test_context_hash_differs_when_workspace_differs():
    a = TopicContext(workspace_name="RENTA 2025", workspace_doc_count=6)
    b = TopicContext(workspace_name="IVA Q1", workspace_doc_count=6)
    assert _context_hash(a) != _context_hash(b)


def test_context_hash_no_ctx_constant():
    assert _context_hash(None) == "no_ctx"


def test_has_fiscal_signal_only_when_meaningful():
    assert _has_fiscal_signal(None) is False
    assert _has_fiscal_signal(TopicContext()) is False
    assert _has_fiscal_signal(TopicContext(workspace_name="RENTA")) is False  # 0 docs
    assert _has_fiscal_signal(TopicContext(workspace_name="RENTA", workspace_doc_count=3)) is True
    assert _has_fiscal_signal(TopicContext(recent_user_turns=["¿IRPF?"])) is True


# ── User message composition ───────────────────────────────────────────────


def test_build_user_message_no_context_returns_question_only():
    msg = _build_user_message("¿es correcto?", None)
    assert msg == "¿es correcto?"


def test_build_user_message_no_signal_skips_context_block():
    """Empty TopicContext (no workspace, no turns) → no context block."""
    msg = _build_user_message("¿es correcto?", TopicContext())
    assert msg == "¿es correcto?"
    assert "Contexto previo" not in msg


def test_build_user_message_includes_workspace():
    ctx = TopicContext(
        workspace_name="Declaracion RENTA 2025",
        workspace_doc_count=6,
        workspace_file_types=["pdf", "xlsx"],
    )
    msg = _build_user_message("evalua si esto es correcto", ctx)
    assert "Contexto previo" in msg
    assert "Declaracion RENTA 2025" in msg
    assert "6 archivos" in msg
    assert "pdf" in msg
    assert "Pregunta actual: evalua si esto es correcto" in msg


def test_build_user_message_includes_recent_turns():
    ctx = TopicContext(recent_user_turns=["¿Cuánto IRPF pago?", "¿y si tributo conjunto?"])
    msg = _build_user_message("y eso cómo se calcula", ctx)
    assert "Cuánto IRPF" in msg
    assert "tributo conjunto" in msg
    assert "Pregunta actual: y eso cómo se calcula" in msg


def test_build_user_message_truncates_long_turns():
    long_turn = "x" * 500
    ctx = TopicContext(recent_user_turns=[long_turn])
    msg = _build_user_message("¿es correcto?", ctx)
    # The turn is capped to 200 chars in the prompt
    assert long_turn not in msg
    assert "x" * 200 in msg


# ── Classifier check() with context ─────────────────────────────────────────


def _classifier_with_mock(response_completion):
    """Build a classifier and inject a mocked Groq client."""
    classifier = FiscalTopicClassifier(sensitivity=0.7)
    classifier.client = MagicMock()
    classifier.client.chat.completions.create.return_value = response_completion
    return classifier


def test_check_no_context_passes_bare_question_to_groq():
    classifier = _classifier_with_mock(_mock_groq_response(True))
    classifier.check("¿Cuánto IRPF pago?")
    call_args = classifier.client.chat.completions.create.call_args
    user_msg = call_args.kwargs["messages"][1]["content"]
    assert user_msg == "¿Cuánto IRPF pago?"
    assert "Contexto previo" not in user_msg


def test_check_with_workspace_context_includes_block_in_groq_prompt():
    classifier = _classifier_with_mock(_mock_groq_response(True))
    ctx = TopicContext(
        workspace_name="Declaracion RENTA 2025",
        workspace_doc_count=6,
        workspace_file_types=["pdf"],
    )
    classifier.check("evalua si esto es correcto", context=ctx)
    user_msg = classifier.client.chat.completions.create.call_args.kwargs["messages"][1]["content"]
    assert "Contexto previo" in user_msg
    assert "Declaracion RENTA 2025" in user_msg


def test_check_returns_groq_verdict():
    classifier = _classifier_with_mock(
        _mock_groq_response(True, confidence=0.9, reason="es fiscal")
    )
    ctx = TopicContext(workspace_name="RENTA 2025", workspace_doc_count=6)
    result = classifier.check("evalua mi declaracion", context=ctx)
    assert result.is_fiscal is True
    assert result.confidence == 0.9


def test_check_blocks_when_groq_says_offscope_even_with_context():
    """Off-scope with workspace must STILL be blocked."""
    classifier = _classifier_with_mock(
        _mock_groq_response(False, confidence=0.95, reason="receta de cocina")
    )
    ctx = TopicContext(workspace_name="RENTA 2025", workspace_doc_count=6)
    result = classifier.check("dame una receta de paella", context=ctx)
    assert result.is_fiscal is False


def test_check_low_confidence_yes_still_rejects():
    """Sensitivity threshold (0.7) is enforced even with context."""
    classifier = _classifier_with_mock(_mock_groq_response(True, confidence=0.5, reason="dudoso"))
    ctx = TopicContext(workspace_name="RENTA 2025", workspace_doc_count=6)
    result = classifier.check("revisa esto", context=ctx)
    assert result.is_fiscal is False
    assert "Baja confianza" in result.reason


# ── Public check_fiscal_topic + cache behavior ──────────────────────────────


def test_check_fiscal_topic_cache_separates_contexts(monkeypatch):
    """Same question with different contexts must NOT share cache entries."""
    from app.security import topic_classifier as tc

    call_count = {"n": 0}

    def fake_check(self, question, context=None):
        call_count["n"] += 1
        # Different verdicts for different contexts to make the test meaningful
        if context and context.workspace_name:
            return TopicCheckResult(is_fiscal=True, confidence=0.9, reason="ctx", classifier="groq")
        return TopicCheckResult(is_fiscal=False, confidence=0.9, reason="no ctx", classifier="groq")

    # Clear cache between tests to avoid interference
    tc._cached_check.cache_clear()
    monkeypatch.setattr(tc.FiscalTopicClassifier, "check", fake_check)

    r1 = tc.check_fiscal_topic("evalua mi declaracion", context=None)
    assert r1.is_fiscal is False

    ctx = TopicContext(workspace_name="RENTA 2025", workspace_doc_count=6)
    r2 = tc.check_fiscal_topic("evalua mi declaracion", context=ctx)
    assert r2.is_fiscal is True

    # Two distinct cache entries → 2 underlying calls
    assert call_count["n"] == 2

    # Repeating each lookup hits cache (no new calls)
    tc.check_fiscal_topic("evalua mi declaracion", context=None)
    tc.check_fiscal_topic("evalua mi declaracion", context=ctx)
    assert call_count["n"] == 2

    tc._cached_check.cache_clear()
