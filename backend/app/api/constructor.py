"""Constructor API — dependency-aware component stack generation.

POST /api/constructor
Takes selected components, resolves dependencies, applies security profile,
runs pipeline, returns ZIP with compose + build artifacts + security reports.
"""
import asyncio
import io
import json
import re
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.pipeline import (
    Pipeline, BuildStep, ScanStep, PackageStep, RegisterStep,
    SignStep, DependencyCheckStep,
)
from app.pipeline.base import PipelineContext
from app.services.dependency_resolver import DependencyResolver
from app.services.security_profiles import apply_profile, list_profiles, get_profile_info
from app.services.port_preflight import check_port_conflicts, PortConflictError

router = APIRouter(prefix="/api/constructor", tags=["constructor"])

REGISTRY_BASE = Path(__file__).parent.parent.parent / "registry"

resolver = DependencyResolver()

_executor = ThreadPoolExecutor(max_workers=2)

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,60}[a-z0-9]$")

def _validate_slug(slug: str, context: str = "") -> str:
    """Validate component slug against safe pattern to prevent path traversal."""
    if not _SLUG_RE.match(slug):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid slug '{slug}'{context}. "
                   f"Must match [a-z0-9][a-z0-9-]{{0,60}}[a-z0-9]",
        )
    return slug


# Pipeline instance used for each component build
_SECURITY_PIPELINE = Pipeline([
    BuildStep(),
    ScanStep(),
    DependencyCheckStep(),
    PackageStep(),
    SignStep(),
    RegisterStep(),
])


class ConstructorRequest(BaseModel):
    components: list[str]
    profile: str = "standard"
    configs: dict[str, dict] = {}
    fast_mode: bool = False  # Skip security pipeline, generate compose only

    class Config:
        json_schema_extra = {
            "example": {
                "components": ["nginx", "nextcloud"],
                "profile": "standard",
                "configs": {"nginx": {"ports": {"80": 80}}},
            }
        }


class ConstructorDiagnostic(BaseModel):
    resolved: list[str]
    auto_added: list[dict]
    profile: dict | None = None
    errors: list[str] = []


class _ManifestComponent:
    """Duck-typed component used by port_preflight.

    port_preflight expects objects with `.slug` and `.default_ports` (the
    shape of ORM `Component` rows, where the dict is `{host_port: int}`).
    Manifests on disk, however, store `component.ports` as
    `{protocol_name: container_port}` (e.g. `{"http": 80, "https": 443}`).
    This shim normalises both into the host-port format the conflict
    checker expects.
    """
    __slots__ = ("slug", "default_ports")

    def __init__(self, slug: str, manifest: dict):
        self.slug = slug
        raw = (
            manifest.get("component", {}).get("ports", {})
            or manifest.get("ports", {})
            or {}
        )
        # Translate {name: port} → {port: port}. Anything non-numeric is
        # silently skipped — port_preflight raises a clearer error than
        # `int("http")` would.
        normalised: dict[str, int] = {}
        for v in raw.values():
            try:
                port = int(v)
            except (TypeError, ValueError):
                continue
            normalised[str(port)] = port
        self.default_ports = normalised


# ── Helpers ──────────────────────────────────────────────────────────


def _load_manifests(slugs: list[str]) -> dict[str, dict]:
    """Bulk-load manifests for port_preflight.

    Returns a dict slug → parsed manifest. Missing manifests are silently
    skipped (the diagnostic path will report them in `errors` anyway).
    """
    out: dict[str, dict] = {}
    for slug in slugs:
        manifest_path = REGISTRY_BASE / slug / "manifest.yml"
        if manifest_path.exists():
            out[slug] = yaml.safe_load(manifest_path.read_text())
    return out


def _run_pipeline_for_component(
    slug: str,
    manifest: dict,
    profile: str,
) -> PipelineContext:
    """Run the full security pipeline for a single component (blocking)."""
    work_dir = Path("/tmp/gosdocker-constructor") / slug
    return _SECURITY_PIPELINE.run(manifest, profile=profile, work_dir=work_dir)


def _build_service_entry(slug: str, manifest: dict, config: dict) -> dict:
    """Build a single service entry for docker-compose.yml."""
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


def _build_readme(
    resolved: list[str],
    manifests: dict[str, dict],
    auto_added: list[dict],
    profile: str,
    pipeline_results: dict[str, PipelineContext] | None = None,
    security_errors: list[str] | None = None,
) -> str:
    """Build README.md with component list and security report summary."""
    comp_lines = []
    for slug in resolved:
        m = manifests[slug].get("component", {})
        auto_note = ""
        for aa in auto_added:
            if aa["slug"] == slug:
                auto_note = f" (автоматически: {aa['reason']})"
        comp_lines.append(f"- **{m.get('name', slug)}** v{m.get('version', '?')}{auto_note}")

    # Security artifacts summary per component
    sec_lines = []
    if pipeline_results:
        for slug in resolved:
            ctx = pipeline_results.get(slug)
            if not ctx:
                continue
            artifacts = {k: v for k, v in ctx.artifacts.items() if v is not None}
            labels = {
                "sbom": "SBOM (CycloneDX)",
                "trivy_report": "Trivy scan report",
                "owasp_report": "OWASP Dependency-Check report",
                "cosign_pub": "Cosign public key",
                "cosign_sig": "Cosign signature",
                "image_tar": "Docker image tar",
                "deploy_script": "Deploy script",
            }
            art_list = [f"  - ✅ {labels.get(k, k)}" for k, v in artifacts.items() if k in labels]
            if art_list:
                sec_lines.append(f"- **{slug}**:")
                sec_lines.extend(art_list)

    sec_text = "\n".join(sec_lines) if sec_lines else "Артефакты не сгенерированы."

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
{err_text}"""


# ── API ──────────────────────────────────────────────────────────────


@router.post("/diagnostic")
async def constructor_diagnostic(body: ConstructorRequest):
    """Resolve dependencies and return what would be generated (no ZIP)."""
    for slug in body.components:
        _validate_slug(slug, " in components list")
    resolved, auto_added = resolver.resolve_with_metadata(body.components)

    errors = []
    for slug in resolved:
        manifest_path = REGISTRY_BASE / slug / "manifest.yml"
        if not manifest_path.exists():
            errors.append(f"Component '{slug}' has no manifest in registry")

    # Port conflict check (mirrors /api/generate behaviour).
    # Components are loaded as duck-typed objects so port_preflight can read
    # `.slug` and `.default_ports` (the same shape it expects from ORM rows).
    manifests_for_ports = _load_manifests(resolved)
    components_for_ports = [_ManifestComponent(s, manifests_for_ports[s]) for s in resolved if s in manifests_for_ports]
    try:
        check_port_conflicts(components_for_ports, body.configs)
    except PortConflictError as e:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "port_conflict",
                "message": (
                    "Selected components bind the same host port. "
                    "Remap one of them under 'config.<slug>.ports' "
                    "and retry."
                ),
                "conflicts": e.conflicts,
            },
        )

    return ConstructorDiagnostic(
        resolved=resolved,
        auto_added=auto_added,
        profile=get_profile_info(body.profile),
        errors=errors,
    )


@router.post("")
async def constructor_generate(body: ConstructorRequest):
    """Generate a complete deployment package with dependency resolution.

    For each component runs the security pipeline (SBOM, Trivy, OWASP DC,
    image packaging, Cosign signing). All artifacts bundled into ZIP.
    """
    # Validate all slugs
    for slug in body.components:
        _validate_slug(slug, " in components list")

    # 1. Resolve dependencies
    resolved, auto_added = resolver.resolve_with_metadata(body.components)

    # 1a. Port conflict check (early-fail before running the security pipeline)
    manifests_for_ports = _load_manifests(resolved)
    components_for_ports = [_ManifestComponent(s, manifests_for_ports[s]) for s in resolved if s in manifests_for_ports]
    try:
        check_port_conflicts(components_for_ports, body.configs)
    except PortConflictError as e:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "port_conflict",
                "message": (
                    "Selected components bind the same host port. "
                    "Remap one of them under 'config.<slug>.ports' "
                    "and retry."
                ),
                "conflicts": e.conflicts,
            },
        )

    # 2. Validate all components exist
    manifests = {}
    for slug in resolved:
        manifest_path = REGISTRY_BASE / slug / "manifest.yml"
        if not manifest_path.exists():
            raise HTTPException(
                status_code=400,
                detail=f"Component '{slug}' not found in registry"
            )
        manifests[slug] = yaml.safe_load(manifest_path.read_text())

    # 3. Run security pipeline for each component (parallel) — skip in fast_mode
    pipeline_results: dict[str, PipelineContext] = {}
    security_errors: list[str] = []

    if not body.fast_mode:
        loop = asyncio.get_running_loop()
        tasks = []
        for slug in resolved:
            manifest = manifests[slug]
            tasks.append(
                loop.run_in_executor(
                    _executor,
                    _run_pipeline_for_component,
                    slug, manifest, body.profile,
                )
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for slug, result in zip(resolved, results):
            if isinstance(result, Exception):
                security_errors.append(f"{slug}: {result}")
            else:
                pipeline_results[slug] = result
                if result.errors:
                    security_errors.extend(f"{slug}: {e}" for e in result.errors)

    # 4. Generate ZIP
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        # docker-compose.yml
        services_section = {}
        for slug in resolved:
            manifest = manifests[slug].get("component", {})
            service_def = _build_service_entry(slug, manifest, body.configs.get(slug, {}))
            services_section[slug] = service_def

        compose = {
            "services": services_section,
            "networks": {"gosdocker": {"driver": "bridge"}},
        }
        apply_profile(compose, body.profile)

        header = (
            f"# Generated by GosDocker — Реестр гос. ИТ-компонентов\n"
            f"# {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            f"# Profile: {body.profile}\n"
        )
        zf.writestr(
            "docker-compose.yml",
            header + yaml.dump(compose, default_flow_style=False, sort_keys=False, allow_unicode=True, indent=2),
        )

        # Build context for each component
        for slug in resolved:
            dockerfile_path = REGISTRY_BASE / slug / "Dockerfile"
            if dockerfile_path.exists():
                zf.write(str(dockerfile_path), f"build/{slug}/Dockerfile")

        # .env.example
        from app.services.generate_service import is_secret_key, _SECRET_PLACEHOLDER
        env_lines = ["# GosDocker Environment Variables", "# Generated Constructor Stack", "# Copy to .env and set real values; secrets are masked.\n"]
        for slug in resolved:
            manifest = manifests[slug].get("component", {})
            default_env = dict(manifest.get("default_env", {}) or {})
            # Merge user env (user wins)
            user_cfg = body.configs.get(slug) or {}
            default_env.update(user_cfg.get("env") or {})
            for key, val in default_env.items():
                # Bug #6: mask secret values in .env.example
                if is_secret_key(key):
                    val = _SECRET_PLACEHOLDER
                env_lines.append(f"{slug.upper()}_{key.upper()}={val}")
        zf.writestr(".env.example", "\n".join(env_lines))

        # Security artifacts from pipeline
        for slug in resolved:
            ctx = pipeline_results.get(slug)
            if not ctx:
                continue
            for art_key, art_path in ctx.artifacts.items():
                if not art_path:
                    continue
                art_file = Path(art_path)
                if art_file.exists():
                    arcname = f"security/{slug}/{art_file.name}"
                    zf.write(str(art_file), arcname)

        # README.md
        readme = _build_readme(
            resolved, manifests, auto_added, body.profile,
            pipeline_results=pipeline_results,
            security_errors=security_errors,
        )
        zf.writestr("README.md", readme)

    buffer.seek(0)

    # Prepare filename
    stack_name = "-".join(resolved[:3])
    if len(resolved) > 3:
        stack_name += f"-and-{len(resolved) - 3}-more"

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=gosdocker-{stack_name}.zip"
        },
    )


@router.get("/profiles")
async def list_available_profiles():
    """List available security profiles."""
    return list_profiles()
