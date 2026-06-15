"""Sync pre-flight: validate that every requested slug exists in the registry.

If any slug is missing, return 400 with a clear error so the client doesn't
have to wait for the background job to fail. The pre-flight port check
instructor.py already returns 409; this complements it for the 400 case.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.constructor import _JOBS  # noqa: F401  -- ensure module loaded


client = TestClient(app)


def test_constructor_preflight_rejects_unknown_slug() -> None:
    """AC-CONST-2: synchronous 400 for unknown slug — the user should
    see a clear error immediately, not wait for the background job
    to discover the missing manifest."""
    response = client.post(
        "/api/constructor",
        json={
            "components": ["definitely-not-a-real-slug-xyz"],
            "profile": "standard",
            "fast_mode": True,
            "configs": {},
        },
    )
    assert response.status_code == 400, response.text
    body = response.json()
    assert "definitely-not-a-real-slug-xyz" in (body.get("detail", {}).get("message", "") or str(body))


def test_constructor_preflight_accepts_known_slug() -> None:
    """AC-CONST-2: known slugs return 202 + job_id, not 400."""
    response = client.post(
        "/api/constructor",
        json={
            "components": ["nginx"],
            "profile": "standard",
            "fast_mode": True,
            "configs": {},
        },
    )
    assert response.status_code == 202, response.text
    assert "job_id" in response.json()


def test_constructor_preflight_collects_all_missing_slugs() -> None:
    """If multiple slugs are missing, list them all in the error."""
    response = client.post(
        "/api/constructor",
        json={
            "components": ["nginx", "fake-a", "fake-b"],
            "profile": "standard",
            "fast_mode": True,
            "configs": {},
        },
    )
    assert response.status_code == 400
    msg = response.json().get("detail", {}).get("message", "")
    assert "fake-a" in msg
    assert "fake-b" in msg
