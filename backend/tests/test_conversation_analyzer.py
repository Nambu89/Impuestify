"""
Tests for ConversationAnalyzer — LLM post-conversation fiscal fact extraction.
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.conversation_analyzer import ConversationAnalyzer


@pytest.fixture
def mock_db():
    db = AsyncMock()
    return db


@pytest.fixture
def analyzer(mock_db):
    return ConversationAnalyzer(mock_db)


@pytest.mark.asyncio
async def test_skip_short_conversations(analyzer):
    """Conversations with < 3 messages should not be analyzed."""
    with patch.object(analyzer, '_get_messages', return_value=[
        {"role": "user", "content": "Hola"},
        {"role": "assistant", "content": "Hola!"},
    ]):
        result = await analyzer.analyze("conv123", "user456")
        assert result == {}


@pytest.mark.asyncio
async def test_skip_single_message(analyzer):
    """A single message should not be analyzed."""
    with patch.object(analyzer, '_get_messages', return_value=[
        {"role": "user", "content": "Hola"},
    ]):
        result = await analyzer.analyze("conv123", "user456")
        assert result == {}


@pytest.mark.asyncio
async def test_skip_empty_conversation(analyzer):
    """An empty conversation should not be analyzed."""
    with patch.object(analyzer, '_get_messages', return_value=[]):
        result = await analyzer.analyze("conv123", "user456")
        assert result == {}


@pytest.mark.asyncio
async def test_analyze_extracts_facts(analyzer):
    """Should extract structured fiscal facts from conversation."""
    messages = [
        {"role": "user", "content": "Soy autonomo en Madrid"},
        {"role": "assistant", "content": "Entendido, eres autonomo en Madrid."},
        {"role": "user", "content": "Tengo 2 hijos y pago hipoteca de 900 euros"},
        {"role": "assistant", "content": "Perfecto, tomo nota."},
    ]
    mock_llm_response = json.dumps({
        "ccaa": "Madrid",
        "situacion_laboral": "autonomo",
        "hijos": 2,
        "hipoteca_activa": True,
        "importe_hipoteca": 900,
    })

    with patch.object(analyzer, '_get_messages', return_value=messages):
        with patch.object(analyzer, '_call_llm', return_value=mock_llm_response):
            with patch.object(analyzer, '_merge_facts', new_callable=AsyncMock):
                result = await analyzer.analyze("conv123", "user456")
                assert result["ccaa"] == "Madrid"
                assert result["hijos"] == 2
                assert result["hipoteca_activa"] is True
                assert result["importe_hipoteca"] == 900
                assert result["situacion_laboral"] == "autonomo"


@pytest.mark.asyncio
async def test_analyze_calls_merge(analyzer):
    """Should call _merge_facts with extracted data."""
    messages = [
        {"role": "user", "content": "Vivo en Barcelona"},
        {"role": "assistant", "content": "Ok"},
        {"role": "user", "content": "Soy asalariado"},
    ]
    extracted = {"ccaa": "Cataluna", "situacion_laboral": "asalariado"}

    with patch.object(analyzer, '_get_messages', return_value=messages):
        with patch.object(analyzer, '_call_llm', return_value=json.dumps(extracted)):
            with patch.object(analyzer, '_merge_facts', new_callable=AsyncMock) as mock_merge:
                await analyzer.analyze("conv123", "user456")
                mock_merge.assert_called_once_with("user456", extracted)


@pytest.mark.asyncio
async def test_analyze_handles_invalid_json(analyzer):
    """Should gracefully handle invalid JSON from LLM."""
    messages = [
        {"role": "user", "content": "Hola"},
        {"role": "assistant", "content": "Hola"},
        {"role": "user", "content": "Pregunta"},
    ]

    with patch.object(analyzer, '_get_messages', return_value=messages):
        with patch.object(analyzer, '_call_llm', return_value="not valid json {{{"):
            result = await analyzer.analyze("conv123", "user456")
            assert result == {}


@pytest.mark.asyncio
async def test_analyze_handles_non_dict_json(analyzer):
    """Should reject non-dict JSON (e.g. a list)."""
    messages = [
        {"role": "user", "content": "Hola"},
        {"role": "assistant", "content": "Hola"},
        {"role": "user", "content": "Pregunta"},
    ]

    with patch.object(analyzer, '_get_messages', return_value=messages):
        with patch.object(analyzer, '_call_llm', return_value='["not", "a", "dict"]'):
            result = await analyzer.analyze("conv123", "user456")
            assert result == {}


@pytest.mark.asyncio
async def test_analyze_handles_llm_exception(analyzer):
    """Should gracefully handle LLM call failure."""
    messages = [
        {"role": "user", "content": "Hola"},
        {"role": "assistant", "content": "Hola"},
        {"role": "user", "content": "Pregunta"},
    ]

    with patch.object(analyzer, '_get_messages', return_value=messages):
        with patch.object(analyzer, '_call_llm', side_effect=Exception("API error")):
            result = await analyzer.analyze("conv123", "user456")
            assert result == {}


@pytest.mark.asyncio
async def test_merge_respects_manual_priority(mock_db):
    """Manual source data should never be overwritten by LLM."""
    # Setup: existing profile with manual ccaa
    existing_datos = {
        "ccaa": {"value": "Cataluna", "_source": "manual"},
        "hijos": {"value": 1, "_source": "regex"},
    }
    mock_result = MagicMock()
    mock_result.rows = [{"datos_fiscales": json.dumps(existing_datos)}]
    mock_db.execute = AsyncMock(return_value=mock_result)

    analyzer = ConversationAnalyzer(mock_db)

    extracted = {"ccaa": "Madrid", "hijos": 3, "cripto_activo": True}
    await analyzer._merge_facts("user456", extracted)

    # Check the UPDATE call
    calls = mock_db.execute.call_args_list
    update_call = calls[-1]  # last call should be UPDATE
    saved_json = json.loads(update_call[0][1][0])

    # ccaa should NOT be overwritten (manual > llm)
    assert saved_json["ccaa"]["value"] == "Cataluna"
    assert saved_json["ccaa"]["_source"] == "manual"
    # hijos should be overwritten (regex < llm)
    assert saved_json["hijos"]["value"] == 3
    assert saved_json["hijos"]["_source"] == "llm"
    # cripto_activo should be added
    assert saved_json["cripto_activo"]["value"] is True
    assert saved_json["cripto_activo"]["_source"] == "llm"


@pytest.mark.asyncio
async def test_merge_creates_profile_if_missing(mock_db):
    """Should create a new profile if none exists."""
    mock_result = MagicMock()
    mock_result.rows = []
    mock_db.execute = AsyncMock(return_value=mock_result)

    analyzer = ConversationAnalyzer(mock_db)
    await analyzer._merge_facts("user789", {"ccaa": "Madrid"})

    # Should have called INSERT
    calls = mock_db.execute.call_args_list
    insert_call = calls[-1]
    assert "INSERT" in insert_call[0][0]


@pytest.mark.asyncio
async def test_analyze_strips_markdown_fences(analyzer):
    """Should handle LLM response wrapped in ```json ... ```."""
    messages = [
        {"role": "user", "content": "Soy de Valencia"},
        {"role": "assistant", "content": "Ok"},
        {"role": "user", "content": "Tengo 1 hijo"},
    ]
    fenced_response = '```json\n{"ccaa": "Valencia", "hijos": 1}\n```'

    with patch.object(analyzer, '_get_messages', return_value=messages):
        with patch.object(analyzer, '_call_llm', return_value=fenced_response):
            with patch.object(analyzer, '_merge_facts', new_callable=AsyncMock):
                result = await analyzer.analyze("conv123", "user456")
                assert result["ccaa"] == "Valencia"
                assert result["hijos"] == 1
