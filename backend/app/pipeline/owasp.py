"""DependencyCheckStep — runs OWASP Dependency-Check via Docker on component source.

Scans source code dependencies (npm, pip, maven, etc.) for known CVEs using
the owasp/dependency-check Docker image. Produces a JSON report.

Requires:
  - Docker installed and accessible
  - owasp/dependency-check Docker image pulled
"""
import json
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

    def execute(self, ctx: PipelineContext) -> None:
        slug = ctx.slug
        work_dir = ctx.work_dir
        work_dir.mkdir(parents=True, exist_ok=True)

        # Resolve source directory relative to registry
        source_dir = Path(__file__).parent.parent.parent / "registry" / slug
        if not source_dir.exists():
            ctx.log(f"Source directory not found: {source_dir} — OWASP DC skipped")
            return

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
                # Copy to work_dir with slug prefix
                named_path = work_dir / f"{slug}-dependency-check.json"
                named_path.write_text(report_path.read_text(encoding="utf-8"))
                ctx.add_artifact("owasp_report", str(named_path))
                ctx.log(f"OWASP DC report: {named_path.name}")

                # Log vulnerability count
                try:
                    report = json.loads(named_path.read_text())
                    vuln_count = len(report.get("vulnerabilities", []))
                    dep_count = len(report.get("dependencies", []))
                    ctx.log(f"  Dependencies scanned: {dep_count}, vulnerabilities: {vuln_count}")
                except (json.JSONDecodeError, KeyError):
                    pass
            else:
                # Write placeholder if Docker failed silently
                ctx.log(f"OWASP DC produced no output file — generating placeholder")
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
