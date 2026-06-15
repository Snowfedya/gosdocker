"""ScanStep — generates SBOM (CycloneDX) via syft and Trivy vulnerability report."""
import json
import subprocess
import shutil
from datetime import datetime
from pathlib import Path
from .base import Step, PipelineContext


def _generate_sbom_manifest(manifest: dict, slug: str) -> dict:
    """Fallback: Generate CycloneDX SBOM JSON from manifest metadata (no syft)."""
    comp = manifest.get("component", {})
    now = datetime.utcnow().isoformat() + "Z"

    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {
            "timestamp": now,
            "tools": [{"vendor": "GosDocker", "name": "pipeline-scan", "version": "1.0.0"}],
            "component": {
                "type": "application",
                "name": slug,
                "version": comp.get("version", "unknown"),
                "description": comp.get("description", ""),
                "licenses": [],
                "externalReferences": [
                    {"type": "vcs", "url": comp.get("source_url", "")},
                    {"type": "website", "url": comp.get("documentation_url", "")},
                ],
            },
        },
        "components": [
            {"type": "file", "name": "Dockerfile", "version": "1.0",
             "description": f"Dockerfile for {slug}"}
        ],
        "dependencies": [{"ref": slug, "dependsOn": []}],
    }


def _generate_sbom_via_syft(source_dir: str, slug: str) -> dict | None:
    """Run syft on a source directory, return CycloneDX JSON dict.

    Falls back to None if syft not installed or fails.
    """
    if not shutil.which("syft"):
        return None

    try:
        result = subprocess.run(
            ["syft", "packages", f"dir:{source_dir}",
             "-o", "cyclonedx-json"],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0:
            sbom = json.loads(result.stdout)
            # Tag with generator info — handle CycloneDX 1.6 tools format:
            #   tools: [...]  (1.4-) or tools: {"components": [...]}  (1.6)
            tools_raw = sbom.get("metadata", {}).get("tools", [])
            if isinstance(tools_raw, dict):
                # CycloneDX 1.6: tools is an object with components array
                tools_list = tools_raw.setdefault("components", [])
            else:
                tools_list = tools_raw
            tools_list.append({
                "vendor": "GosDocker",
                "name": "pipeline-scan",
                "version": "1.0.0",
            })
            return sbom
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError) as e:
        pass

    return None


def _run_trivy_image(slug: str, work_dir: Path, fallback_image: str | None = None) -> str | None:
    """Run Trivy against the built image, falling back to source image.

    AC-2: When ``gosdocker/<slug>:latest`` was not built (build degraded),
    trivy cannot scan it. We fall back to the source image declared in the
    manifest (e.g. ``dh-mirror.gitverse.ru/riftbit/angie:latest``) so the
    scan still returns real CVE data on the actual upstream image the user
    would deploy.

    First checks if the Docker image exists — if not, returns None immediately
    instead of hanging for 320 seconds on a pull attempt.
    """
    trivy_path = shutil.which("trivy")
    if not trivy_path:
        return None

    # AC-2: pick scan target — built image if present, else manifest source
    target = _scan_target_for_slug(slug, fallback_image)
    if not target:
        return None

    # Check if the target image actually exists before trying to scan it
    try:
        img_check = subprocess.run(
            ["docker", "images", "-q", target],
            capture_output=True, text=True, timeout=15,
        )
        if not img_check.stdout.strip():
            return None  # Image doesn't exist — skip trivy image scan
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None

    trivy_out = work_dir / f"{slug}-trivy.json"
    try:
        result = subprocess.run(
            [trivy_path, "image", "--format=json", "--output", str(trivy_out),
             target, "--timeout", "5m"],
            capture_output=True, text=True, timeout=320,
        )
        if result.returncode == 0:
            return str(trivy_out)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return None


def _local_image_exists(image_ref: str) -> bool:
    """Return True if ``docker images`` lists the given ref locally.

    AC-2 helper. Tolerates docker errors (returns False, not raise) so the
    caller can fall back to the source image without a stack trace.
    """
    try:
        result = subprocess.run(
            ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return False
        refs = {line.strip() for line in (result.stdout or "").splitlines() if line.strip()}
        return image_ref in refs
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def _scan_target_for_slug(slug: str, fallback_image: str | None) -> str | None:
    """Pick the image trivy should scan.

    Priority:
    1. ``gosdocker/<slug>:latest`` — our built artifact (most accurate)
    2. ``fallback_image`` — manifest source image (e.g. upstream registry)
    3. None — no target, caller should skip
    """
    built = f"gosdocker/{slug}:latest"
    if _local_image_exists(built):
        return built
    if fallback_image and fallback_image.strip():
        return fallback_image.strip()
    return None


def _run_trivy_filesystem(slug: str, source_dir: str, work_dir: Path) -> str | None:
    """Run Trivy on source filesystem (no image needed)."""
    trivy_path = shutil.which("trivy")
    if not trivy_path:
        return None

    trivy_out = work_dir / f"{slug}-trivy.json"
    try:
        result = subprocess.run(
            [trivy_path, "fs", "--format=json", "--output", str(trivy_out),
             source_dir, "--timeout", "3m"],
            capture_output=True, text=True, timeout=200,
        )
        if result.returncode == 0:
            return str(trivy_out)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return None


def _generate_trivy_placeholder(slug: str, work_dir: Path) -> str:
    """Generate placeholder Trivy report when scanner unavailable."""
    placeholder = work_dir / f"{slug}-trivy-report.json"
    placeholder.write_text(json.dumps({
        "artifact": slug,
        "scanner": "aquasecurity/trivy (placeholder)",
        "vulnerabilities": [],
        "summary": {"critical": 0, "high": 0, "medium": 0, "low": 0},
        "note": "Install trivy and run: docker build -t gosdocker/{slug} . && trivy image gosdocker/{slug}",
    }, indent=2))
    return str(placeholder)


class ScanStep(Step):
    """Generates SBOM document and optionally runs Trivy vulnerability scan.

    SBOM:
      - Tries syft dir: on component source (real CycloneDX with dependencies)
      - Falls back to metadata-only manual SBOM if syft not installed
    Trivy:
      - Tries trivy image (needs Docker socket + built image)
      - Falls back to trivy fs (filesystem scan, no Docker needed)
      - Final fallback: placeholder JSON
    """

    name = "scan"

    def applicable(self, ctx: PipelineContext) -> bool:
        return True

    def execute(self, ctx: PipelineContext) -> None:
        slug = ctx.slug
        work_dir = ctx.work_dir
        work_dir.mkdir(parents=True, exist_ok=True)

        # Source directory for filesystem-based scanning
        source_dir = str(
            Path(__file__).parent.parent.parent / "registry" / slug
        )

        # 1. Generate CycloneDX SBOM (syft → fallback)
        sbom = _generate_sbom_via_syft(source_dir, slug) or _generate_sbom_manifest(ctx.manifest, slug)
        sbom_path = work_dir / f"{slug}-sbom.json"
        sbom_path.write_text(json.dumps(sbom, indent=2), encoding="utf-8")
        ctx.add_artifact("sbom", str(sbom_path))
        ctx.log(f"SBOM generated: {sbom_path.name} ({'syft' if 'syft' in json.dumps(sbom.get('metadata', {})) else 'metadata fallback'})")

        # 2. Try Trivy scan (image → fs → placeholder)
        # AC-2: pass manifest source image as fallback for image scan
        fallback_image = (ctx.manifest.get("component", {}).get("image", "") or "").strip()
        trivy_report = _run_trivy_image(slug, work_dir, fallback_image=fallback_image or None) \
                       or _run_trivy_filesystem(slug, source_dir, work_dir) \
                       or _generate_trivy_placeholder(slug, work_dir)
        ctx.add_artifact("trivy_report", trivy_report)
        ctx.log(f"Trivy report: {Path(trivy_report).name}")
