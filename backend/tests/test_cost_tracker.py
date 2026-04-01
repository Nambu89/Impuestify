"""Tests for CostTracker service."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.cost_tracker import CostTracker


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(rows=[]))
    return db


@pytest.fixture
def tracker(mock_db):
    return CostTracker(mock_db)


@pytest.mark.asyncio
async def test_track_records_usage(tracker, mock_db):
    await tracker.track(
        user_id="user123",
        model="gpt-4o-mini",
        input_tokens=500,
        output_tokens=200,
        endpoint="/api/ask/stream",
    )
    mock_db.execute.assert_called_once()
    call_args = mock_db.execute.call_args
    assert "INSERT INTO usage_metrics" in call_args[0][0]


@pytest.mark.asyncio
async def test_calculate_cost_gpt4o_mini(tracker):
    cost = tracker.calculate_cost("gpt-4o-mini", 1000, 500)
    # input: 1000/1M * 0.15 = 0.00015, output: 500/1M * 0.60 = 0.0003
    assert abs(cost - 0.00045) < 0.0001


@pytest.mark.asyncio
async def test_calculate_cost_gpt4o(tracker):
    cost = tracker.calculate_cost("gpt-4o", 1000, 500)
    # input: 1000/1M * 2.50 = 0.0025, output: 500/1M * 10.00 = 0.005
    assert abs(cost - 0.0075) < 0.0001


@pytest.mark.asyncio
async def test_calculate_cost_unknown_model(tracker):
    cost = tracker.calculate_cost("unknown-model", 1000, 500)
    assert cost == 0.0  # unknown model, no cost


@pytest.mark.asyncio
async def test_calculate_cost_gpt5(tracker):
    cost = tracker.calculate_cost("gpt-5", 1000, 500)
    # input: 1000/1M * 5.00 = 0.005, output: 500/1M * 15.00 = 0.0075
    assert abs(cost - 0.0125) < 0.0001


@pytest.mark.asyncio
async def test_calculate_cost_embedding_model(tracker):
    cost = tracker.calculate_cost("text-embedding-3-large", 1000, 0)
    # input: 1000/1M * 0.13 = 0.00013, output: 0
    assert abs(cost - 0.00013) < 0.0001


@pytest.mark.asyncio
async def test_track_does_not_raise_on_db_error(mock_db):
    """CostTracker.track should never raise, even if DB fails."""
    mock_db.execute = AsyncMock(side_effect=Exception("DB connection lost"))
    tracker = CostTracker(mock_db)
    # Should not raise
    await tracker.track(
        user_id="user123",
        model="gpt-4o-mini",
        input_tokens=100,
        output_tokens=50,
        endpoint="/api/ask/stream",
    )


@pytest.mark.asyncio
async def test_period_start_week(tracker):
    result = tracker._period_start("week")
    assert isinstance(result, str)
    assert "T" in result  # ISO format


@pytest.mark.asyncio
async def test_period_start_month(tracker):
    result = tracker._period_start("month")
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_period_start_year(tracker):
    result = tracker._period_start("year")
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_period_start_default(tracker):
    result = tracker._period_start("invalid")
    assert isinstance(result, str)
