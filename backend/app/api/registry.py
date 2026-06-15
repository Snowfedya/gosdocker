"""Registry API — browse component manifests, build, and fetch security reports."""
import json
import re
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.responses import FileResponse

from app.pipeline import (
    Pipeline, BuildStep, ScanStep, PackageStep, RegisterStep,
    SignStep, DependencyCheckStep,
)

router = APIRouter(prefix="/api/registry", tags=["registry"])

REGISTRY_DIR = Path(__file__).parent.parent.parent / "registry"
REGISTRY_BASE = REGISTRY_DIR
REPORTS_DIR = Path("/tmp/gosdocker-reports")

# Single pipeline instance — same as constructor
_PIPELINE = Pipeline([
    BuildStep(),
    ScanStep(),
    PackageStep(),
    SignStep(),
    RegisterStep(),
    DependencyCheckStep(),  # runs last — can timeout without blocking the critical path
])

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,60}[a-z0-9]$")

def _validate_slug(slug: str) -> str:
    """Validate component slug against safe pattern to prevent path traversal."""
    if not _SLUG_RE.match(slug):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid slug '{slug}'. Must match [a-z0-9][a-z0-9-]{{0,60}}[a-z0-9]",
        )
    return slug


def _list_registry_components() -> list[str]:
    """Scan registry directory for component slugs."""
    if not REGISTRY_BASE.exists():
        return []
    return sorted(d.name for d in REGISTRY_BASE.iterdir()
                  if d.is_dir() and (d / "manifest.yml").exists())


def _load_manifest(slug: str) -> dict | None:
    """Load and parse manifest.yml for a component slug.

    AC-2 helper: enrich the manifest with ``component.image`` sourced
    from the Component table (``registry_url`` field), so ScanStep can
    fall back to scanning the upstream image when our built artifact
    is not present.
    """
    import yaml
    manifest_path = REGISTRY_BASE / slug / "manifest.yml"
    if not manifest_path.exists():
        return None
    manifest = yaml.safe_load(manifest_path.read_text())
    if not isinstance(manifest, dict):
        return None

    # AC-2: merge image from DB so ScanStep can fallback on source image.
    # Run in a dedicated thread to avoid clashes with any event loop
    # that may already be running (pytest-asyncio, FastAPI handlers, etc).
    try:
        from app.database import async_session
        from sqlalchemy import select
        from app.models import Component
        import asyncio

        async def _fetch_image() -> str | None:
            async with async_session() as s:
                r = await s.execute(
                    select(Component.registry_url).where(Component.slug == slug)
                )
                return r.scalar_one_or_none()

        container: dict[str, Any] = {}

        def _runner() -> None:
            try:
                container["url"] = asyncio.run(_fetch_image())
            except Exception as e:  # pragma: no cover - defensive
                container["error"] = str(e)

        import threading
        t = threading.Thread(target=_runner, daemon=True)
        t.start()
        t.join(timeout=5)
        registry_url = container.get("url")
        if registry_url:
            comp = manifest.setdefault("component", {})
            comp.setdefault("image", registry_url)
    except Exception:
        pass
    return manifest


def _parse_sbom_summary(sbom_path: Path) -> dict:
    """Extract a summary from CycloneDX SBOM."""
    try:
        data = json.loads(sbom_path.read_text())
        components = data.get("components", [])
        # Count by type
        type_counts: dict[str, int] = {}
        top_deps: list[dict] = []
        for c in components:
            t = c.get("type", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1
            name = c.get("name", "?")
            ver = c.get("version", "")
            if len(top_deps) < 30:
                top_deps.append({"name": name, "version": ver, "type": t})
        tool_names = []
        tools_raw = data.get("metadata", {}).get("tools", {})
        if isinstance(tools_raw, dict):
            for tool in tools_raw.get("components", []):
                if isinstance(tool, dict):
                    tool_names.append(tool.get("name", "?"))
        elif isinstance(tools_raw, list):
            for tool in tools_raw:
                if isinstance(tool, dict):
                    tool_names.append(tool.get("name", "?"))
        return {
            "total_components": len(components),
            "by_type": type_counts,
            "top_dependencies": top_deps,
            "tools": tool_names,
            "bom_format": data.get("bomFormat", ""),
            "spec_version": data.get("specVersion", ""),
        }
    except Exception as e:
        return {"error": str(e), "total_components": 0, "by_type": {}, "top_dependencies": [], "tools": []}


def _parse_trivy_summary(trivy_path: Path) -> dict:
    """Extract vulnerability summary from Trivy JSON report."""
    try:
        data = json.loads(trivy_path.read_text())
        results = data.get("results", [])
        total_vulns = 0
        severity_counts: dict[str, int] = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNKNOWN": 0}
        vuln_list: list[dict] = []
        for result in results:
            vulns = result.get("vulnerabilities", [])
            for v in vulns:
                sev = v.get("Severity", "UNKNOWN").upper()
                if sev in severity_counts:
                    severity_counts[sev] += 1
                total_vulns += 1
                if len(vuln_list) < 50:
                    vuln_list.append({
                        "id": v.get("VulnerabilityID", ""),
                        "pkg": v.get("PkgName", ""),
                        "severity": sev,
                        "title": v.get("Title", "")[:80],
                        "fixed": v.get("FixedVersion", ""),
                    })
        return {
            "total_vulnerabilities": total_vulns,
            "by_severity": severity_counts,
            "vulnerabilities": vuln_list,
        }
    except Exception as e:
        return {"error": str(e), "total_vulnerabilities": 0, "by_severity": {}, "vulnerabilities": []}


def _parse_owasp_summary(owasp_path: Path) -> dict:
    """Extract summary from OWASP Dependency-Check report."""
    try:
        data = json.loads(owasp_path.read_text())
        dependencies = data.get("dependencies", [])
        total_deps = len(dependencies)
        vuln_count = 0
        sev_counts: dict[str, int] = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for dep in dependencies:
            for v in dep.get("vulnerabilities", []):
                vuln_count += 1
                sev = v.get("severity", "LOW").upper()
                if sev in sev_counts:
                    sev_counts[sev] += 1
        return {
            "total_dependencies": total_deps,
            "total_vulnerabilities": vuln_count,
            "by_severity": sev_counts,
        }
    except Exception as e:
        return {"error": str(e), "total_dependencies": 0, "total_vulnerabilities": 0}


def _build_report_from_context(slug: str, profile: str, artifacts: dict, errors: list) -> dict:
    """Build a structured security report from pipeline artifacts.

    AC-1: distinguishes degraded mode (build skipped, no artifacts) from
    a successful scan. Returns ``status: "degraded"`` and ``degraded: True``
    when no file artifacts were produced, so the UI cannot display a
    false-positive "A 100 / 0 vulnerabilities" green badge.
    """
    # ── Step 1: collect flags + file paths separately ──────────────────
    flags: dict[str, Any] = {}
    for art_key, art_value in artifacts.items():
        if isinstance(art_value, bool):
            flags[art_key] = art_value

    degraded = bool(flags.get("build_degraded", False)) or not _any_file_artifact(artifacts)
    trivy_skipped = bool(flags.get("trivy_skipped", False)) or degraded

    # ── Step 2: initialise report skeleton with degraded fields ────────
    report: dict = {
        "slug": slug,
        "profile": profile,
        "status": "degraded" if degraded else ("error" if errors else "ok"),
        "degraded": degraded,
        "trivy_skipped": trivy_skipped,
        "errors": errors,
        "sbom": None,
        "trivy": None,
        "owasp": None,
        "cosign": {"signed": False, "public_key": None, "signature": None},
    }

    # ── Step 3: ingest path-typed artifacts (skip non-string/Path) ────
    for art_key, art_path_str in artifacts.items():
        if not isinstance(art_path_str, (str, Path)):
            continue
        art_path = Path(art_path_str)
        if not art_path.exists():
            continue

        if art_key == "sbom":
            summary = _parse_sbom_summary(art_path)
            report["sbom"] = summary
        elif art_key == "trivy_report":
            summary = _parse_trivy_summary(art_path)
            summary["trivy_skipped"] = False
            report["trivy"] = summary
        elif art_key == "owasp_report":
            summary = _parse_owasp_summary(art_path)
            report["owasp"] = summary
        elif art_key == "cosign_sig":
            report["cosign"]["signature"] = str(art_path)
            report["cosign"]["signed"] = True
        elif art_key == "cosign_pub":
            report["cosign"]["public_key"] = str(art_path)

    # ── Step 4: when trivy didn't run, leave explicit marker ──────────
    if report["trivy"] is None and trivy_skipped:
        report["trivy"] = {
            "total_vulnerabilities": 0,
            "by_severity": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNKNOWN": 0},
            "vulnerabilities": [],
            "trivy_skipped": True,
        }

    return report


def _any_file_artifact(artifacts: dict) -> bool:
    """Return True if at least one path-typed artifact exists on disk."""
    for art_value in artifacts.values():
        if isinstance(art_value, (str, Path)):
            try:
                if Path(art_value).exists():
                    return True
            except OSError:
                continue
    return False


def _save_report_cache(slug: str, report: dict):
    """Cache the latest report to disk for later retrieval."""
    cache_dir = REPORTS_DIR / slug
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / "latest.json").write_text(json.dumps(report, indent=2, default=str))


def _load_report_cache(slug: str) -> dict | None:
    """Load cached report, or None if not found / stale.

    AC-3: if the manifest mtime is newer than the cache mtime, the
    cache is treated as stale and ``None`` is returned — the caller
    (GET /reports) should re-trigger a build or return 404 to prompt
    the UI to do so. Without this, an unchanged report with stale
    "0 vulns" could persist for hours after the manifest changes.
    """
    cache_file = REPORTS_DIR / slug / "latest.json"
    if not cache_file.exists():
        return None
    # AC-3: invalidate cache when manifest mtime > cache mtime
    manifest_path = REGISTRY_BASE / slug / "manifest.yml"
    if manifest_path.exists():
        try:
            if manifest_path.stat().st_mtime > cache_file.stat().st_mtime:
                return None
        except OSError:
            pass
    try:
        return json.loads(cache_file.read_text())
    except (json.JSONDecodeError, OSError):
        return None


# ── API Routes ───────────────────────────────────────────────────────


@router.get("")
async def list_registry():
    """List all components in the registry with their manifest overview."""
    components = []
    for slug in _list_registry_components():
        manifest = _load_manifest(slug)
        if manifest:
            comp = manifest.get("component", {})
            components.append({
                "slug": slug,
                "name": comp.get("name", slug),
                "version": comp.get("version", ""),
                "category": comp.get("category", ""),
                "description": comp.get("description", ""),
                "build_method": comp.get("build_method", ""),
                "provides": comp.get("dependencies", {}).get("provides", []),
                "has_dockerfile": (REGISTRY_BASE / slug / "Dockerfile").exists(),
                "source_url": comp.get("source_url", ""),
                "community_url": comp.get("community_url", None),
            })
    return components


@router.get("/{slug}")
async def get_registry_component(slug: str):
    _validate_slug(slug)
    """Get full component manifest."""
    manifest = _load_manifest(slug)
    if not manifest:
        raise HTTPException(status_code=404, detail=f"Component '{slug}' not found in registry")
    return manifest


@router.get("/{slug}/dockerfile")
async def get_dockerfile(slug: str):
    _validate_slug(slug)
    """Download the Dockerfile for a component."""
    dockerfile_path = REGISTRY_BASE / slug / "Dockerfile"
    if not dockerfile_path.exists():
        raise HTTPException(status_code=404, detail=f"Dockerfile for '{slug}' not found")
    return FileResponse(
        str(dockerfile_path),
        media_type="text/plain",
        filename=f"{slug}.Dockerfile",
    )


@router.get("/{slug}/manifest")
async def get_manifest_raw(slug: str):
    _validate_slug(slug)
    """Get raw manifest.yml content as text."""
    manifest_path = REGISTRY_BASE / slug / "manifest.yml"
    if not manifest_path.exists():
        raise HTTPException(status_code=404, detail=f"Manifest for '{slug}' not found")
    return FileResponse(
        str(manifest_path),
        media_type="text/plain",
        filename=f"{slug}-manifest.yml",
    )


# AC-4: in-memory job store. Keyed by job_id, holds status / report / timing.
# Production deployment should swap this for Redis or a DB-backed queue;
# the single-process uvicorn in this prototype keeps the model in-process.
_JOBS: dict[str, dict[str, Any]] = {}


def _run_pipeline_job(slug: str, profile: str, job_id: str) -> None:
    """Background job: run pipeline, save report, update job status.

    AC-4: invoked by FastAPI BackgroundTasks, executes the previously
    synchronous pipeline off the request thread. Updates ``_JOBS[job_id]``
    with status transitions: pending → running → ok | degraded | failed.
    """
    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    job = _JOBS[job_id]
    job["status"] = "running"
    manifest = _load_manifest(slug)
    if not manifest:
        job["status"] = "failed"
        job["error"] = f"Component '{slug}' not found in registry"
        job["finished_at"] = time.time()
        return

    work_dir = Path("/tmp/gosdocker-constructor") / slug
    executor = ThreadPoolExecutor(max_workers=2)

    def _run() -> Any:
        return _PIPELINE.run(manifest, profile=profile, work_dir=work_dir)

    try:
        loop = asyncio.new_event_loop()
        try:
            ctx = loop.run_until_complete(loop.run_in_executor(executor, _run))
        finally:
            loop.close()
        report = _build_report_from_context(slug, profile, ctx.artifacts, ctx.errors)
        _save_report_cache(slug, report)
        job["status"] = report["status"]
        job["report"] = report
    except Exception as e:  # pragma: no cover - defensive
        job["status"] = "failed"
        job["error"] = str(e)
    finally:
        job["finished_at"] = time.time()


@router.post("/{slug}/build", status_code=202)
async def run_pipeline(
    slug: str,
    background: BackgroundTasks,
    profile: str = Query("standard", description="Security profile: basic, standard, or hardened"),
):
    _validate_slug(slug)
    """Run the security pipeline for a component asynchronously.

    AC-4: returns HTTP 202 + job_id immediately; the actual pipeline
    runs in a FastAPI BackgroundTask and updates ``_JOBS[job_id]``.
    Clients poll ``GET /api/registry/{slug}/jobs/{job_id}`` for status.
    """
    if not _load_manifest(slug):
        raise HTTPException(status_code=404, detail=f"Component '{slug}' not found in registry")

    job_id = uuid.uuid4().hex[:12]
    _JOBS[job_id] = {
        "slug": slug,
        "job_id": job_id,
        "profile": profile,
        "status": "pending",
        "started_at": time.time(),
    }
    background.add_task(_run_pipeline_job, slug, profile, job_id)
    return {"job_id": job_id, "status": "pending", "slug": slug, "profile": profile}


@router.get("/{slug}/jobs/{job_id}")
async def get_job(slug: str, job_id: str):
    """Return the current status of a pipeline job.

    AC-4: UI polls this every 2s after POST /build; when status ∈
    {ok, degraded, failed}, the ``report`` field is included and the
    client can stop polling.
    """
    job = _JOBS.get(job_id)
    if not job or job.get("slug") != slug:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found for '{slug}'")
    response = {
        "job_id": job["job_id"],
        "slug": job["slug"],
        "profile": job.get("profile", "standard"),
        "status": job["status"],
        "started_at": job.get("started_at"),
        "finished_at": job.get("finished_at"),
    }
    if job["status"] in ("ok", "degraded", "failed") and "report" in job:
        response["report"] = job["report"]
    if job.get("error"):
        response["error"] = job["error"]
    return response


@router.get("/{slug}/reports")
async def get_reports(slug: str):
    _validate_slug(slug)
    """Fetch the latest cached security report for a component.

    Returns 404 if no build has been run yet.
    """
    report = _load_report_cache(slug)
    if report is None:
        raise HTTPException(
            status_code=404,
            detail=f"No security report found for '{slug}'. Run POST /api/registry/{slug}/build first.",
        )
    return report
