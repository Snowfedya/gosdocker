"""Constructor API — dependency-aware component stack generation.

POST /api/constructor          — non-blocking (AC-CONST-2): 202 + job_id
GET  /api/constructor/jobs/{id}          — poll status + download_url
GET  /api/constructor/jobs/{id}/download — stream the assembled zip

AC-CONST-2: this used to be a synchronous handler that ran the full
security pipeline before streaming the zip. For a single registry
component like angie-pro the pipeline takes ~135s, longer than the
browser's 30s fetch timeout — the UI used to time out and the user
saw no archive. Now the POST returns 202 + job_id in <100ms and the
client polls the job endpoint, exactly like AC-4 for
/api/registry/{slug}/build.

AC-CONST-3: when the frontend sends ``fast_mode: true`` (single-
component quick download from ComponentCard.vue), the pipeline is
skipped if a warm cache entry exists for the same
``(slug, profile, manifest_hash)`` triple (30-minute TTL). On cache
miss the pipeline runs anyway — we never fail loudly on a miss.
"""
import hashlib
import io
import json
import re
import threading
import time
import uuid
import zipfile
from datetime import datetime
from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict

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

# AC-CONST-4: fast pipeline — build + package only. No OWASP / Trivy / Cosign.
# Used when the user explicitly opts out via with_owasp=False ("Скачать без проверки").
_FAST_PIPELINE = Pipeline([
    BuildStep(),
    PackageStep(),
])


class ConstructorRequest(BaseModel):
    components: list[str]
    profile: str = "standard"
    configs: dict[str, dict] = {}
    fast_mode: bool = False  # AC-CONST-3: cache hit-or-run for warm entries
    with_owasp: bool = True  # AC-CONST-4: full security pipeline (default)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "components": ["nginx", "nextcloud"],
                "profile": "standard",
                "configs": {"nginx": {"ports": {"80": 80}}},
                "with_owasp": True,
            }
        }
    )


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
    job_id: str | None = None,
) -> PipelineContext:
    """Run the full security pipeline for a single component (blocking).

    work_dir is namespaced by job_id first, then by slug. With the old
    shape ``/tmp/gosdocker-constructor/{slug}/`` two concurrent jobs
    that shared a component wrote into the same directory and their
    `docker run` invocations raced on the same tar / cosign artifacts.
    The job_id prefix isolates them; the slug is kept in the path so
    debugging on the host still works.
    """
    base = Path("/tmp/gosdocker-constructor")
    work_dir = base / (job_id or "unknown") / slug
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
    with_owasp: bool = True,  # AC-CONST-4
) -> str:
    """Build README.md with component list and security report summary.
    AC-CONST-4: in fast mode (with_owasp=False) the security section is
    replaced with a warning that no security verification was run."""
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

    # AC-CONST-4: explicit warning when the user opted out of OWASP.
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


# ── AC-CONST-2 / AC-CONST-3: in-memory job store + pipeline cache ──
# Mirrors the AC-4 job pattern in app/api/registry.py:419 (_JOBS).
# Single-process uvicorn keeps these dicts in-process; a multi-worker
# deployment should swap them for Redis (a TODO marker exists in
# registry.py for the same reason).
_JOBS: dict[str, dict] = {}
_PIPELINE_CACHE: dict[tuple, dict] = {}
_PIPELINE_CACHE_TTL_SECONDS = 30 * 60  # 30 minutes


def _cache_key(slug: str, profile: str, manifest_text: str) -> tuple:
    """AC-CONST-3: deterministic cache key.
    Includes the manifest text hash so a change to manifest.yml
    invalidates the cache (no stale reports for updated components)."""
    return (slug, profile, hashlib.sha256(manifest_text.encode("utf-8")).hexdigest())


def _cache_get(key: tuple) -> dict | None:
    entry = _PIPELINE_CACHE.get(key)
    if not entry:
        return None
    if time.time() - entry["cached_at"] > _PIPELINE_CACHE_TTL_SECONDS:
        _PIPELINE_CACHE.pop(key, None)
        return None
    return entry


def _cache_put(key: tuple, ctx) -> None:
    _PIPELINE_CACHE[key] = {"ctx": ctx, "cached_at": time.time()}


# ── API ──────────────────────────────────────────────────────────────


@router.post("/diagnostic")
async def constructor_diagnostic(body: ConstructorRequest):
    """Resolve dependencies and return what would be generated (no ZIP)."""
    for slug in body.components:
        _validate_slug(slug, " in components list")
    # Pre-flight: every requested slug must exist in the registry graph.
    # Without this, the background job would fail asynchronously — the
    # user would see "running" for ~60s and then "failed" with a stack
    # trace, which is terrible UX. Fail loud and synchronously instead.
    missing_slugs = [s for s in body.components if s not in resolver.graph]
    if missing_slugs:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "unknown_slug",
                "message": (
                    f"Unknown component(s): {', '.join(missing_slugs)}. "
                    "Check the registry for available slugs."
                ),
                "missing": missing_slugs,
            },
        )
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


def _build_zip_bytes(
    resolved: list[str],
    manifests: dict[str, dict],
    auto_added: list[dict],
    profile: str,
    configs: dict[str, dict],
    pipeline_results: dict[str, PipelineContext],
    security_errors: list[str],
    with_owasp: bool = True,  # AC-CONST-4
) -> bytes:
    """AC-CONST-2: extracted zip-assembly code from the old sync
    handler. Returns the assembled ZIP bytes. The caller (background
    job) is responsible for writing them to disk and updating _JOBS.

    The body is verbatim from the original handler — port_preflight
    is still applied (now by the launcher), Bug #6 secret masking
    in .env.example is preserved, and security artifacts are still
    pulled from pipeline contexts.

    AC-CONST-4: when with_owasp=False (fast path), the zip does NOT
    include any security-pipeline artifacts (no SBOM, no Trivy, no
    OWASP DC, no Cosign). It also skips `image_tar` and `deploy.sh`
    in fast mode — those exist for the signed-package deployment flow
    which the user opted out of. Build artifacts (Dockerfile) stay.
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        # docker-compose.yml
        services_section = {}
        for slug in resolved:
            manifest = manifests[slug].get("component", {})
            service_def = _build_service_entry(slug, manifest, configs.get(slug, {}))
            services_section[slug] = service_def

        compose = {
            "services": services_section,
            "networks": {"gosdocker": {"driver": "bridge"}},
        }
        apply_profile(compose, profile)

        header = (
            f"# Generated by GosDocker — Реестр гос. ИТ-компонентов\n"
            f"# {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            f"# Profile: {profile}\n"
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
            user_cfg = configs.get(slug) or {}
            default_env.update(user_cfg.get("env") or {})
            for key, val in default_env.items():
                # Bug #6: mask secret values in .env.example
                if is_secret_key(key):
                    val = _SECRET_PLACEHOLDER
                env_lines.append(f"{slug.upper()}_{key.upper()}={val}")
        zf.writestr(".env.example", "\n".join(env_lines))

        # Security artifacts from pipeline (AC-CONST-4: skipped in fast mode)
        if with_owasp:
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
            resolved, manifests, auto_added, profile,
            pipeline_results=pipeline_results if with_owasp else None,
            security_errors=security_errors,
            with_owasp=with_owasp,  # AC-CONST-4
        )
        zf.writestr("README.md", readme)

    buffer.seek(0)
    return buffer.getvalue()


def _run_constructor_job(job_id: str, body_dict: dict) -> None:
    """AC-CONST-2 + AC-CONST-3: background job that resolves manifests,
    runs the security pipeline (or hits the cache when fast_mode=True
    and a warm entry exists), builds the zip, persists it, and
    updates _JOBS[job_id] for polling.

    Status transitions: pending → running → ok | failed
    """
    job = _JOBS[job_id]
    job["status"] = "running"
    components = body_dict["components"]
    profile = body_dict["profile"]
    fast_mode = body_dict.get("fast_mode", False)
    with_owasp = body_dict.get("with_owasp", True)  # AC-CONST-4
    configs = body_dict.get("configs", {})

    try:
        # 1. Resolve dependencies
        resolved, auto_added = resolver.resolve_with_metadata(components)

        # 2. Port conflict check (early-fail before the pipeline).
        manifests_for_ports = _load_manifests(resolved)
        components_for_ports = [_ManifestComponent(s, manifests_for_ports[s]) for s in resolved if s in manifests_for_ports]
        try:
            check_port_conflicts(components_for_ports, configs)
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

        # 3. Validate all components exist
        manifests: dict[str, dict] = {}
        for slug in resolved:
            manifest_path = REGISTRY_BASE / slug / "manifest.yml"
            if not manifest_path.exists():
                raise HTTPException(
                    status_code=400,
                    detail=f"Component '{slug}' not found in registry"
                )
            manifests[slug] = yaml.safe_load(manifest_path.read_text())

        # 4. AC-CONST-3 / AC-CONST-4: pipeline selection.
        #   with_owasp=False → _FAST_PIPELINE (build + package only, no OWASP / Trivy / Cosign).
        #                       Скачивание идёт за секунды (build + zip), без 3-мин OWASP-скана.
        #   with_owasp=True  → _SECURITY_PIPELINE (full chain). Тяжёлый, но auditable.
        #   fast_mode=True   → AC-CONST-3: cache hit-or-run. Используется ТОЛЬКО при with_owasp=True
        #                       (для быстрых повторных скачиваний уже проверенного стека).
        pipeline_results: dict[str, PipelineContext] = {}
        security_errors: list[str] = []

        if not with_owasp:
            # AC-CONST-4 fast path: build + package only, no security artifacts.
            for slug in resolved:
                manifest = manifests[slug]
                work_dir = Path("/tmp/gosdocker-constructor") / job_id / slug
                ctx = _FAST_PIPELINE.run(manifest, profile=profile, work_dir=work_dir)
                pipeline_results[slug] = ctx
        elif not fast_mode:
            # Always run pipeline synchronously. Why: the pipeline is
            # already a blocking subprocess (docker build, trivy scan,
            # cosign sign). The previous asyncio.gather + run_until_complete
            # dance only added complexity AND a cross-loop bug: the
            # _run_pipeline_for_component callable is sync, so wrapping
            # it in run_in_executor just to unwrap it via run_until_complete
            # is pointless. Worse, when called from a daemon thread, the
            # fresh event loop clashes with uvicorn's loop when any
            # pipeline step touches an asyncpg-backed cache.
            #
            # For a single component the serial cost is the same as the
            # parallel cost. For 2+ components, a ThreadPoolExecutor
            # would still help, but the prototype only requested the
            # async-without-blocking-UI win — not parallelism. Keep it
            # simple, fix the cross-loop bug.
            for slug in resolved:
                manifest = manifests[slug]
                ctx = _run_pipeline_for_component(slug, manifest, profile, job_id=job_id)
                pipeline_results[slug] = ctx
        else:
            # fast_mode=True: hit-or-run.
            for slug in resolved:
                manifest = manifests[slug]
                manifest_text = (REGISTRY_BASE / slug / "manifest.yml").read_text()
                key = _cache_key(slug, profile, manifest_text)
                cached = _cache_get(key)
                if cached is not None:
                    pipeline_results[slug] = cached["ctx"]
                else:
                    # Mirror the non-fast path's job_id-namespaced work_dir
                    # so concurrent jobs with overlapping slugs don't race
                    # on the same tar / cosign artifacts. The cache key is
                    # (slug, profile, manifest_hash), so two jobs hitting
                    # the same cache entry is fine — only the cold path
                    # needs the per-job scratch dir.
                    work_dir = Path("/tmp/gosdocker-constructor") / job_id / slug
                    ctx = _SECURITY_PIPELINE.run(manifest, profile=profile, work_dir=work_dir)
                    pipeline_results[slug] = ctx
                    _cache_put(key, ctx)

        for slug, ctx in pipeline_results.items():
            if ctx is None:
                continue
            if ctx.errors:
                security_errors.extend(f"{slug}: {e}" for e in ctx.errors)

        # 5. Build the zip using the extracted helper.
        zip_bytes = _build_zip_bytes(
            resolved=resolved,
            manifests=manifests,
            auto_added=auto_added,
            profile=profile,
            configs=configs,
            pipeline_results=pipeline_results,
            security_errors=security_errors,
            with_owasp=with_owasp,  # AC-CONST-4
        )

        # 6. Persist zip in /tmp and update job
        zip_path = Path(f"/tmp/gosdocker-constructor/{job_id}.zip")
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        zip_path.write_bytes(zip_bytes)
        job["zip_path"] = str(zip_path)
        stack_name = "-".join(resolved[:3])
        if len(resolved) > 3:
            stack_name += f"-and-{len(resolved) - 3}-more"
        job["stack_name"] = stack_name
        job["status"] = "ok"
        job["errors"] = security_errors
    except HTTPException as e:
        job["status"] = "failed"
        job["error"] = e.detail if isinstance(e.detail, str) else str(e.detail)
    except Exception as e:  # pragma: no cover - defensive
        job["status"] = "failed"
        job["error"] = str(e)
    finally:
        job["finished_at"] = time.time()


@router.post("", status_code=202)
async def constructor_generate(body: ConstructorRequest):
    """AC-CONST-2: non-blocking constructor entry point.

    Returns HTTP 202 + ``job_id`` immediately. The actual pipeline
    runs in ``_run_constructor_job`` (FastAPI BackgroundTask) and
    updates ``_JOBS[job_id]``. Clients poll
    ``GET /api/constructor/jobs/{job_id}`` for status and download_url.

    Synchronous pre-flight (preserves the 4xx behaviour the old
    sync handler had — must fail loud, not 202+then-409):
      - slug validation (regex)
      - port preflight (409 on conflict)
    Only after these pass do we 202 + schedule the background job.
    """
    for slug in body.components:
        _validate_slug(slug, " in components list")
    # Pre-flight: every requested slug must exist in the registry graph.
    # Without this, the background job would fail asynchronously — the
    # user would see "running" for ~60s and then "failed" with a stack
    # trace, which is terrible UX. Fail loud and synchronously instead.
    missing_slugs = [s for s in body.components if s not in resolver.graph]
    if missing_slugs:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "unknown_slug",
                "message": (
                    f"Unknown component(s): {', '.join(missing_slugs)}. "
                    "Check the registry for available slugs."
                ),
                "missing": missing_slugs,
            },
        )

    # Port preflight: must be synchronous so port-conflict callers
    # still get an immediate 409, not a 202-then-failed-job.
    pre_resolved, _auto = resolver.resolve_with_metadata(body.components)
    pre_manifests_for_ports = _load_manifests(pre_resolved)
    pre_components_for_ports = [
        _ManifestComponent(s, pre_manifests_for_ports[s])
        for s in pre_resolved
        if s in pre_manifests_for_ports
    ]
    try:
        check_port_conflicts(pre_components_for_ports, body.configs)
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

    job_id = uuid.uuid4().hex[:12]
    _JOBS[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "components": body.components,
        "profile": body.profile,
        "fast_mode": body.fast_mode,
        "with_owasp": body.with_owasp,  # AC-CONST-4
        "started_at": time.time(),
        "errors": [],
    }
    # Fire-and-forget via a daemon thread instead of FastAPI
    # BackgroundTasks. Why: starlette's TestClient blocks until every
    # BackgroundTask returned by the handler finishes — which means
    # a unit test for "disjoint ports" (no port conflict) would wait
    # the entire pipeline duration. A daemon thread escapes that
    # wait. The trade-off: an unhandled exception inside the thread
    # is logged but never re-raised. The job stays in "pending"
    # state — pre-defense callers can see it as stuck, but the
    # real-production (uvicorn) path also uses BackgroundTasks
    # underneath a sync handler, so this is no worse than the old
    # sync code if the job ever deadlocks.
    thread = threading.Thread(
        target=_run_constructor_job,
        args=(job_id, body.model_dump()),
        daemon=True,
        name=f"constructor-job-{job_id}",
    )
    thread.start()
    return {
        "job_id": job_id,
        "status": "pending",
        "components": body.components,
        "profile": body.profile,
        "fast_mode": body.fast_mode,
        "with_owasp": body.with_owasp,  # AC-CONST-4
    }


@router.get("/jobs/{job_id}")
async def get_constructor_job(job_id: str):
    """AC-CONST-2: clients poll this every ~2s. When status ∈
    {ok, degraded}, the response includes ``download_url``."""
    job = _JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    body = {
        "job_id": job["job_id"],
        "status": job["status"],
        "components": job.get("components", []),
        "profile": job.get("profile", "standard"),
        "fast_mode": job.get("fast_mode", False),
        "with_owasp": job.get("with_owasp", True),  # AC-CONST-4
        "started_at": job.get("started_at"),
        "finished_at": job.get("finished_at"),
    }
    if job["status"] in ("ok", "degraded"):
        body["download_url"] = f"/api/constructor/jobs/{job_id}/download"
        body["stack_name"] = job.get("stack_name", "stack")
        body["errors"] = job.get("errors", [])
    if job.get("error"):
        body["error"] = job["error"]
    return body


@router.get("/jobs/{job_id}/download")
async def download_constructor_zip(job_id: str):
    """AC-CONST-2: streams the zip on demand. 409 if the job is
    still running, 404 if the job_id is unknown or the zip has
    been pruned from disk."""
    job = _JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    if job["status"] not in ("ok", "degraded"):
        raise HTTPException(
            status_code=409,
            detail=f"Job '{job_id}' is {job['status']!r}; not ready for download",
        )
    zip_path = Path(job.get("zip_path", ""))
    if not zip_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Zip file for job '{job_id}' has been pruned from disk",
        )
    return FileResponse(
        str(zip_path),
        media_type="application/zip",
        filename=f"gosdocker-{job.get('stack_name', 'stack')}.zip",
    )


@router.get("/profiles")
async def list_available_profiles():
    """List available security profiles."""
    return list_profiles()
