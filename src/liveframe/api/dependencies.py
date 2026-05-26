"""FastAPI dependency injection."""

from __future__ import annotations

from functools import lru_cache

from liveframe.config import LiveframeSettings


@lru_cache
def get_settings() -> LiveframeSettings:
    """Return the global settings instance."""
    return LiveframeSettings()
