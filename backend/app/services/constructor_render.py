"""Pure rendering helpers used by the constructor API.

These functions build the docker-compose service entries and README
content. They are pure (no FastAPI / no async I/O) so they live in
``app/services/`` and are unit-testable without the API surface.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

# PipelineContext is a duck-typed object — we only read .artifacts dict
# (mapping artifact-name → path-or-None). Avoids importing the heavy
# pipeline module just for the type alias.
PipelineContextLike = Any


def build_service_entry(slug: str, manifest: dict, config: dict) -> dict:
    """Build a single service entry for docker-compose.yml.

    Mirrors what the legacy ``app/api/constructor._build_service_entry``
    produced: container_name, build context, networks, ports (user
    override → manifest default), and environment (with secret sanitization
    matching ``GenerateService._render_compose``).
    """
    service = {
        "container_name": slug,
        "build": {
            "context": f"./build/{slug}",
            "dockerfile": "Dockerfile",
            "args": {
                "VERSION": manifest.get("version", "1.0"),
            },
        },
        "networks": ["gosdocker"],
    }

    ports = manifest.get("ports", {})
    user_ports = config.get("ports", {})
    if user_ports:
        service["ports"] = [f"{ext}:{intv}" for ext, intv in user_ports.items()]
    elif ports:
        service["ports"] = [f"{intv}:{intv}" for _, intv in ports.items()]

    env = manifest.get("default_env", {})
    user_env = config.get("env", {})
    merged_env: dict = {}
    if user_env:
        merged_env = {**env, **user_env}
    elif env:
        merged_env = dict(env)
    if merged_env:
        # Sanitize secret env values (Bug #6). Same rule as in
        # GenerateService._render_compose. The KEY is preserved so users
        # see what to set; the value is replaced with a safe placeholder
        # that docker compose will resolve from .env at runtime.
        from app.services.generate_service import is_secret_key, _SECRET_PLACEHOLDER

        merged_env = {
            k: (_SECRET_PLACEHOLDER if is_secret_key(k) else v)
            for k, v in merged_env.items()
        }
        service["environment"] = merged_env

    return service


_ARTIFACT_LABELS = {
    "sbom": "SBOM (CycloneDX)",
    "trivy_report": "Trivy scan report",
    "owasp_report": "OWASP Dependency-Check report",
    "cosign_pub": "Cosign public key",
    "cosign_sig": "Cosign signature",
    "image_tar": "Docker image tar",
    "deploy_script": "Deploy script",
}


def build_readme(
    resolved: list[str],
    manifests: dict[str, dict],
    auto_added: list[dict],
    profile: str,
    pipeline_results: dict[str, PipelineContextLike] | None = None,
    security_errors: list[str] | None = None,
    with_owasp: bool = True,  # AC-CONST-4
) -> str:
    """Build README.md with component list and security report summary.

    AC-CONST-4: in fast mode (``with_owasp=False``) the security section
    is replaced with a warning that no security verification was run.
    """
    comp_lines = []
    for slug in resolved:
        m = manifests[slug].get("component", {})
        auto_note = ""
        for aa in auto_added:
            if aa["slug"] == slug:
                auto_note = f" (автоматически: {aa['reason']})"
        comp_lines.append(
            f"- **{m.get('name', slug)}** v{m.get('version', '?')}{auto_note}"
        )

    sec_lines: list[str] = []
    if pipeline_results:
        for slug in resolved:
            ctx = pipeline_results.get(slug)
            if not ctx:
                continue
            artifacts = {k: v for k, v in ctx.artifacts.items() if v is not None}
            art_list = [
                f"  - ✅ {_ARTIFACT_LABELS.get(k, k)}"
                for k in artifacts
                if k in _ARTIFACT_LABELS
            ]
            if art_list:
                sec_lines.append(f"- **{slug}**:")
                sec_lines.extend(art_list)

    sec_text = "\n".join(sec_lines) if sec_lines else "Артефакты не сгенерированы."

    fast_mode_warning = ""
    if not with_owasp:
        fast_mode_warning = (
            "\n## ⚠️ Режим без проверки безопасности\n\n"
            "Этот стек сгенерирован в быстром режиме (`with_owasp: false`).\n"
            "**Проверка безопасности НЕ выполнялась**: SBOM (CycloneDX), Trivy, "
            "OWASP Dependency-Check и подпись Cosign отсутствуют. "
            "Для продакшн-развёртывания в государственных учреждениях "
            "пересоберите стек с `with_owasp: true`.\n"
        )

    err_text = ""
    if security_errors:
        err_lines = "\n".join(f"  ⚠️ {e}" for e in security_errors)
        err_text = f"\n## Предупреждения\n\n{err_lines}\n"

    return f"""# GosDocker Stack — Конструктор

Сгенерировано: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
Профиль безопасности: {profile}

## Состав стека

{chr(10).join(comp_lines)}

## Быстрый старт

```bash
# 1. Соберите образы из исходников
docker compose build

# 2. Запустите стек
docker compose up -d
```

## Артефакты безопасности

{sec_text}

## Режим Air-Gapped

Для развёртывания в изолированном контуре:

1. `docker compose build` — собрать образы
2. `docker save -o images.tar <image1> <image2> ...` — экспортировать
3. `docker load -i images.tar && docker compose up -d`

### Проверка подписей (Cosign)

```bash
# Для каждого компонента с подписью:
cosign verify-blob --key security/<slug>/<slug>-cosign.pub \\
    --signature security/<slug>/<slug>-cosign.sig \\
    security/<slug>/<slug>.tar
```
{fast_mode_warning}{err_text}"""
