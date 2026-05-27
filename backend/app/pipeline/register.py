"""RegisterStep — updates component registry metadata with build results."""
import json
from pathlib import Path
from datetime import datetime
from .base import Step, PipelineContext


class RegisterStep(Step):
    """Records pipeline execution results into registry metadata artifact."""

    name = "register"

    def applicable(self, ctx: PipelineContext) -> bool:
        return True

    def execute(self, ctx: PipelineContext) -> None:
        slug = ctx.slug
        work_dir = ctx.work_dir
        work_dir.mkdir(parents=True, exist_ok=True)

        registry_entry = {
            "slug": slug,
            "name": ctx.component_name,
            "pipeline_run": datetime.utcnow().isoformat(),
            "profile": ctx.profile,
            "artifacts": {k: v for k, v in ctx.artifacts.items() if v is not None},
            "log_count": len(ctx.logs),
            "error_count": len(ctx.errors),
            "build_method": ctx.manifest.get("component", {}).get("build_method", ""),
            "version": ctx.manifest.get("component", {}).get("version", ""),
        }

        registry_path = work_dir / f"{slug}-registry.json"
        registry_path.write_text(json.dumps(registry_entry, indent=2), encoding="utf-8")
        ctx.log(f"Registry entry saved: {registry_path.name}")
