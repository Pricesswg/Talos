"""Sources of declarative facts about a Home Assistant instance."""

from __future__ import annotations

from .base import (
    AuthError,
    CommandError,
    CommandTransport,
    DeclarativeSource,
    SourceError,
)
from .mapping import RegistryPayload, build_scan
from .websocket import AiohttpTransport, WebSocketSource

__all__ = [
    "AiohttpTransport",
    "AuthError",
    "CommandError",
    "CommandTransport",
    "DeclarativeSource",
    "RegistryPayload",
    "SourceError",
    "WebSocketSource",
    "build_scan",
]
