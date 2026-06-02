"""BuildStep — builds Docker image from component source code.

Downloads source tarball and builds the image using the component's
Dockerfile, producing gosdocker/{slug}:latest for downstream steps
(Trivy image scan, docker save, Cosign sign-blob).
"""
import subprocess
import shutil
from pathlib import Path
from .base import Step, PipelineContext


class BuildStep(Step):
    """Builds the Docker image for the component.

    Artifacts:
      docker_image — image tag (gosdocker/{slug}:latest) on success
      dockerfile   — relative path to the used Dockerfile
    """

    name = "build"

    def applicable(self, ctx: PipelineContext) -> bool:
        """Needs Docker to build."""
        return bool(shutil.which("docker"))

    def execute(self, ctx: PipelineContext) -> None:
        slug = ctx.slug
        registry_path = Path(__file__).parent.parent.parent / "registry" / slug
        dockerfile = registry_path / "Dockerfile"

        if not registry_path.exists():
            ctx.log(f"Registry directory not found: {registry_path} — skipping build")
            return
        if not dockerfile.exists():
            ctx.log(f"Dockerfile not found: {dockerfile} — skipping build")
            return

        image_tag = f"gosdocker/{slug}:latest"
        ctx.log(f"Building Docker image {image_tag} from {dockerfile} ...")

        try:
            result = subprocess.run(
                ["docker", "build", "-t", image_tag,
                 "-f", str(dockerfile),
                 str(registry_path)],
                capture_output=True, text=True, timeout=600,
            )
            if result.returncode == 0:
                ctx.add_artifact("dockerfile", f"registry/{slug}/Dockerfile")
                ctx.add_artifact("docker_image", image_tag)
                ctx.log(f"Docker image built successfully: {image_tag}")
            else:
                ctx.log(f"Docker build failed (exit {result.returncode}): "
                        f"{result.stderr.strip()[:500]}")
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            ctx.log(f"Docker build error: {e}")
