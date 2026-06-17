"""Registry URL parser/validator for seed data.

Pure logic — no network. Network-level "does this tag exist?" checks live
in `scripts/verify_seed_images.py` (run manually before re-seeding).

Rationale: seed.py runs at DB init time. Network calls during seed would
introduce flakiness (transient registry outages) and slow down startup.
This module catches well-formedness bugs at import time; existence is a
human-driven step.
"""
import re
from urllib.parse import urlparse


class RegistryValidationError(ValueError):
    """Raised when a registry_url string is malformed."""


# registry.red-soft.ru, dh-mirror.gitverse.ru, registry-1.docker.io, …
# Allow letters, digits, dots, hyphens. Must contain a dot (FQDN).
_HOST_RE = re.compile(r"^[a-z0-9][a-z0-9.\-]*\.[a-z]{2,}$")
# repo path: lowercase alnum + underscore, slash-separated, 1+ segments
_REPO_SEGMENT_RE = re.compile(r"^[a-z0-9_\-]+$")
# tag: conservative — alnum, dot, underscore, hyphen, plus `_alpine` / `-ubi8` style suffixes
_TAG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._\-]{0,127}$")


def parse_registry_url(url: str) -> dict:
    """Parse `registry/.../repo:tag` into structured parts.

    Returns: {"registry": str, "repo": str, "tag": str}

    Raises RegistryValidationError on any malformation. The format
    matches what `docker pull` accepts, but rejects `:latest` because
    mutable tags are a deployment hazard.
    """
    if not url or not isinstance(url, str):
        raise RegistryValidationError(f"registry_url must be a non-empty string, got: {url!r}")

    s = url.strip()
    if not s:
        raise RegistryValidationError("registry_url is empty/whitespace")

    # 1) split off the tag (last `:` that's not inside the registry FQDN)
    if ":" not in s:
        raise RegistryValidationError(
            f"registry_url missing tag: {url!r} (expected 'host/repo:tag')"
        )
    # tag is whatever comes after the LAST `:` — but that only works if the
    # registry host itself does not have a port. Our seed uses FQDNs only
    # (no ports), so last-`:` is safe.
    left, tag = s.rsplit(":", 1)

    # 2) split registry from the path. The registry is the first path segment.
    if "/" not in left:
        raise RegistryValidationError(
            f"registry_url missing repo path: {url!r} (expected 'host/repo:tag')"
        )
    registry, repo_path = left.split("/", 1)

    # 3) validate registry host
    if not _HOST_RE.match(registry):
        raise RegistryValidationError(
            f"registry host is not a valid FQDN: {registry!r} in {url!r}"
        )

    # 4) validate repo path
    for seg in repo_path.split("/"):
        if not _REPO_SEGMENT_RE.match(seg):
            raise RegistryValidationError(
                f"invalid repo segment {seg!r} in {url!r}"
            )
    if not repo_path:
        raise RegistryValidationError(f"empty repo path in {url!r}")

    # 5) validate tag
    if not _TAG_RE.match(tag):
        raise RegistryValidationError(
            f"invalid tag {tag!r} in {url!r}"
        )
    if tag.lower() == "latest":
        raise RegistryValidationError(
            f"tag ':latest' is forbidden (deployment hazard) in {url!r}"
        )

    return {"registry": registry, "repo": repo_path, "tag": tag}
