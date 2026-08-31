"""Find the AdGuard Home endpoint instead of asking for it.

Most of what is needed is already somewhere in Home Assistant: the official
AdGuard integration stores host, port and credentials; the add-on always
answers on a known hostname. Talos looks in those places, probes what it
finds, and pre-fills the form with the first address that actually answers.

Two rules shape this file. Nothing is ever used silently: whatever is found is
put in the form where the user can see and change it. And nothing is assumed:
a candidate counts only once `/control/status` has answered on it, because a
wrong address that looks plausible produces an empty report that reads like a
clean one.

The functions that decide what to try are pure, so they are unit-testable
without Home Assistant. Only `async_probe` touches the network, through a
callable the caller supplies.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Awaitable, Callable, Iterable, Sequence
from urllib.parse import urlsplit

STATUS_PATH = "/control/status"

# The community add-on's hostname. Fixed by its slug, so it survives an IP
# change and works from inside the Home Assistant container.
ADDON_HOSTNAME = "a0d7b954-adguard"

# Ports worth trying, in the order they are worth trying them.
COMMON_PORTS: tuple[int, ...] = (3000, 80, 8080, 443)


@dataclass(frozen=True, slots=True)
class Candidate:
    """One address to try, and where the idea came from."""

    url: str
    username: str = ""
    password: str = ""
    verify_ssl: bool = True
    source: str = ""

    @property
    def has_credentials(self) -> bool:
        return bool(self.username or self.password)


def candidates_from_adguard_entries(entries: Iterable[dict[str, Any]]) -> list[Candidate]:
    """Read the official AdGuard integration's own configuration.

    This is the best source by far: if that integration works, its address and
    credentials work too. Its data is only ever offered back to the same admin
    who already owns it, inside a form they can edit.
    """
    found: list[Candidate] = []
    for data in entries:
        host = str(data.get("host") or "").strip()
        if not host:
            continue
        scheme = "https" if data.get("ssl") else "http"
        port = data.get("port")
        authority = f"{host}:{port}" if port else host
        found.append(
            Candidate(
                url=f"{scheme}://{authority}",
                username=str(data.get("username") or ""),
                password=str(data.get("password") or ""),
                verify_ssl=bool(data.get("verify_ssl", True)),
                source="adguard_integration",
            )
        )
    return found


def fallback_candidates(internal_url: str | None = None) -> list[Candidate]:
    """Addresses worth trying when nothing is configured yet.

    The add-on hostname first, because it is stable and resolvable from inside
    Home Assistant, then the host Home Assistant knows itself by, since the
    add-on usually runs on the same machine.
    """
    hosts = [ADDON_HOSTNAME]
    if internal_url:
        host = urlsplit(internal_url).hostname
        if host and host not in hosts:
            hosts.append(host)

    found: list[Candidate] = []
    for host in hosts:
        for port in COMMON_PORTS:
            scheme = "https" if port == 443 else "http"
            found.append(
                Candidate(
                    url=f"{scheme}://{host}:{port}",
                    # A self-signed or DuckDNS certificate never matches an
                    # internal hostname, so verification would always fail.
                    verify_ssl=False,
                    source="addon" if host == ADDON_HOSTNAME else "internal_url",
                )
            )
    return found


def deduplicate(candidates: Iterable[Candidate]) -> list[Candidate]:
    """Keep the first candidate per address, so a configured one wins."""
    seen: set[str] = set()
    unique: list[Candidate] = []
    for candidate in candidates:
        key = candidate.url.rstrip("/")
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return unique


async def async_probe(
    check: Callable[[Candidate], Awaitable[str | None]],
    candidates: Sequence[Candidate],
) -> Candidate | None:
    """Return the first candidate that answers, or None.

    `check` returns "ok" when the API answered, "auth" when it answered but
    demanded credentials, and None when there was nothing there. An "auth"
    answer still confirms the address: only the credentials are missing, which
    is exactly what the form is for.
    """
    for candidate in candidates:
        outcome = await check(candidate)
        if outcome == "ok":
            return candidate
        if outcome == "auth":
            # Confirmed address, but the credentials we guessed do not apply.
            return replace(candidate, username="", password="")
    return None
