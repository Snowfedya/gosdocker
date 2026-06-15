"""Unit tests for port-conflict preflight in generate pipeline.

Run with: python3 -m pytest tests/test_port_conflict.py -v

Bug: nginx + angie-pro (both bind host 80 and 443) generates a compose file
that passes syntax check but fails at runtime with `bind: address already in use`.
The preflight must reject the request with HTTP 409 BEFORE the ZIP is built.
"""
import pytest

from app.services.port_preflight import check_port_conflicts, PortConflictError


# ── fixtures ──────────────────────────────────────────────────

class _Component:
    """Minimal Component stand-in matching the model's attribute set used here."""
    def __init__(self, slug, default_ports):
        self.slug = slug
        self.default_ports = default_ports


@pytest.fixture
def nginx():
    return _Component("nginx", {"80": 80, "443": 443})


@pytest.fixture
def angie_pro():
    return _Component("angie-pro", {"80": 80, "443": 443})


@pytest.fixture
def postgresql():
    return _Component("postgresql", {"5432": 5432})


# ── happy path ────────────────────────────────────────────────

def test_no_conflict_for_disjoint_ports(nginx, postgresql):
    """nginx (80,443) + postgresql (5432) — distinct host ports, must pass."""
    # No exception expected
    check_port_conflicts([nginx, postgresql], configs={})


# ── the bug: same port on two services ───────────────────────

def test_same_port_two_services_raises(nginx, angie_pro):
    """nginx and angie-pro both want host 80 and 443 → PortConflictError."""
    with pytest.raises(PortConflictError) as exc_info:
        check_port_conflicts([nginx, angie_pro], configs={})
    # The error must name the conflicting port
    assert "80" in str(exc_info.value)
    # And both services
    msg = str(exc_info.value)
    assert "nginx" in msg
    assert "angie-pro" in msg


def test_conflict_error_is_an_http_409_mappable(nginx, angie_pro):
    """The error must carry a structured payload the API can return as 409."""
    with pytest.raises(PortConflictError) as exc_info:
        check_port_conflicts([nginx, angie_pro], configs={})
    err = exc_info.value
    # Structured fields for the HTTP layer
    assert hasattr(err, "conflicts")
    assert isinstance(err.conflicts, list)
    assert len(err.conflicts) >= 1
    first = err.conflicts[0]
    # Each conflict: {"host_port": int, "services": [str, ...]}
    assert "host_port" in first
    assert "services" in first
    assert first["host_port"] == 80
    assert set(first["services"]) == {"nginx", "angie-pro"}


# ── user override can resolve conflict ────────────────────────

def test_user_override_resolves_conflict(nginx, angie_pro):
    """If user remaps angie-pro to different host ports, no conflict."""
    configs = {"angie-pro": {"ports": {"8080": 80, "8443": 443}}}
    # No exception
    check_port_conflicts([nginx, angie_pro], configs=configs)


# ── single service, no conflict ──────────────────────────────

def test_single_service_always_passes(nginx):
    check_port_conflicts([nginx], configs={})
