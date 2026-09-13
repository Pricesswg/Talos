"""The observed-source contract.

The declarative side says what Home Assistant believes. This side says what
the resolver actually saw. They are joined later, and never before both are
labelled.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Protocol, runtime_checkable


class ObservedError(RuntimeError):
    """An observed source could not produce its facts."""


class ObservedAuthError(ObservedError):
    """The credentials were rejected."""


@runtime_checkable
class HttpTransport(Protocol):
    """Anything that can exchange JSON with the appliance.

    `get_json` is the common case and every collector reads with it. Pi-hole
    also needs to trade a password for a session and hand it back, which is a
    POST and a DELETE with a header: `request_json` is the general form."""

    async def get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Return the decoded body. Raises `ObservedError` on failure."""

    async def request_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        """Any verb, optional body and headers. Same contract as `get_json`."""


class ObservedSource(ABC):
    """Produces observations, leases and the zero check."""

    @abstractmethod
    async def fetch(self, since: str | None = None) -> Any:
        """Collect since a cursor. Raises `ObservedError` on failure."""

    @abstractmethod
    async def probe(self) -> None:
        """Reach the appliance once, with the credentials given, and return
        nothing. Raises `ObservedAuthError` when the address answers but the
        credentials do not, `ObservedError` when nothing answers. This is
        what the setup form runs before saving."""
