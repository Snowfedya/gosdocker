"""Tests for port conflict validation in /api/constructor endpoint.

Why this exists:
  /api/generate returns 409 with detail.conflicts (Bug #1, fixed in phase 02).
  /api/constructor — the route ConstructorView actually uses — had NO
  port conflict check at all. This test enforces the same contract on
  the constructor endpoint.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_constructor_returns_409_for_port_conflict(client):
    """nginx + angie-pro both bind 80/443 → 409 with detail.conflicts."""
    res = client.post(
        "/api/constructor",
        json={
            "components": ["nginx", "angie-pro"],
            "profile": "basic",
            "fast_mode": True,
            "configs": {},
        },
    )
    assert res.status_code == 409, f"Expected 409, got {res.status_code}: {res.text[:200]}"
    body = res.json()
    assert "detail" in body
    detail = body["detail"]
    assert "conflicts" in detail, f"detail must contain 'conflicts', got: {detail}"
    conflicts = detail["conflicts"]
    assert isinstance(conflicts, list) and len(conflicts) >= 1
    # Each conflict has a port and at least 2 components
    for c in conflicts:
        assert "host_port" in c
        assert "services" in c
        assert len(c["services"]) >= 2


def test_constructor_does_not_409_for_disjoint_ports(client):
    """Two components with no port overlap → no 409."""
    res = client.post(
        "/api/constructor",
        json={
            "components": ["nginx", "redis"],
            "profile": "basic",
            "fast_mode": True,
            "configs": {},
        },
    )
    # We don't assert 200 here (the test DB might not have these), but
    # we MUST not see 409. Any other status is OK for the contract test.
    assert res.status_code != 409, f"Disjoint ports should not conflict: {res.text[:200]}"


def test_constructor_diagnostic_also_returns_409(client):
    """/api/constructor/diagnostic must also validate ports.

    The diagnostic endpoint is what the UI calls BEFORE generating, to
    give the user a chance to fix port conflicts. It must surface the
    same 409 detail.conflicts as the generate endpoint.
    """
    res = client.post(
        "/api/constructor/diagnostic",
        json={
            "components": ["nginx", "angie-pro"],
            "profile": "basic",
            "configs": {},
        },
    )
    assert res.status_code == 409, f"Expected 409, got {res.status_code}: {res.text[:200]}"
    body = res.json()
    detail = body.get("detail", {})
    assert "conflicts" in detail
