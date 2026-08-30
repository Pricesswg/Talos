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
    """Anything that can GET a JSON document from the appliance."""

    async def get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Return the decoded body. Raises `ObservedError` on failure."""


class ObservedSource(ABC):
    """Produces observations, leases and the zero check."""

    @abstractmethod
    async def fetch(self, since: str | None = None) -> Any:
        """Collect since a cursor. Raises `ObservedError` on failure."""
