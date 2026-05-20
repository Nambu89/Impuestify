"""Tests for demo mode configuration and behavior."""

import os
from unittest.mock import patch

import pytest


def test_demo_settings_defaults_off():
    """Default settings: demo mode OFF, brand=Impuestify, subscriptions ON."""
    from app.config import Settings

    s = Settings(_env_file=None)
    assert s.DEMO_MODE is False
    assert s.BRAND_NAME == "Impuestify"
    assert s.BRAND_DOMAIN == "impuestify.com"
    assert s.SUBSCRIPTIONS_ENABLED is True
    assert s.RAG_TERRITORY_LOCK is None
    assert s.DEMO_USER_EMAIL is None
    assert s.DEMO_USER_PASSWORD is None


def test_demo_settings_can_enable_via_env(monkeypatch):
    """When DEMO_MODE=true env var set, settings reflect demo config."""
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("BRAND_NAME", "Fiscal IA Melilla")
    monkeypatch.setenv("BRAND_DOMAIN", "fiscal-melilla.demo")
    monkeypatch.setenv("SUBSCRIPTIONS_ENABLED", "false")
    monkeypatch.setenv("RAG_TERRITORY_LOCK", "Melilla")
    monkeypatch.setenv("DEMO_USER_EMAIL", "demo@fiscal-melilla.demo")
    monkeypatch.setenv("DEMO_USER_PASSWORD", "Demo2026!")

    from app.config import Settings

    s = Settings(_env_file=None)
    assert s.DEMO_MODE is True
    assert s.BRAND_NAME == "Fiscal IA Melilla"
    assert s.BRAND_DOMAIN == "fiscal-melilla.demo"
    assert s.SUBSCRIPTIONS_ENABLED is False
    assert s.RAG_TERRITORY_LOCK == "Melilla"
    assert s.DEMO_USER_EMAIL == "demo@fiscal-melilla.demo"
    assert s.DEMO_USER_PASSWORD == "Demo2026!"


def test_resolve_territory_filter_uses_lock_when_set(monkeypatch):
    """RAG_TERRITORY_LOCK overrides user-provided territory."""
    from app.utils.demo_filters import resolve_territory_filter

    # No lock -> use user territory
    assert resolve_territory_filter("Madrid", lock=None) == "Madrid"

    # Lock set -> override user
    assert resolve_territory_filter("Madrid", lock="Melilla") == "Melilla"

    # Lock set, user None -> lock wins
    assert resolve_territory_filter(None, lock="Melilla") == "Melilla"

    # No lock, no user -> None (let retriever search all)
    assert resolve_territory_filter(None, lock=None) is None


def test_chat_route_uses_lock_in_demo_mode(monkeypatch):
    """When DEMO_MODE+lock set, helper resolves user CCAA to the lock."""
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("RAG_TERRITORY_LOCK", "Melilla")

    from app.config import Settings
    from app.utils.demo_filters import resolve_territory_filter

    # Build a fresh Settings to pick up monkeypatched env
    s = Settings(_env_file=None)
    assert resolve_territory_filter("Madrid", s.RAG_TERRITORY_LOCK) == "Melilla"


def test_subscription_endpoint_returns_404_when_disabled(monkeypatch):
    """When SUBSCRIPTIONS_ENABLED=false, /subscription routes are not registered.

    Uses a fresh FastAPI() to avoid corrupting global app state with importlib.reload.
    """
    monkeypatch.setenv("SUBSCRIPTIONS_ENABLED", "false")

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.config import Settings
    from app.routers.subscription import router as subscription_router

    s = Settings(_env_file=None)
    test_app = FastAPI()
    if s.SUBSCRIPTIONS_ENABLED:
        test_app.include_router(subscription_router)

    client = TestClient(test_app)
    r = client.get("/subscription/status")
    assert r.status_code == 404
    assert "stripe" not in r.text.lower()


@pytest.mark.asyncio
async def test_seed_demo_user_idempotent(monkeypatch):
    """seed_demo_user creates user if absent, no-op if present, hashes password."""
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("DEMO_USER_EMAIL", "demo@test.local")
    monkeypatch.setenv("DEMO_USER_PASSWORD", "Demo2026!")
    monkeypatch.setenv("RAG_TERRITORY_LOCK", "Melilla")

    # Reload settings module to pick up the new env vars
    import importlib
    from unittest.mock import AsyncMock, MagicMock

    import app.config as config_module

    importlib.reload(config_module)
    import app.services.demo_seed_service as seed_module

    importlib.reload(seed_module)

    db = MagicMock()
    db.execute = AsyncMock(return_value=MagicMock(rows=[]))  # No existing user

    await seed_module.seed_demo_user(db)

    # Should have called INSERT
    insert_calls = [c for c in db.execute.call_args_list if "INSERT" in str(c).upper()]
    assert len(insert_calls) >= 1
    args_str = str(insert_calls[0])
    # Password is hashed (not plaintext)
    assert "Demo2026!" not in args_str

    # Second call: user exists -> no INSERT
    db.execute.reset_mock()
    db.execute = AsyncMock(return_value=MagicMock(rows=[{"id": "abc"}]))
    await seed_module.seed_demo_user(db)
    insert_calls = [c for c in db.execute.call_args_list if "INSERT" in str(c).upper()]
    assert len(insert_calls) == 0


@pytest.mark.asyncio
async def test_seed_demo_user_noop_when_demo_mode_off(monkeypatch):
    """No-op when DEMO_MODE=false."""
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.delenv("DEMO_USER_EMAIL", raising=False)
    monkeypatch.delenv("DEMO_USER_PASSWORD", raising=False)

    import importlib
    from unittest.mock import AsyncMock, MagicMock

    import app.config as config_module

    importlib.reload(config_module)
    import app.services.demo_seed_service as seed_module

    importlib.reload(seed_module)

    db = MagicMock()
    db.execute = AsyncMock()
    await seed_module.seed_demo_user(db)
    db.execute.assert_not_called()
