"""Port-conflict preflight for the generate pipeline.

Pure logic — no DB, no FastAPI. Raised errors carry structured `conflicts`
that the API layer maps to HTTP 409 with a JSON body.

Bug: nginx + angie-pro (both bind host 80/443) currently generates a compose
file that passes syntax validation but fails at runtime. This module catches
it BEFORE the ZIP is built.
"""
from collections import Counter
from typing import Iterable


class PortConflictError(Exception):
    """Raised when two or more services would bind the same host port.

    `conflicts` is a list of {"host_port": int, "services": [slug, ...]} so
    the HTTP layer can return a structured 409 body.
    """

    def __init__(self, conflicts: list[dict]):
        self.conflicts = conflicts
        # Human-readable summary
        lines = [
            f"Port conflict on host port {c['host_port']}: {', '.join(c['services'])}"
            for c in conflicts
        ]
        super().__init__("; ".join(lines))


def _effective_ports(slug: str, component, configs: dict) -> dict[str, int]:
    """Return the host→container port mapping that would be rendered for `slug`.

    Mirrors the merge logic in GenerateService._render_compose:
    user override wins; else component.default_ports.
    """
    raw = configs.get(slug)
    if raw is None:
        config = {}
    elif hasattr(raw, "model_dump"):
        config = raw.model_dump()
    elif isinstance(raw, dict):
        config = raw
    else:
        config = dict(raw)

    user_ports = config.get("ports")
    if user_ports:
        # Keys may be str or int; normalise to str for the collision check.
        return {str(k): int(v) for k, v in user_ports.items()}

    defaults = getattr(component, "default_ports", None) or {}
    return {str(k): int(v) for k, v in defaults.items()}


def check_port_conflicts(components: Iterable, configs: dict) -> None:
    """Raise PortConflictError if any host port is bound by ≥ 2 services.

    Returns None on success. `components` may be ORM rows or duck-typed
    objects with `slug` and `default_ports`.
    """
    # slug -> list of host ports
    port_to_services: dict[str, list[str]] = {}

    for comp in components:
        slug = comp.slug
        ports = _effective_ports(slug, comp, configs)
        for host_port in ports.keys():
            port_to_services.setdefault(host_port, []).append(slug)

    conflicts: list[dict] = []
    for host_port, slugs in port_to_services.items():
        # Dedup: if same slug listed twice (shouldn't happen, but defensive)
        unique = sorted(set(slugs))
        if len(unique) >= 2:
            conflicts.append({"host_port": int(host_port), "services": unique})

    if conflicts:
        # Stable ordering: by host_port ascending, then by first service
        conflicts.sort(key=lambda c: (c["host_port"], c["services"][0]))
        raise PortConflictError(conflicts)
