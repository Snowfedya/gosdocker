"""Pipeline module — modular build→scan→package→register pipeline for GosDocker components."""
from .base import Pipeline, Step, PipelineContext
from .build import BuildStep
from .scan import ScanStep
from .package import PackageStep
from .register import RegisterStep

__all__ = [
    "Pipeline", "Step", "PipelineContext",
    "BuildStep", "ScanStep", "PackageStep", "RegisterStep",
]
