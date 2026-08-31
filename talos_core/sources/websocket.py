"""Declarative collection over the Home Assistant WebSocket API.

Used when Talos runs outside Home Assistant: a container on another machine, a
cron job, the CLI. Inside HA the registries are read directly and this file is
not involved. Same normalised output either way, which is the whole reason
`mapping.build_scan` is a pure function both paths call.

Command names on this API have moved before. Every call goes through an
ordered list of candidates and falls back rather than failing outright, and
whatever could not be read ends up in the scan's unverified list instead of
quietly reading as "nothing to report".
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Sequence

from ..model import Scan, UnverifiedCheck
from .base import AuthError, CommandError, CommandTransport, DeclarativeSource, SourceError
from .mapping import RegistryPayload, build_scan

# Ordered candidates per fact. First one the server accepts wins.
CONFIG_ENTRY_COMMANDS: tuple[str, ...] = ("config_entries/get", "config_entries/list")
DEVICE_COMMANDS: tuple[str, ...] = ("config/device_registry/list",)
ENTITY_COMMANDS: tuple[str, ...] = (
    "config/entity_registry/list",
    "config/entity_registry/list_for_display",
)
AREA_COMMANDS: tuple[str, ...] = ("config/area_registry/list",)
MANIFEST_COMMANDS: tuple[str, ...] = ("manifest/list",)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class WebSocketSource(DeclarativeSource):
    """Reads the declarative side through a connected transport."""

    def __init__(
        self,
        transport: CommandTransport,
        *,
        clock: Callable[[], str] = _utc_now,
    ) -> None:
        self._transport = transport
        self._clock = clock

    async def fetch(self) -> Scan:
        payload = await self.collect()
        return build_scan(
            payload,
            generated_at=self._clock(),
            collector="websocket",
            ha_version=self._transport.ha_version,
        )

    async def collect(self) -> RegistryPayload:
        """Read every registry, degrading with a note rather than failing."""
        notes: list[UnverifiedCheck] = []

        config_entries = await self._required(CONFIG_ENTRY_COMMANDS, "config entries")
        devices = await self._required(DEVICE_COMMANDS, "device registry")

        entities = await self._optional(
            ENTITY_COMMANDS,
            notes,
            check_id="unv.entity_registry_unreadable",
            title="Entity registry",
            detail=(
                "The server accepted no command for it. Without the entity"
                " registry the autonomy counts stay at zero, and zero must not be"
                " read as 'nothing at risk'."
            ),
        )
        areas = await self._optional(
            AREA_COMMANDS,
            notes,
            check_id="unv.area_registry_unreadable",
            title="Area registry",
            detail="Devices are left without an area. No other effect.",
        )
        manifests = await self._optional(
            MANIFEST_COMMANDS,
            notes,
            check_id="unv.manifest_list_unreadable",
            title="Manifest list",
            detail=(
                "Without manifests every integration stays 'unknown': there is no"
                " way to say which ones depend on the cloud."
            ),
        )

        return RegistryPayload(
            config_entries=_as_entries(config_entries),
            devices=_as_entries(devices),
            entities=_as_entries(entities),
            areas=_as_entries(areas),
            manifests=_as_entries(manifests),
            notes=notes,
        )

    async def _required(self, commands: Sequence[str], what: str) -> Any:
        result, error = await self._first_accepted(commands)
        if error is not None:
            raise SourceError(
                f"could not read the {what}: no supported command among"
                f" {', '.join(commands)} ({error})"
            )
        return result

    async def _optional(
        self,
        commands: Sequence[str],
        notes: list[UnverifiedCheck],
        *,
        check_id: str,
        title: str,
        detail: str,
    ) -> Any:
        result, error = await self._first_accepted(commands)
        if error is not None:
            notes.append(
                UnverifiedCheck(
                    id=check_id,
                    title=title,
                    reason="missing_data",
                    detail=f"{detail} (error: {error})",
                )
            )
            return []
        return result

    async def _first_accepted(self, commands: Sequence[str]) -> tuple[Any, str | None]:
        last: str | None = None
        for command in commands:
            try:
                return await self._transport.send({"type": command}), None
            except CommandError as err:
                last = str(err)
        return None, last or "no command attempted"


def _as_entries(result: Any) -> list[dict[str, Any]]:
    """Accept both a bare list and the `{"entries": [...]}` shape."""
    if isinstance(result, dict):
        for key in ("entries", "result", "items"):
            if isinstance(result.get(key), list):
                result = result[key]
                break
        else:
            return []
    if not isinstance(result, list):
        return []
    return [item for item in result if isinstance(item, dict)]


class AiohttpTransport:
    """A `CommandTransport` over aiohttp, with the Home Assistant handshake.

    aiohttp is imported inside `connect` on purpose: the core declares no
    runtime dependencies, and only the standalone CLI ever needs one.
    """

    def __init__(self, url: str, token: str) -> None:
        self._url = url
        self._token = token
        self._ha_version: str | None = None
        self._session: Any = None
        self._socket: Any = None
        self._next_id = 1

    @property
    def ha_version(self) -> str | None:
        return self._ha_version

    async def __aenter__(self) -> AiohttpTransport:
        await self.connect()
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.close()

    async def connect(self) -> None:
        try:
            import aiohttp
        except ImportError as err:  # pragma: no cover - depends on the install
            raise SourceError(
                "aiohttp is required for the standalone collector:"
                " install talos-core[cli]"
            ) from err

        self._session = aiohttp.ClientSession()
        try:
            self._socket = await self._session.ws_connect(self._url, heartbeat=30)
        except Exception as err:
            await self.close()
            raise SourceError(f"could not connect to {self._url}: {err}") from err

        greeting = await self._socket.receive_json()
        if greeting.get("type") != "auth_required":
            await self.close()
            raise SourceError(f"unexpected greeting from the server: {greeting.get('type')}")

        await self._socket.send_json({"type": "auth", "access_token": self._token})
        reply = await self._socket.receive_json()
        if reply.get("type") != "auth_ok":
            await self.close()
            raise AuthError(reply.get("message") or "the access token was rejected")
        self._ha_version = reply.get("ha_version")

    async def send(self, command: dict[str, Any]) -> Any:
        if self._socket is None:
            raise SourceError("transport is not connected")

        message_id = self._next_id
        self._next_id += 1
        await self._socket.send_json({**command, "id": message_id})

        # Events and other traffic can interleave; keep reading until the
        # result carrying our id comes back.
        while True:
            message = await self._socket.receive_json()
            if message.get("id") != message_id:
                continue
            if message.get("success"):
                return message.get("result")
            error = message.get("error") or {}
            raise CommandError(
                command.get("type", "?"),
                error.get("message") or "command refused",
                error.get("code"),
            )

    async def close(self) -> None:
        if self._socket is not None:
            await self._socket.close()
            self._socket = None
        if self._session is not None:
            await self._session.close()
            self._session = None
