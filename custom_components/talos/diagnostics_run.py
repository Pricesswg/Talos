"""The Home Assistant side of a diagnostic run.

Everything here is started by the user and ends on its own. The event bus is
listened to for the window and then released; the log is read once, from
the tail; each declared endpoint gets one connection attempt with a timeout.
Nothing is scheduled, nothing is left running, nothing is retried.

Kept apart from the coordinator on purpose. A run is not a scan: it is a
measurement taken at a moment, it contributes to no check, and the last one is
held in memory until the next, never persisted.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .core import (
    DiagnosticRun,
    Reach,
    Scan,
    attribute_churn,
    clamp_window,
    declared_targets,
    parse_blocking_calls,
)

_LOGGER = logging.getLogger(__name__)

# How much of the log to read, from the end. Rotation keeps the file bounded
# anyway; this keeps the read bounded on an install that turned rotation off.
LOG_TAIL_BYTES = 4 * 1024 * 1024

# Per connection. A broker on the LAN answers in milliseconds; a host that
# takes longer than this is unreachable for any purpose that matters here.
CONNECT_TIMEOUT = 3.0

# Connections in flight at once. Enough to finish quickly, few enough that
# the run never looks like a burst to whatever is watching the network.
CONNECT_PARALLELISM = 4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


async def _wait(seconds: float) -> None:
    """The listening window. One seam, so a test can make it instant."""
    await asyncio.sleep(seconds)


async def run_diagnostics(hass: Any, scan: Scan, window: Any = None) -> DiagnosticRun:
    """One complete run. Every section that could not be measured says so."""
    seconds = clamp_window(window)
    run = DiagnosticRun(started_at=_now(), window_seconds=seconds)

    # The three measures are independent, so the two that do not need the
    # window run while the bus is being listened to.
    churn_task = asyncio.ensure_future(_measure_churn(hass, seconds))
    blocking_task = asyncio.ensure_future(_read_blocking_calls(hass))
    reach_task = asyncio.ensure_future(_measure_reachability(scan))

    changes, entry_of, churn_note = await churn_task
    rows, total, unattributed = attribute_churn(changes, entry_of, seconds)
    run.churn = rows
    run.total_changes = total
    run.unattributed_changes = unattributed
    if churn_note:
        run.notes.append(churn_note)

    blocking, blocking_note = await blocking_task
    run.blocking = blocking
    if blocking_note:
        run.notes.append(blocking_note)

    reachability, reach_note = await reach_task
    run.reachability = reachability
    if reach_note:
        run.notes.append(reach_note)

    run.finished_at = _now()
    return run


async def _measure_churn(
    hass: Any, seconds: int
) -> tuple[list[str], dict[str, str | None], str | None]:
    """Every entity that changed state during the window, in order.

    The entity registry is read once, after the window, so the attribution
    reflects the registry as it stands rather than as it stood at each event.
    """
    changed: list[str] = []

    def _on_change(event: Any) -> None:
        entity_id = (getattr(event, "data", None) or {}).get("entity_id")
        if entity_id:
            changed.append(str(entity_id))

    try:
        unsubscribe = hass.bus.async_listen("state_changed", _on_change)
    except Exception as err:  # noqa: BLE001
        return [], {}, f"the event bus could not be listened to: {err}"
    try:
        await _wait(seconds)
    finally:
        try:
            unsubscribe()
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Talos: releasing the state listener failed", exc_info=True)

    entry_of: dict[str, str | None] = {}
    try:
        from homeassistant.helpers import entity_registry

        registry = entity_registry.async_get(hass)
        for entity_id in set(changed):
            entry = registry.async_get(entity_id)
            entry_of[entity_id] = getattr(entry, "config_entry_id", None) if entry else None
    except Exception as err:  # noqa: BLE001
        return changed, {}, f"the entity registry could not be read, so nothing is attributed: {err}"
    return changed, entry_of, None


async def _read_blocking_calls(hass: Any) -> tuple[list[Any], str | None]:
    """The tail of the log, parsed for calls that blocked the loop."""
    path = Path(hass.config.path("home-assistant.log"))

    def _read() -> str:
        if not path.exists():
            return ""
        with path.open("rb") as handle:
            handle.seek(0, 2)
            size = handle.tell()
            handle.seek(max(0, size - LOG_TAIL_BYTES))
            return handle.read().decode("utf-8", "replace")

    try:
        text = await hass.async_add_executor_job(_read)
    except Exception as err:  # noqa: BLE001
        return [], f"the log could not be read: {err}"
    if not text:
        return [], "no log file at the expected path, so blocking calls could not be counted"
    return parse_blocking_calls(text), None


async def _measure_reachability(scan: Scan) -> tuple[list[Reach], str | None]:
    """One timed connect per declared endpoint, a few at a time."""
    targets = declared_targets(scan)
    if not targets:
        return [], "no config entry declares a host and a port, so there was nothing to connect to"

    gate = asyncio.Semaphore(CONNECT_PARALLELISM)

    async def _one(entry_id: str, host: str, port: int) -> Reach:
        async with gate:
            started = time.perf_counter()
            try:
                _reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port), timeout=CONNECT_TIMEOUT
                )
            except asyncio.TimeoutError:
                return Reach(entry_id, host, port, False, None, f"no answer within {CONNECT_TIMEOUT:g}s")
            except OSError as err:
                return Reach(entry_id, host, port, False, None, err.strerror or str(err))
            except Exception as err:  # noqa: BLE001
                return Reach(entry_id, host, port, False, None, str(err))
            latency = (time.perf_counter() - started) * 1000
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:  # noqa: BLE001
                pass
            return Reach(entry_id, host, port, True, latency)

    results = await asyncio.gather(*(_one(*target) for target in targets))
    results.sort(key=lambda row: (row.reachable, -(row.latency_ms or 0), row.host))
    return results, None
