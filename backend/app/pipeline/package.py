"""PackageStep — creates air-gapped deployment package: tar + deploy.sh."""
import subprocess
from pathlib import Path
from datetime import datetime
from .base import Step, PipelineContext


_DEPLOY_SH = """#!/bin/sh
# GosDocker Deployment Script — Air-Gapped Mode with Security Verification
# Component: {name} ({slug})
# Generated: {timestamp}
set -e

echo "=== GosDocker: {name} Deployment ==="
echo "Component: {slug}"
echo ""

if ! command -v docker >/dev/null 2>&1; then
    echo "ERROR: Docker not found. Install Docker first."
    exit 1
fi

IMAGE_TAR="{slug}.tar"
SEC_DIR="security/{slug}"

if [ -f "$IMAGE_TAR" ]; then
    echo "[1/3] Verifying image signature..."
    COSIGN_PUB="$SEC_DIR/{slug}-cosign.pub"
    COSIGN_SIG="$SEC_DIR/{slug}-cosign.sig"
    if [ -f "$COSIGN_PUB" ] && [ -f "$COSIGN_SIG" ]; then
        if command -v cosign >/dev/null 2>&1; then
            cosign verify-blob --key "$COSIGN_PUB" --signature "$COSIGN_SIG" "$IMAGE_TAR" && \\
                echo "  ✓ Signature verified" || \\
                echo "  ⚠ Signature verification FAILED — image may be tampered with!"
        else
            echo "  ⚠ cosign not found — install from https://sigstore.dev to verify"
        fi
    else
        echo "  - No signature found for verification"
    fi
    echo "Loading Docker image..."
    docker load -i "$IMAGE_TAR"
    echo "  Image loaded."
else
    echo "[1/3] No pre-built image found. Build from source:"
    echo "  docker build -t gosdocker/{slug} -f {slug}/Dockerfile {slug}/"
fi

echo "[2/3] Running container..."
if [ -f "docker-compose.yml" ]; then
    docker compose up -d
    echo "  Stack started via docker compose."
elif [ -f "compose.yml" ]; then
    docker compose up -d
else
    echo "  No compose file found. Run manually:"
    echo "  docker run -d --name {slug} gosdocker/{slug}"
fi

echo ""
echo "=== Deployment complete ==="
"""


class PackageStep(Step):
    """Creates deploy.sh and optionally saves Docker image as tar."""

    name = "package"

    def applicable(self, ctx: PipelineContext) -> bool:
        return True

    def execute(self, ctx: PipelineContext) -> None:
        slug = ctx.slug
        name = ctx.component_name
        work_dir = ctx.work_dir
        work_dir.mkdir(parents=True, exist_ok=True)

        # 1. Write deploy.sh
        deploy_sh = _DEPLOY_SH.format(
            name=name, slug=slug,
            timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        )
        deploy_path = work_dir / "deploy.sh"
        deploy_path.write_text(deploy_sh, encoding="utf-8")
        deploy_path.chmod(0o755)
        ctx.add_artifact("deploy_script", str(deploy_path))
        ctx.log(f"deploy.sh created")

        # 2. Try docker save
        image_tar = work_dir / f"{slug}.tar"
        try:
            img_id = subprocess.run(
                ["docker", "images", "-q", f"gosdocker/{slug}:latest"],
                capture_output=True, text=True, timeout=15,
            ).stdout.strip()
            if img_id:
                subprocess.run(
                    ["docker", "save", "-o", str(image_tar), f"gosdocker/{slug}:latest"],
                    capture_output=True, text=True, timeout=120,
                )
                ctx.add_artifact("image_tar", str(image_tar))
                ctx.log(f"Image tar: {image_tar.name} ({image_tar.stat().st_size / 1024 / 1024:.0f} MB)")
            else:
                ctx.log(f"Image not found — build first to create tar")
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            ctx.log(f"docker save skipped: {e}")
