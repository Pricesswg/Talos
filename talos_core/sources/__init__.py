"""Sources of declarative facts about a Home Assistant instance."""

from __future__ import annotations

from .base import (
    AuthError,
    CommandError,
    CommandTransport,
    DeclarativeSource,
    SourceError,
)
from .mapping import RegistryPayload, apply_mesh_roles, build_scan
from .websocket import AiohttpTransport, WebSocketSource

__all__ = [
    "AiohttpTransport",
    "apply_mesh_roles",
    "AuthError",
    "CommandError",
    "CommandTransport",
    "DeclarativeSource",
    "RegistryPayload",
    "SourceError",
    "WebSocketSource",
    "build_scan",
]
