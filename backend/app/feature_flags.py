"""
Development Feature Flags for Impuestify.

Simple JSON-based feature flags for local development.
Reads from .feature_flags.json in the project root.
In production (Railway), all flags default to True unless overridden by env vars.
"""
import json
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Default flags — all new features start as True (enabled)
DEFAULT_FLAGS = {
    "warmup_greeting": True,
    "semantic_window": True,
    "conversation_analyzer": True,
    "cost_tracker": True,
    "territory_plugins": True,
    "retribucion_especie": True,
}

_flags_cache = None


def _load_flags() -> dict:
    """Load flags from .feature_flags.json, falling back to defaults."""
    global _flags_cache
    if _flags_cache is not None:
        return _flags_cache

    # Check for local config file
    config_path = Path(__file__).parent.parent.parent.parent / ".feature_flags.json"
    if config_path.exists():
        try:
            with open(config_path) as f:
                local_flags = json.load(f)
            # Merge: local overrides defaults
            merged = {**DEFAULT_FLAGS, **local_flags}
            _flags_cache = merged
            logger.info(f"Loaded feature flags from {config_path}")
            return merged
        except Exception as e:
            logger.warning(f"Failed to load feature flags: {e}")

    # Check env var overrides (for Railway/production)
    flags = dict(DEFAULT_FLAGS)
    for key in flags:
        env_key = f"FF_{key.upper()}"
        env_val = os.environ.get(env_key)
        if env_val is not None:
            flags[key] = env_val.lower() in ("true", "1", "yes")

    _flags_cache = flags
    return flags


def is_enabled(flag_name: str) -> bool:
    """Check if a feature flag is enabled."""
    flags = _load_flags()
    return flags.get(flag_name, True)  # default: enabled


def reload_flags():
    """Force reload flags from disk (useful during development)."""
    global _flags_cache
    _flags_cache = None
    return _load_flags()


def list_flags() -> dict:
    """Return all current flag values."""
    return dict(_load_flags())
