"""
TDD: AC-4.1 senior-audit — generated compose must NOT contain hardcoded
container_name (forces port conflicts and breaks scaling/replicas).

RED proof: tests scan all rendered templates via jinja2 and fail if
any output contains `container_name:`.
"""
import os
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader


TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "app" / "templates"


def _render(relative_path: str, ctx: dict) -> str:
    """Render a template through the real TemplateService (handles now(),
    configs, registry_url, etc. properly)."""
    from app.services.template_service import TemplateService

    svc = TemplateService()

    # Decide single vs stack from path
    rel = relative_path.replace("\\", "/")
    if rel.startswith("single/"):
        # rel = single/<slug>/docker-compose.yml.j2
        slug = rel.split("/")[1]
        return svc.render_single(slug, ctx.get("config") or {})
    if rel.startswith("stacks/"):
        slug = rel.split("/")[1].replace(".yml.j2", "")
        return svc.render_stack(
            slug,
            ctx.get("components") or [],
            ctx.get("configs") or {},
        )
    raise ValueError(f"unknown template path: {rel}")


def _all_template_files():
    return list(TEMPLATES_DIR.rglob("*.j2"))


def test_no_hardcoded_container_name_in_single_templates():
    """
    Каждый single-шаблон после рендера с минимальным контекстом
    НЕ должен содержать `container_name:`.
    """
    single = TEMPLATES_DIR / "single"
    files = list(single.rglob("*.j2"))
    assert files, f"no single templates found under {single}"
    leaks = []
    for f in files:
        out = _render(
            f.relative_to(TEMPLATES_DIR).as_posix(),
            {"registry_url": "nginx:1.28", "config": {}},
        )
        if "container_name:" in out:
            leaks.append(f.name)
    assert not leaks, f"hardcoded container_name in: {leaks}"


def test_no_hardcoded_container_name_in_stack_templates():
    """
    Stack-шаблоны тоже не должны содержать `container_name:`.
    """
    stacks = TEMPLATES_DIR / "stacks"
    files = list(stacks.rglob("*.j2"))
    assert files, f"no stack templates found under {stacks}"
    leaks = []
    for f in files:
        try:
            out = _render(
                f.relative_to(TEMPLATES_DIR).as_posix(),
                {"components": [], "configs": {}},
            )
        except Exception as e:
            pytest.fail(f"render failed for {f.name}: {e}")
        if "container_name:" in out:
            leaks.append(f.name)
    assert not leaks, f"hardcoded container_name in: {leaks}"


def test_no_container_name_in_template_sources_either():
    """
    Дополнительно: исходники .j2 сами не должны содержать
    `container_name:` (чтобы при будущих правках не вернулось).
    """
    leaks = []
    for f in _all_template_files():
        content = f.read_text(encoding="utf-8")
        if "container_name:" in content:
            leaks.append(str(f.relative_to(TEMPLATES_DIR)))
    assert not leaks, f"container_name hardcoded in template sources: {leaks}"
