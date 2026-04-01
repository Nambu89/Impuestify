"""
Tests for SemanticWindow — intelligent message selection for LLM context.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.semantic_window import SemanticWindow, cosine_similarity
from datetime import datetime, timedelta


def _make_message(idx: int, content: str) -> dict:
    return {
        "id": f"msg_{idx}",
        "role": "user" if idx % 2 == 0 else "assistant",
        "content": content,
        "created_at": (datetime(2026, 1, 1) + timedelta(hours=idx)).isoformat(),
    }


# --- cosine_similarity unit tests ---

def test_cosine_similarity_identical_vectors():
    assert cosine_similarity([1, 0, 0], [1, 0, 0]) == pytest.approx(1.0)


def test_cosine_similarity_orthogonal_vectors():
    assert cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0)


def test_cosine_similarity_empty_vectors():
    assert cosine_similarity([], []) == 0.0


def test_cosine_similarity_different_lengths():
    assert cosine_similarity([1, 0], [1, 0, 0]) == 0.0


def test_cosine_similarity_zero_vector():
    assert cosine_similarity([0, 0], [1, 1]) == 0.0


# --- SemanticWindow tests ---

@pytest.mark.asyncio
async def test_short_conversation_returns_all():
    window = SemanticWindow(max_messages=15, recent_guaranteed=5)
    messages = [_make_message(i, f"Message {i}") for i in range(10)]

    with patch.object(window, '_get_messages', return_value=messages):
        result = await window.select("conv123", "query text")
        assert len(result) == 10  # all messages returned


@pytest.mark.asyncio
async def test_long_conversation_selects_semantically():
    window = SemanticWindow(max_messages=8, recent_guaranteed=3)
    messages = [_make_message(i, f"Message {i}") for i in range(20)]

    async def mock_embed(text):
        # Simple mock: return text length as a fake embedding
        return [len(text) / 100.0]

    async def mock_get_embedding(msg_id, content):
        return [len(content) / 100.0]

    with patch.object(window, '_get_messages', return_value=messages):
        with patch.object(window, '_embed', side_effect=mock_embed):
            with patch.object(window, '_get_or_create_embedding', side_effect=mock_get_embedding):
                result = await window.select("conv123", "Message 5")
                # Should return max_messages (8) total
                assert len(result) == 8
                # Last 3 should always be the recent ones
                assert result[-1]["id"] == "msg_19"
                assert result[-2]["id"] == "msg_18"
                assert result[-3]["id"] == "msg_17"


@pytest.mark.asyncio
async def test_result_is_chronologically_ordered():
    window = SemanticWindow(max_messages=6, recent_guaranteed=2)
    messages = [_make_message(i, f"Msg {i}") for i in range(10)]

    async def mock_embed(text):
        return [0.5]

    async def mock_get_embedding(msg_id, content):
        return [0.5]

    with patch.object(window, '_get_messages', return_value=messages):
        with patch.object(window, '_embed', side_effect=mock_embed):
            with patch.object(window, '_get_or_create_embedding', side_effect=mock_get_embedding):
                result = await window.select("conv123", "test query")
                # All selected messages should be in chronological order
                timestamps = [m["created_at"] for m in result]
                assert timestamps == sorted(timestamps)


@pytest.mark.asyncio
async def test_recent_messages_always_included():
    """Even if recent messages have low similarity, they are always included."""
    window = SemanticWindow(max_messages=5, recent_guaranteed=3)
    messages = [_make_message(i, f"Message {i}") for i in range(12)]

    async def mock_embed(text):
        # Query is about "taxes", recent messages about "weather" (low sim)
        if "taxes" in text:
            return [1.0, 0.0]
        return [0.0, 1.0]

    async def mock_get_embedding(msg_id, content):
        return [0.0, 1.0]  # All messages are "weather" themed

    with patch.object(window, '_get_messages', return_value=messages):
        with patch.object(window, '_embed', side_effect=mock_embed):
            with patch.object(window, '_get_or_create_embedding', side_effect=mock_get_embedding):
                result = await window.select("conv123", "taxes question")
                assert len(result) == 5
                # Last 3 must be the most recent messages
                recent_ids = {m["id"] for m in result[-3:]}
                assert recent_ids == {"msg_11", "msg_10", "msg_9"}


@pytest.mark.asyncio
async def test_embedding_cache_is_used():
    """Messages embeddings are cached and reused across calls."""
    window = SemanticWindow(max_messages=5, recent_guaranteed=2)
    messages = [_make_message(i, f"Message {i}") for i in range(8)]

    call_count = 0

    async def mock_embed(text):
        nonlocal call_count
        call_count += 1
        return [0.5]

    # Pre-populate cache for some messages
    window._embedding_cache["msg_0"] = [0.5]
    window._embedding_cache["msg_1"] = [0.5]

    with patch.object(window, '_get_messages', return_value=messages):
        with patch.object(window, '_embed', side_effect=mock_embed):
            result = await window.select("conv123", "test query")
            # _embed should be called for query + non-cached messages only
            # Cached: msg_0, msg_1. Not cached: msg_2..msg_5 (6 candidates minus 2 recent)
            # Plus 1 for the query embedding = total 5
            assert call_count == 5  # query + 4 uncached candidate messages
