"""Helpers to enforce demo-mode constraints across routers."""

from __future__ import annotations


def resolve_territory_filter(
    user_territory: str | None,
    lock: str | None,
) -> str | None:
    """Return the territory to use for RAG queries.

    When `lock` is set (settings.RAG_TERRITORY_LOCK), it overrides any
    user-provided territory. This is how demo deploys force Melilla-only
    corpus while keeping the multi-CCAA codepath intact for non-demo runs.
    """
    if lock:
        return lock
    return user_territory
