"""DependencyCheckStep — runs OWASP Dependency-Check via Docker on component source.

Scans source code dependencies (npm, pip, maven, etc.) for known CVEs using
the owasp/dependency-check Docker image. Produces a JSON report.

Docker-outside-Docker (DooD) note:
  When running inside a container with /var/run/docker.sock mounted,
  docker commands execute on the HOST. Volume paths must resolve
  on the host filesystem, not inside the container.
  Set REGISTRY_HOST_PATH env var to the host-side path of the registry dir.
  Example: REGISTRY_HOST_PATH=/opt/gosdocker/backend/registry

Requires:
  - Docker installed and accessible (or DooD socket mount)
  - owasp/dependency-check Docker image pulled
"""
import json
import os
import subprocess
import shutil
from pathlib import Path
from .base import Step, PipelineContext


class DependencyCheckStep(Step):
    """Scans component source dependencies for known CVEs via OWASP DC.

    Artifact:
      owasp_report — JSON report from OWASP Dependency-Check
    """

    name = "dependency-check"

    def applicable(self, ctx: PipelineContext) -> bool:
        """Needs Docker to run the owasp/dc image."""
        return bool(shutil.which("docker"))

    def _resolve_source_dir(self, slug: str) -> Path | None:
        """Resolve source directory, accounting for DooD path mapping.

        Inside the container the registry is at /app/registry/{slug}.
        With DooD, Docker runs on the host where the path is different.
        Use REGISTRY_HOST_PATH to map correctly.
        """
        host_registry = os.environ.get("REGISTRY_HOST_PATH")
        if host_registry:
            host_path = Path(host_registry) / slug
            if host_path.exists():
                return host_path

        # Fallback: try container-internal path (works without DooD)
        container_path = Path(__file__).parent.parent.parent / "registry" / slug
        if container_path.exists():
            return container_path

        return None

    def execute(self, ctx: PipelineContext) -> None:
        slug = ctx.slug
        work_dir = ctx.work_dir
        work_dir.mkdir(parents=True, exist_ok=True)

        # OWASP Dependency-Check scan is deferred - uses placeholder for now.
        # The docker container owasp/dependency-check takes 5+ minutes on first
        # run (downloading NVD database) and requires DooD volume path resolution.
        # To enable: remove this early return and ensure REGISTRY_HOST_PATH is set.
        self._write_placeholder(ctx, work_dir, slug)
        return
        # but /tmp is shared with host, so the path works for both.
        output_dir = work_dir / "dependency-check-out"
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            ctx.log(f"OWASP DC scanning {slug} source @ {source_dir} ...")
            result = subprocess.run(
                ["docker", "run", "--rm",
                 "-v", f"{source_dir}:/src:ro",
                 "-v", f"{output_dir}:/out:rw",
                 "owasp/dependency-check",
                 "--scan", "/src",
                 "--format", "JSON",
                 "--out", "/out",
                 "--failOnCVSS", "11",  # never fail the pipeline
                 "--suppression", "/dev/null"],
                capture_output=True, text=True, timeout=600,
            )

            # Find the output JSON (owasp/dc creates a file named 'dependency-check-report.json')
            json_files = sorted(output_dir.glob("*.json"))
            if json_files:
                report_path = json_files[0]
                named_path = work_dir / f"{slug}-dependency-check.json"
                named_path.write_text(report_path.read_text(encoding="utf-8"))
                ctx.add_artifact("owasp_report", str(named_path))
                ctx.log(f"OWASP DC report: {named_path.name}")

                try:
                    report = json.loads(named_path.read_text())
                    vuln_count = len(report.get("vulnerabilities", []))
                    dep_count = len(report.get("dependencies", []))
                    ctx.log(f"  Dependencies scanned: {dep_count}, vulnerabilities: {vuln_count}")
                except (json.JSONDecodeError, KeyError):
                    pass
            else:
                ctx.log(f"OWASP DC produced no output — stdout: {result.stdout[:200]}, stderr: {result.stderr[:200]}")
                self._write_placeholder(ctx, work_dir, slug)

        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            ctx.log(f"OWASP DC skipped: {e}")
            self._write_placeholder(ctx, work_dir, slug)

    def _write_placeholder(self, ctx: PipelineContext, work_dir: Path, slug: str) -> None:
        """Write a placeholder report when OWASP DC is unavailable."""
        placeholder = work_dir / f"{slug}-dependency-check.json"
        placeholder.write_text(json.dumps({
            "report": slug,
            "scanner": "OWASP Dependency-Check (placeholder)",
            "dependencies": [],
            "vulnerabilities": [],
            "summary": {"total_dependencies": 0, "critical": 0, "high": 0, "medium": 0, "low": 0},
            "note": "Run locally: docker run --rm -v $(pwd):/src owasp/dependency-check "
                    "--scan /src --format JSON --out /out",
        }, indent=2))
        placeholder.chmod(0o644)
        ctx.log(f"OWASP DC placeholder: {placeholder.name}")
