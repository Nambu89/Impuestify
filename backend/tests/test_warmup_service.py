"""Tests for WarmupService — personalized greetings and RAG pre-loading."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.warmup_service import WarmupService


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def warmup(mock_db):
    return WarmupService(mock_db)


@pytest.mark.asyncio
async def test_warmup_returns_greeting_for_user_with_profile(warmup):
    """Warmup with a profile returns personalized greeting and preloaded RAG."""
    profile = {
        "ccaa_residencia": "Madrid",
        "situacion_laboral": "autonomo",
    }
    with patch.object(warmup, '_get_profile', return_value=profile):
        with patch.object(warmup, '_preload_rag', return_value=True):
            with patch.object(warmup, '_generate_greeting', return_value="Hola, bienvenido"):
                result = await warmup.warmup("user123")
                assert result["greeting"] == "Hola, bienvenido"
                assert result["rag_preloaded"] is True


@pytest.mark.asyncio
async def test_warmup_static_greeting_for_new_user(warmup):
    """Warmup without profile returns static greeting, no RAG preload."""
    with patch.object(warmup, '_get_profile', return_value=None):
        result = await warmup.warmup("user_new")
        assert "Impuestify" in result["greeting"]
        assert result["rag_preloaded"] is False


@pytest.mark.asyncio
async def test_warmup_handles_llm_failure_gracefully(warmup):
    """If LLM greeting fails, falls back to static greeting."""
    profile = {
        "ccaa_residencia": "Cataluna",
        "situacion_laboral": "particular",
    }
    with patch.object(warmup, '_get_profile', return_value=profile):
        with patch.object(warmup, '_preload_rag', return_value=True):
            with patch.object(warmup, '_generate_greeting', return_value="Hola, bienvenido a Impuestify. Soy tu asistente fiscal. Puedes preguntarme sobre IRPF, deducciones, modelos fiscales o cualquier duda tributaria."):
                result = await warmup.warmup("user456")
                assert result["greeting"] is not None
                assert len(result["greeting"]) > 0


@pytest.mark.asyncio
async def test_warmup_generate_greeting_llm_exception_fallback(warmup):
    """_generate_greeting returns static greeting when OpenAI call raises."""
    profile = {
        "ccaa_residencia": "Madrid",
        "situacion_laboral": "autonomo",
    }

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API error"))
    warmup._client = mock_client

    greeting = await warmup._generate_greeting(profile)
    assert "Impuestify" in greeting


@pytest.mark.asyncio
async def test_warmup_get_profile_no_rows(warmup, mock_db):
    """_get_profile returns None when no user_profiles row."""
    mock_result = MagicMock()
    mock_result.rows = []
    mock_db.execute = AsyncMock(return_value=mock_result)

    profile = await warmup._get_profile("nonexistent")
    assert profile is None


@pytest.mark.asyncio
async def test_warmup_get_profile_no_ccaa(warmup, mock_db):
    """_get_profile returns None when ccaa_residencia is empty."""
    mock_result = MagicMock()
    mock_result.rows = [{"ccaa_residencia": "", "situacion_laboral": "particular", "datos_fiscales": None}]
    mock_db.execute = AsyncMock(return_value=mock_result)

    profile = await warmup._get_profile("user_no_ccaa")
    assert profile is None


@pytest.mark.asyncio
async def test_warmup_preload_rag_handles_missing_territory(warmup):
    """_preload_rag returns False when territory plugin is not found."""
    with patch('app.services.warmup_service.get_territory', side_effect=KeyError("No plugin")):
        result = await warmup._preload_rag("UnknownTerritory", "particular")
        assert result is False
