"""SignStep — signs Docker images with Cosign using key-pair mode.

Generates a Cosign key pair (if one doesn't exist for this component) and
signs the built image tar with `cosign sign-blob`. The public key and
signature are exported for verification in air-gapped environments.

Requires:
  - cosign binary installed and in PATH
  - (optional) Docker image tar for sign-blob
"""
import os
import subprocess
import shutil
from pathlib import Path
from .base import Step, PipelineContext


class SignStep(Step):
    """Generates Cosign key pair and signs the Docker image tar.

    Artifacts:
      cosign_key  — private key (for signing, keep secure)
      cosign_pub  — public key (for verification by consumer)
      cosign_sig  — signature blob
    """

    name = "sign"

    def applicable(self, ctx: PipelineContext) -> bool:
        """Only applicable if cosign is installed."""
        return bool(shutil.which("cosign"))

    def execute(self, ctx: PipelineContext) -> None:
        slug = ctx.slug
        work_dir = ctx.work_dir
        work_dir.mkdir(parents=True, exist_ok=True)

        key_path = work_dir / f"{slug}.key"
        pub_path = work_dir / f"{slug}.pub"
        # Read Cosign password from environment or generate a random one for CI
        # IMPORTANT: For production government use, always set COSIGN_PASSWORD=<strong-password>
        cosign_password = os.environ.get("COSIGN_PASSWORD", os.urandom(32).hex())
        env = {**os.environ, "COSIGN_PASSWORD": cosign_password}

        # 1. Generate key pair if not exists
        if not key_path.exists():
            try:
                result = subprocess.run(
                    ["cosign", "generate-key-pair",
                     "--output-key-prefix", str(work_dir / slug)],
                    capture_output=True, text=True, timeout=30,
                    env=env,
                )
                if result.returncode == 0:
                    ctx.log(f"Cosign key pair generated: {key_path.name}")
                else:
                    ctx.log(f"Cosign key generation skipped: {result.stderr.strip()[:200]}")
                    return
            except (FileNotFoundError, subprocess.TimeoutExpired) as e:
                ctx.log(f"Cosign key generation failed: {e}")
                return
        else:
            ctx.log(f"Cosign key pair already exists")

        # 2. Sign the image tar (if exists)
        image_tar = work_dir / f"{slug}.tar"
        sig_path = work_dir / f"{slug}-cosign.sig"

        if image_tar.exists():
            ctx.log(f"Signing image tar: {image_tar.name} ({image_tar.stat().st_size / 1024 / 1024:.0f} MB)")
            try:
                sig_result = subprocess.run(
                    ["cosign", "sign-blob", "--key", str(key_path),
                     "--bundle", str(sig_path),
                     str(image_tar)],
                    capture_output=True, text=True, timeout=60,
                    env=env,
                )
                if sig_result.returncode == 0:
                    ctx.add_artifact("cosign_key", str(key_path))
                    ctx.add_artifact("cosign_pub", str(pub_path))
                    ctx.add_artifact("cosign_sig", str(sig_path))
                    ctx.log(f"Image tar signed: {sig_path.name}")
                else:
                    # Fallback: try old --output-signature flag for older cosign
                    fallback = subprocess.run(
                        ["cosign", "sign-blob", "--key", str(key_path),
                         "--output-signature", str(sig_path),
                         str(image_tar)],
                        capture_output=True, text=True, timeout=60, env=env,
                    )
                    if fallback.returncode == 0:
                        ctx.add_artifact("cosign_key", str(key_path))
                        ctx.add_artifact("cosign_pub", str(pub_path))
                        ctx.add_artifact("cosign_sig", str(sig_path))
                        ctx.log(f"Image tar signed (legacy flag): {sig_path.name}")
                    else:
                        ctx.log(f"Cosign sign-blob failed: {sig_result.stderr.strip()[:200]}")
            except (FileNotFoundError, subprocess.TimeoutExpired) as e:
                ctx.log(f"Cosign sign-blob error: {e}")
        else:
            ctx.log("No image tar found — cosign signing deferred (build first)")
            # Still export keys so they can be used later
            if key_path.exists() and pub_path.exists():
                ctx.add_artifact("cosign_key", str(key_path))
                ctx.add_artifact("cosign_pub", str(pub_path))
