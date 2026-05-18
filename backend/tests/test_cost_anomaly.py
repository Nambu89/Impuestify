"""Tests for cost anomaly detector (Sprint 2 P1 #4)."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.cost_anomaly_detector import (
    CostAnomalyDetector,
    DEFAULT_MULTIPLIER,
    LOWER_FLOOR_USD,
)


def _row(**fields):
    """Make a dict-like row that supports ['key'] and .keys()."""

    class R(dict):
        pass

    r = R(fields)
    return r


def _result(rows):
    res = MagicMock()
    res.rows = rows
    return res


@pytest.mark.asyncio
async def test_no_usage_no_hits():
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _result([]),  # today
            _result([]),  # baseline
        ]
    )
    det = CostAnomalyDetector(db=db)
    hits = await det.find_anomalies()
    assert hits == []


@pytest.mark.asyncio
async def test_user_below_threshold_no_hit():
    # baseline 0.10/day -> threshold = max(0.50, 10*0.10) = 0.50
    # today 0.20 -> below -> no hit
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _result([_row(user_id="u1", today_cost=0.20, today_requests=5)]),
            _result([_row(user_id="u1", baseline_avg=0.10)]),
            _result([_row(id="u1", email="u1@example.com", plan_type="particular")]),
        ]
    )
    det = CostAnomalyDetector(db=db)
    hits = await det.find_anomalies()
    assert hits == []


@pytest.mark.asyncio
async def test_user_over_10x_baseline_triggers():
    # baseline 0.30/day, today 5.00 -> ratio 16.6x -> hit
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _result([_row(user_id="u1", today_cost=5.00, today_requests=120)]),
            _result([_row(user_id="u1", baseline_avg=0.30)]),
            _result([_row(id="u1", email="u1@example.com", plan_type="creator")]),
        ]
    )
    det = CostAnomalyDetector(db=db)
    hits = await det.find_anomalies()
    assert len(hits) == 1
    h = hits[0]
    assert h.user_id == "u1"
    assert h.email == "u1@example.com"
    assert h.plan == "creator"
    assert h.today_cost_usd == 5.00
    assert h.baseline_avg_usd == 0.30
    assert h.multiplier > 10
    assert h.today_requests == 120


@pytest.mark.asyncio
async def test_user_with_no_baseline_only_alerts_above_floor():
    # New user, no baseline. Today $0.40 -> below floor*5 = $2.50 -> NO hit
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _result([_row(user_id="new1", today_cost=0.40, today_requests=3)]),
            _result([]),  # no baseline for this user
            _result([_row(id="new1", email="new@example.com", plan_type=None)]),
        ]
    )
    det = CostAnomalyDetector(db=db)
    hits = await det.find_anomalies()
    assert hits == []


@pytest.mark.asyncio
async def test_user_with_no_baseline_alerts_when_huge():
    # New user spent $5 today (above floor*5 = $2.50) -> hit
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _result([_row(user_id="new2", today_cost=5.00, today_requests=200)]),
            _result([]),
            _result([_row(id="new2", email="new2@example.com", plan_type="particular")]),
        ]
    )
    det = CostAnomalyDetector(db=db)
    hits = await det.find_anomalies()
    assert len(hits) == 1
    assert hits[0].multiplier == -1  # infinite ratio sentinel


@pytest.mark.asyncio
async def test_floor_protects_tiny_baselines():
    # baseline $0.001/day, today $0.05 -> ratio 50x but cost below floor -> no hit
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _result([_row(user_id="u1", today_cost=0.05, today_requests=2)]),
            _result([_row(user_id="u1", baseline_avg=0.001)]),
            _result([_row(id="u1", email="u1@example.com", plan_type="particular")]),
        ]
    )
    det = CostAnomalyDetector(db=db)
    hits = await det.find_anomalies()
    assert hits == [], "Floor must protect against noisy tiny baselines"
