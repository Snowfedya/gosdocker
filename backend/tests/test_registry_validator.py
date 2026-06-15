"""Unit tests for the registry URL parser/validator used by the seed CLI.

The validator is a pure-Python helper:
  1) parses `registry/repo:tag` into structured parts
  2) checks well-formedness (no empty parts, no 'latest' ambiguity, etc.)
  3) does NOT do network calls — that's a separate CLI step

Network-level "does this tag exist in the registry?" verification lives in
`scripts/verify_seed_images.py` and is run manually before re-seeding.
"""
import pytest

from app.services.registry_validator import (
    parse_registry_url,
    RegistryValidationError,
)


# ── parsing: good inputs ──────────────────────────────────────


def test_parses_three_part_url():
    p = parse_registry_url("registry.red-soft.ru/ubi8/postgresql-17:17")
    assert p["registry"] == "registry.red-soft.ru"
    assert p["repo"] == "ubi8/postgresql-17"
    assert p["tag"] == "17"


def test_parses_dh_mirror_library():
    p = parse_registry_url("dh-mirror.gitverse.ru/library/nginx:1.28")
    assert p["registry"] == "dh-mirror.gitverse.ru"
    assert p["repo"] == "library/nginx"
    assert p["tag"] == "1.28"


def test_parses_deep_path():
    p = parse_registry_url("dh-mirror.gitverse.ru/grafana/grafana:11.6.15")
    assert p["registry"] == "dh-mirror.gitverse.ru"
    assert p["repo"] == "grafana/grafana"
    assert p["tag"] == "11.6.15"


# ── parsing: bad inputs (defensive) ───────────────────────────


def test_missing_tag_raises():
    with pytest.raises(RegistryValidationError):
        parse_registry_url("dh-mirror.gitverse.ru/library/nginx")


def test_empty_raises():
    with pytest.raises(RegistryValidationError):
        parse_registry_url("")


def test_no_slash_raises():
    with pytest.raises(RegistryValidationError):
        parse_registry_url("nginx:1.28")


def test_latest_tag_raises():
    """`:latest` is a deployment hazard — refuse it explicitly."""
    with pytest.raises(RegistryValidationError) as exc_info:
        parse_registry_url("dh-mirror.gitverse.ru/library/nginx:latest")
    assert "latest" in str(exc_info.value).lower()
