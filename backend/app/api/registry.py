"""Registry API — browse component manifests, download Dockerfiles and artifacts."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path

from app.pipeline import Pipeline, BuildStep, ScanStep, PackageStep, RegisterStep

router = APIRouter(prefix="/api/registry", tags=["registry"])

REGISTRY_DIR = Path(__file__).parent.parent.parent / "registry"
REGISTRY_BASE = Path(__file__).parent.parent.parent / "registry"


def _list_registry_components() -> list[str]:
    """Scan registry directory for component slugs."""
    if not REGISTRY_BASE.exists():
        return []
    return sorted(d.name for d in REGISTRY_BASE.iterdir() if d.is_dir() and (d / "manifest.yml").exists())


def _load_manifest(slug: str) -> dict | None:
    """Load and parse manifest.yml for a component slug."""
    import yaml
    manifest_path = REGISTRY_BASE / slug / "manifest.yml"
    if not manifest_path.exists():
        return None
    return yaml.safe_load(manifest_path.read_text())


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
    """Get full component manifest."""
    manifest = _load_manifest(slug)
    if not manifest:
        raise HTTPException(status_code=404, detail=f"Component '{slug}' not found in registry")
    return manifest


@router.get("/{slug}/dockerfile")
async def get_dockerfile(slug: str):
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
    """Get raw manifest.yml content as text."""
    manifest_path = REGISTRY_BASE / slug / "manifest.yml"
    if not manifest_path.exists():
        raise HTTPException(status_code=404, detail=f"Manifest for '{slug}' not found")
    return FileResponse(
        str(manifest_path),
        media_type="text/plain",
        filename=f"{slug}-manifest.yml",
    )


@router.get("/{slug}/build")
async def run_pipeline(slug: str, profile: str = "standard"):
    """Run the pipeline for a component and return its build context."""
    manifest = _load_manifest(slug)
    if not manifest:
        raise HTTPException(status_code=404, detail=f"Component '{slug}' not found")

    pipeline = Pipeline([BuildStep(), ScanStep(), PackageStep(), RegisterStep()])
    ctx = pipeline.run(manifest, profile=profile)

    return {
        "slug": slug,
        "profile": profile,
        "status": "ok" if not ctx.errors else "error",
        "errors": ctx.errors,
        "artifacts": {k: v for k, v in ctx.artifacts.items() if v is not None},
        "logs": ctx.logs[-5:],  # last 5 log entries
    }
