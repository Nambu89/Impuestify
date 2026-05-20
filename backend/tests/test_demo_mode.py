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
