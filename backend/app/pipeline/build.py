"""BuildStep — registers Dockerfile path for build: directive in compose."""
from .base import Step, PipelineContext


class BuildStep(Step):
    """Records the path to the component's Dockerfile for compose build: directive."""

    name = "build"

    def applicable(self, ctx: PipelineContext) -> bool:
        """All components have a Dockerfile — always applicable."""
        return True

    def execute(self, ctx: PipelineContext) -> None:
        slug = ctx.slug
        dockerfile_path = f"registry/{slug}/Dockerfile"
        ctx.add_artifact("dockerfile", dockerfile_path)
        manifest = ctx.manifest.get("component", {})
        ctx.log(f"Dockerfile: {dockerfile_path}")
        ctx.log(f"Build method: {manifest.get('build_method', 'unknown')}")
        ctx.log(f"Source URL: {manifest.get('source_url', 'none')}")
