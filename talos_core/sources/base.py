"""The declarative-source contract.

Talos reads the same declarative facts in two very different situations: from
outside, over the Home Assistant WebSocket API with a long lived token, and
from inside, through the registry helpers when it runs as an integration. Both
must produce an identical, normalised `Scan`, or the standalone CLI and the
panel would slowly start disagreeing about the same house.

The transport is kept behind a protocol on purpose. Everything that decides
*what a payload means* lives in `mapping.py` and is a pure function, testable
against recorded payloads with no network and no running Home Assistant.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Protocol, runtime_checkable

from ..model import Scan


class SourceError(RuntimeError):
    """A source could not produce a scan."""


class AuthError(SourceError):
    """The credentials were rejected."""


class CommandError(SourceError):
    """The server accepted the connection but refused a command."""

    def __init__(self, command: str, message: str, code: str | None = None) -> None:
        self.command = command
        self.code = code
        super().__init__(f"{command}: {message}" + (f" [{code}]" if code else ""))


@runtime_checkable
class CommandTransport(Protocol):
    """Anything that can carry one Home Assistant command and bring back a result."""

    @property
    def ha_version(self) -> str | None:
        """Reported by the server during the handshake, when it says."""

    async def send(self, command: dict[str, Any]) -> Any:
        """Send one command and return its `result`.

        Raises `CommandError` when the server answers with `success: false`.
        """


class DeclarativeSource(ABC):
    """Produces a scan carrying `evidence: declared` only.

    Observations are somebody else's job: this side reports what Home
    Assistant says about itself, and nothing more.
    """

    @abstractmethod
    async def fetch(self) -> Scan:
        """Collect and normalise. Raises `SourceError` on failure."""
