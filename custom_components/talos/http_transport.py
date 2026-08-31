"""HTTP transport for AdGuard Home, on Home Assistant's shared session."""

from __future__ import annotations

from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .core import ObservedAuthError, ObservedError


class HassHttpTransport:
    """`HttpTransport` backed by the session Home Assistant already manages.

    Credentials are sent per request rather than bound to the session: the
    session is shared with every other integration in the instance.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        base_url: str,
        username: str = "",
        password: str = "",
        verify_ssl: bool = True,
        timeout: float = 60,
    ) -> None:
        self._hass = hass
        self._base_url = base_url.rstrip("/")
        self._auth = (
            aiohttp.BasicAuth(username, password) if username or password else None
        )
        self._verify_ssl = verify_ssl
        self._timeout = timeout

    async def get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        session = async_get_clientsession(self._hass, verify_ssl=self._verify_ssl)
        try:
            async with session.get(
                f"{self._base_url}{path}",
                params=params,
                auth=self._auth,
                timeout=aiohttp.ClientTimeout(total=self._timeout),
            ) as response:
                if response.status in (401, 403):
                    raise ObservedAuthError(f"{path}: HTTP {response.status}")
                if response.status >= 400:
                    raise ObservedError(f"{path}: HTTP {response.status}")
                return await response.json(content_type=None)
        except ObservedError:
            raise
        except aiohttp.ClientError as err:
            raise ObservedError(f"{path}: {err}") from err
        except TimeoutError as err:
            raise ObservedError(f"{path}: timeout") from err
