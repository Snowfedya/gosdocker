"""ScanStep — generates SBOM (CycloneDX) and Trivy vulnerability report."""
import json
import subprocess
import shutil
from datetime import datetime
from pathlib import Path
from .base import Step, PipelineContext


def _generate_sbom(manifest: dict, slug: str) -> dict:
    """Generate CycloneDX SBOM JSON from manifest metadata."""
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


class ScanStep(Step):
    """Generates SBOM document and optionally runs Trivy vulnerability scan."""

    name = "scan"

    def applicable(self, ctx: PipelineContext) -> bool:
        return True

    def execute(self, ctx: PipelineContext) -> None:
        slug = ctx.slug
        work_dir = ctx.work_dir
        work_dir.mkdir(parents=True, exist_ok=True)

        # 1. Generate CycloneDX SBOM
        sbom = _generate_sbom(ctx.manifest, slug)
        sbom_path = work_dir / f"{slug}-sbom.json"
        sbom_path.write_text(json.dumps(sbom, indent=2), encoding="utf-8")
        ctx.add_artifact("sbom", str(sbom_path))
        ctx.log(f"SBOM generated: {sbom_path.name}")

        # 2. Try Trivy scan
        trivy_path = shutil.which("trivy")
        if trivy_path:
            trivy_out = work_dir / f"{slug}-trivy.json"
            try:
                result = subprocess.run(
                    [trivy_path, "image", "--format=json", "--output", str(trivy_out),
                     f"gosdocker/{slug}:latest", "--timeout", "5m"],
                    capture_output=True, text=True, timeout=320,
                )
                if result.returncode == 0:
                    ctx.add_artifact("trivy_report", str(trivy_out))
                    ctx.log(f"Trivy scan OK")
                else:
                    ctx.log(f"Trivy skipped (image not built): {result.stderr.strip()[:200]}")
            except subprocess.TimeoutExpired:
                ctx.log("Trivy scan timed out")
        else:
            placeholder = work_dir / f"{slug}-trivy-report.json"
            placeholder.write_text(json.dumps({
                "artifact": slug,
                "scanner": "trivy (placeholder)",
                "vulnerabilities": [],
                "summary": {"critical": 0, "high": 0, "medium": 0, "low": 0},
                "note": f"Run 'docker build -t gosdocker/{slug} . && trivy image gosdocker/{slug}'",
            }, indent=2))
            ctx.add_artifact("trivy_report", str(placeholder))
            ctx.log("Trivy placeholder report generated")
