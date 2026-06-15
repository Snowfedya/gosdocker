"""Tests for pipeline step behavior under network-constrained environments.

Lesson #24 (pre-defense): "don't say 'works' until you've verified with
curl + docker pull". When egress is blocked, BuildStep must degrade gracefully
and signal degraded mode via artifacts, not hang.

Per skill `gosdocker-network-probe-fallacy`: BuildStep.applicable() must
NOT probe network (would block in sandbox). It checks `shutil.which("docker")`
only. Network availability is detected at execute() time via the docker
subprocess exit code.
"""
import tempfile
from pathlib import Path
from unittest.mock import patch

from app.pipeline.base import PipelineContext
from app.pipeline.build import BuildStep
from app.pipeline.owasp import DependencyCheckStep


def _make_ctx(slug: str = "test-slug") -> PipelineContext:
    """Build a minimal PipelineContext for unit testing."""
    return PipelineContext(
        manifest={"component": {"slug": slug, "build_method": "docker", "source_url": "x"}},
        profile="standard",
        work_dir=Path(tempfile.mkdtemp(prefix="gosdocker-test-")),
    )


def test_build_applicable_false_when_docker_missing():
    """applicable() returns False when docker binary is not on PATH."""
    with patch("app.pipeline.build.shutil.which", return_value=None):
        assert BuildStep().applicable(_make_ctx()) is False


def test_build_applicable_true_when_docker_available():
    """applicable() returns True when docker binary is on PATH.
    (Per skill: must NOT probe network here — that would block in sandbox.)
    """
    with patch("app.pipeline.build.shutil.which", return_value="/usr/bin/docker"):
        assert BuildStep().applicable(_make_ctx()) is True


def test_build_execute_skips_when_docker_missing():
    """AC-1.2 + AC-1.3: execute() with applicable()=False adds degraded marker,
    logs skip, no exception, no error in ctx.errors.
    """
    ctx = _make_ctx()
    step = BuildStep()

    with patch.object(step, "applicable", return_value=False):
        step.execute(ctx)

    assert any("skip" in log.lower() or "degraded" in log.lower() or "docker" in log.lower()
               for log in ctx.logs), f"expected skip/docker log, got: {ctx.logs}"
    assert ctx.errors == [], f"expected no errors, got: {ctx.errors}"


def test_build_execute_no_registry_path_skips_cleanly():
    """When applicable()=True but registry path doesn't exist, log + skip."""
    ctx = _make_ctx("nonexistent-slug-zzz-fake")
    step = BuildStep()

    with patch.object(step, "applicable", return_value=True):
        step.execute(ctx)

    assert ctx.errors == [], f"expected no errors, got: {ctx.errors}"


# -------- DependencyCheckStep network degradation --------

def test_owasp_applicable_false_when_docker_missing():
    """OWASP DC: applicable() returns False when docker binary is not on PATH.
    (Per skill: must NOT probe network here — that would block in sandbox.)"""
    with patch("app.pipeline.owasp.shutil.which", return_value=None):
        assert DependencyCheckStep().applicable(_make_ctx()) is False


def test_owasp_execute_writes_placeholder_when_no_network():
    """OWASP DC: execute() with applicable()=False writes placeholder, no docker call."""
    ctx = _make_ctx("test-owasp-slug")
    step = DependencyCheckStep()

    with patch.object(step, "applicable", return_value=False):
        with patch("app.pipeline.owasp.subprocess.run") as mock_run:
            step.execute(ctx)
            mock_run.assert_not_called()  # critical: no docker run attempt

    assert ctx.errors == []
