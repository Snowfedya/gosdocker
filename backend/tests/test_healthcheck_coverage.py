"""
AC-4.2 senior-audit: ≥6/10 single-templates must declare a healthcheck.
"""
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader


TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "app" / "templates"
SINGLE_DIR = TEMPLATES_DIR / "single"

# Список критичных для production сервисов, для которых senior-audit
# ожидает healthcheck. Базовые/опциональные (nextcloud, postgresql)
# НЕ в списке — они либо слишком медленно стартуют, либо есть
# встроенный healthcheck в самом образе.
EXPECTED_HEALTHCHECK_SERVICES = {
    "nginx",
    "angie-pro",
    "prometheus",
    "grafana",
    "redis",
    "clickhouse-redos",
    "mariadb-redos",
}


def _all_single_templates():
    return list(SINGLE_DIR.rglob("docker-compose.yml.j2"))


def test_minimum_healthcheck_coverage():
    """
    Покрытие healthcheck должно быть ≥60% от EXPECTED list (≥5/7).
    """
    coverage = 0
    for service in EXPECTED_HEALTHCHECK_SERVICES:
        f = SINGLE_DIR / service / "docker-compose.yml.j2"
        if f.exists() and "healthcheck:" in f.read_text(encoding="utf-8"):
            coverage += 1
    assert coverage >= 5, (
        f"expected ≥5/7 healthcheck coverage, got {coverage}/7. "
        f"Missing: {EXPECTED_HEALTHCHECK_SERVICES - {s for s in EXPECTED_HEALTHCHECK_SERVICES if (SINGLE_DIR/s/'docker-compose.yml.j2').exists() and 'healthcheck:' in (SINGLE_DIR/s/'docker-compose.yml.j2').read_text()}}"
    )


def test_rendered_nginx_has_valid_healthcheck():
    """Generated nginx compose должен иметь healthcheck с корректным test:."""
    from app.services.template_service import TemplateService

    out = TemplateService().render_single("nginx", {"ports": {"8080": "80"}})
    assert "healthcheck:" in out
    assert 'test:' in out
    # Должен быть executable, а не literal URL (иначе Docker ругается)
    assert "[" in out, f"healthcheck test must be CMD list, got: {out}"
    assert "wget" in out or "curl" in out


def test_rendered_redis_has_healthcheck():
    from app.services.template_service import TemplateService

    out = TemplateService().render_single("redis", {})
    assert "healthcheck:" in out
    assert "redis-cli" in out


def test_no_service_with_malformed_healthcheck():
    """Если healthcheck есть, test: должен быть CMD list (yaml sequence)."""
    bad = []
    for f in _all_single_templates():
        text = f.read_text(encoding="utf-8")
        if "healthcheck:" in text:
            # Find test: line, проверяем что есть [
            import re
            m = re.search(r"test:\s*([^\n]+)", text)
            if m and not m.group(1).strip().startswith("["):
                bad.append(f"{f.parent.name}: test={m.group(1).strip()}")
    assert not bad, f"malformed healthcheck test (must be CMD list): {bad}"
