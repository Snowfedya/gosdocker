"""Shared component-slug validation.

Used by every API endpoint that takes a slug from user input and
uses it to construct a filesystem path (manifest, Dockerfile, reports).

The original pattern was duplicated in ``app/api/constructor.py`` and
``app/api/registry.py`` — extracting it here means:
- One place to harden the regex if a bypass is found
- Trivially unit-testable
- Other future endpoints can ``from app.services.slug import validate_slug``

Pattern: ``^[a-z0-9][a-z0-9-]{0,60}[a-z0-9]$``
- starts and ends with [a-z0-9] (no leading/trailing hyphens)
- middle can contain [a-z0-9-]
- total length 2..62 chars
- explicitly rejects path traversal: ``..``, ``/``, ``\\``, ``%2F``, null bytes
"""
from __future__ import annotations

import re

from fastapi import HTTPException

# Public regex so callers can do their own checks when needed.
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,60}[a-z0-9]$")


def is_valid_slug(slug: str) -> bool:
    """Return True iff slug matches the safe pattern."""
    if not isinstance(slug, str):
        return False
    return SLUG_RE.match(slug) is not None


def validate_slug(slug: str, context: str = "") -> str:
    """Validate slug, returning it on success. Raises 400 HTTPException otherwise.

    Parameters
    ----------
    slug : str
        The component slug from user input.
    context : str
        Optional human-readable context appended to the error message,
        e.g. ``" in components list"`` to help the user locate the
        problem in their request.

    Returns
    -------
    str
        The slug, unchanged, on success.

    Raises
    ------
    HTTPException
        400 with detail explaining the pattern requirement.
    """
    if not is_valid_slug(slug):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid slug '{slug}'{context}. "
                f"Must match [a-z0-9][a-z0-9-]{{0,60}}[a-z0-9]"
            ),
        )
    return slug
