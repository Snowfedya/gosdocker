import json
from dataclasses import dataclass, field
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Any


@dataclass
class PipelineContext:
    """Context passed through pipeline steps. Carries manifest, profile, and results."""

    manifest: dict[str, Any]
    profile: str  # basic | standard | hardened
    work_dir: Path = field(default_factory=lambda: Path("/tmp/gosdocker-build"))
    artifacts: dict[str, str | None] = field(
        default_factory=lambda: {
            "dockerfile": None,
            "sbom": None,
            "trivy_report": None,
            "cosign_pub": None,
            "cosign_sig": None,
            "cosign_key": None,
            "owasp_report": None,
            "image_tar": None,
            "deploy_script": None,
        }
    )
    logs: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def log(self, msg: str) -> None:
        self.logs.append(msg)

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def add_artifact(self, key: str, path: str | Path) -> None:
        self.artifacts[key] = str(path)

    @property
    def slug(self) -> str:
        return self.manifest.get("component", {}).get("slug", "unknown")

    @property
    def component_name(self) -> str:
        return self.manifest.get("component", {}).get("name", self.slug)


class Step(ABC):
    """Abstract pipeline step. Override `applicable` and `execute`."""

    name: str = "step"

    @abstractmethod
    def applicable(self, ctx: PipelineContext) -> bool:
        """Return False to skip this step for this component."""
        ...

    @abstractmethod
    def execute(self, ctx: PipelineContext) -> None:
        """Run the step. Mutate ctx.artifacts and ctx.logs."""
        ...


class Pipeline:
    """Orchestrates a sequence of Steps for one component."""

    def __init__(self, steps: list[Step]):
        self.steps = steps

    def run(
        self,
        manifest: dict[str, Any],
        profile: str = "standard",
        work_dir: Path | None = None,
    ) -> PipelineContext:
        """Run all applicable steps in order. Returns PipelineContext with artifacts."""
        ctx = PipelineContext(
            manifest=manifest,
            profile=profile,
            work_dir=work_dir or Path("/tmp/gosdocker-build") / manifest.get("component", {}).get("slug", "unknown"),
        )
        ctx.log(f"Pipeline start: {ctx.slug} @ {profile}")
        for step in self.steps:
            if not step.applicable(ctx):
                ctx.log(f"  Skip {step.name}: not applicable")
                continue
            ctx.log(f"  Run {step.name}...")
            try:
                step.execute(ctx)
                ctx.log(f"  {step.name} OK")
            except Exception as e:
                ctx.error(f"{step.name} FAILED: {e}")
                break
        ctx.log(f"Pipeline done: {len(ctx.errors)} error(s)")
        return ctx
