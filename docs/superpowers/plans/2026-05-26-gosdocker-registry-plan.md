# GosDocker Registry + Constructor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (3 concurrent batches max). Tasks use checkbox `- [ ]` syntax.

**Goal:** Transform GosDocker from compose-generator into a full state IT-component registry with source builds, SBOM, vulnerability scanning, air-gapped packaging, dependency resolution, and 3 security profiles.

**Architecture:** Pipeline pattern (Build→Scan→Package→Register) processes each component through modular steps. Constructors resolves dependency DAG and applies security profiles before generation.

**Tech Stack:** FastAPI / SQLAlchemy async / Jinja2 / Vue3+TS+Tailwind / Docker / Trivy / CycloneDX

---

## Phase 0: Foundation — Directory Structure + Pipeline Core

Files:
- Create: `backend/app/pipeline/__init__.py`
- Create: `backend/app/pipeline/base.py`
- Create: `backend/registry/` dirs (7 slugs)
- Create: `backend/app/services/dependency_resolver.py`
- Create: `backend/app/services/security_profiles.py`

- [ ] **Step 0.1: Create directory structure**
  `mkdir -p backend/app/pipeline/ backend/registry/{nginx,angie-pro,postgresql,postgresql-redos,nextcloud,prometheus,grafana} backend/app/services/`

- [ ] **Step 0.2: Write pipeline/base.py**

```python
"""Pipeline base classes — Step, Pipeline, PipelineContext."""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Any

@dataclass
class PipelineContext:
    manifest: dict
    profile: str  # basic | standard | hardened
    work_dir: Path
    artifacts: dict = field(default_factory=lambda: {
        "dockerfile": None,
        "sbom": None,
        "trivy_report": None,
        "image_tar": None,
        "deploy_script": None,
    })
    logs: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def log(self, msg: str) -> None:
        self.logs.append(msg)

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def add_artifact(self, key: str, path: str | Path) -> None:
        self.artifacts[key] = str(path)


class Step(ABC):
    name: str = "step"

    @abstractmethod
    def applicable(self, ctx: PipelineContext) -> bool:
        ...

    @abstractmethod
    def execute(self, ctx: PipelineContext) -> None:
        ...


class Pipeline:
    def __init__(self, steps: list[Step]):
        self.steps = steps

    def run(self, manifest: dict, profile: str = "standard", work_dir: Path | None = None) -> PipelineContext:
        ctx = PipelineContext(
            manifest=manifest,
            profile=profile,
            work_dir=work_dir or Path("/tmp/gosdocker-build"),
        )
        ctx.log(f"Pipeline start: {manifest.get('component', {}).get('slug', 'unknown')} @ {profile}")
        for step in self.steps:
            if not step.applicable(ctx):
                ctx.log(f"  Skip {step.name}: not applicable")
                continue
            ctx.log(f"  Run {step.name}...")
            step.execute(ctx)
            if ctx.errors:
                ctx.log(f"  {step.name} FAILED: {ctx.errors[-1]}")
                break
        return ctx
```

- [ ] **Step 0.3: Write pipeline/__init__.py**
  `from .base import Pipeline, Step, PipelineContext`

- [ ] **Step 0.4: Verify — import pipeline module**
  `cd backend && python -c "from app.pipeline import Pipeline; print('Pipeline OK')"`
  Expected: `Pipeline OK`

---

## Phase 1: Registry Manifests + Dockerfiles

### Batch 1.1: nginx + angie-pro + postgresql

- [ ] **1.1a: nginx manifest.yml** — `registry/nginx/manifest.yml`
  source: `http://nginx.org/download/nginx-1.27.4.tar.gz`, method: `configure_make`
  Dockerfile: multi-stage Alpine, `./configure --with-http_ssl_module --with-http_v2_module`, stage 2 = alpine:latest

- [ ] **1.1b: angie-pro manifest.yml** — `registry/angie-pro/manifest.yml`
  source: `https://github.com/angie/angie/archive/refs/tags/1.10.0.tar.gz`, method: `configure_make`
  Dockerfile: multi-stage, same pattern as nginx with angie-specific config

- [ ] **1.1c: postgresql manifest.yml** — `registry/postgresql/manifest.yml`
  source: `https://ftp.postgresql.org/pub/source/v15.10/postgresql-15.10.tar.bz2`, method: `configure_make`
  Dockerfile: multi-stage Debian, `./configure --with-openssl --with-icu`, long compile

### Batch 1.2: postgresql-redos + nextcloud

- [ ] **1.2a: postgresql-redos manifest.yml** — `registry/postgresql-redos/manifest.yml`
  source: `https://ftp.postgresql.org/pub/source/v17.2/postgresql-17.2.tar.bz2`, method: `configure_make`
  Dockerfile: multi-stage, postgresql 17 + RED OS compat layer

- [ ] **1.2b: nextcloud manifest.yml** — `registry/nextcloud/manifest.yml`
  source: `https://download.nextcloud.com/server/releases/nextcloud-30.0.0.tar.bz2`, method: `php_extract`
  Dockerfile: multi-stage, php-fpm + nginx, extract to webroot, runs as www-data

### Batch 1.3: prometheus + grafana

- [ ] **1.3a: prometheus manifest.yml** — `registry/prometheus/manifest.yml`
  source: `https://github.com/prometheus/prometheus/archive/refs/tags/v2.55.0.tar.gz`, method: `go_build`
  Dockerfile: multi-stage golang:alpine build → scratch runtime

- [ ] **1.3b: grafana manifest.yml** — `registry/grafana/manifest.yml`
  source: `https://github.com/grafana/grafana/archive/refs/tags/v11.4.0.tar.gz`, method: `node_go`
  Dockerfile: multi-stage — Node.js frontend build + Go backend build → alpine runtime

---

## Phase 2: Pipeline Steps

### Task 2.1: BuildStep

- [ ] **Write pipeline/build.py**

```python
"""BuildStep — generates Dockerfile path in compose build: directive."""
from .base import Step, PipelineContext

class BuildStep(Step):
    name = "build"
    
    def applicable(self, ctx: PipelineContext) -> bool:
        # All components have a Dockerfile
        return True
    
    def execute(self, ctx: PipelineContext) -> None:
        slug = ctx.manifest.get("component", {}).get("slug", "unknown")
        dockerfile_path = f"registry/{slug}/Dockerfile"
        ctx.add_artifact("dockerfile", dockerfile_path)
        ctx.log(f"Build artifact: {dockerfile_path}")
```

### Task 2.2: ScanStep

- [ ] **Write pipeline/scan.py**

```python
"""ScanStep — generates SBOM (CycloneDX) and Trivy report."""
class ScanStep(Step):
    name = "scan"
    
    def applicable(self, ctx: PipelineContext) -> bool:
        # Applicable for non-php-extract components? Actually for all
        return True
    
    def execute(self, ctx: PipelineContext) -> None:
        # Generate CycloneDX SBOM
        # Run Trivy scan
        # Save reports to work_dir / artifacts
```

### Task 2.3: PackageStep

- [ ] **Write pipeline/package.py**

```python
"""PackageStep — creates tar archive + deploy.sh for air-gapped."""
class PackageStep(Step):
    name = "package"
    
    def applicable(self, ctx: PipelineContext) -> bool:
        return True
    
    def execute(self, ctx: PipelineContext) -> None:
        # docker save → image.tar
        # Generate deploy.sh script
        # Add to context artifacts
```

### Task 2.4: RegisterStep

- [ ] **Write pipeline/register.py**

```python
"""RegisterStep — updates component metadata with build results."""
class RegisterStep(Step):
    name = "register"
    
    def applicable(self, ctx: PipelineContext) -> bool:
        return True
    
    def execute(self, ctx: PipelineContext) -> None:
        # Record build timestamp, artifact hashes, SBOM digest
```

---

## Phase 3: Services

### Task 3.1: dependency_resolver.py

```python
"""Dependency resolver — DAG-based component dependency resolution."""

class DependencyResolver:
    GRAPH = {
        "nextcloud": {"database"},     # requires database
        "grafana": {"monitoring"},     # requires prometheus/monitoring
        "postgresql": set(),           # no deps
        "postgresql-redos": set(),     # no deps
        "nginx": set(),                # no deps
        "angie-pro": set(),            # no deps
        "prometheus": set(),           # no deps
    }
    
    # Dependency providers
    PROVIDERS = {
        "database": {"postgresql", "postgresql-redos"},
        "monitoring": {"prometheus"},
        "web-server": {"nginx", "angie-pro"},
    }
    
    def resolve(self, selected_slugs: list[str]) -> list[str]:
        """Add missing dependencies, return complete list."""
        resolved = set(selected_slugs)
        changed = True
        while changed:
            changed = False
            for slug in list(resolved):
                needs = self.GRAPH.get(slug, set())
                for dep_type in needs:
                    if not (resolved & self.PROVIDERS.get(dep_type, set())):
                        # Pick first available provider
                        provider = next(iter(self.PROVIDERS.get(dep_type, set())))
                        if provider not in resolved:
                            resolved.add(provider)
                            changed = True
        return list(resolved)
```

### Task 3.2: security_profiles.py

```python
"""Security profiles — compose template additions per security level."""

PROFILES = {
    "basic": {
        "read_only": False,
        "cap_drop": [],
        "no_new_privileges": False,
    },
    "standard": {
        "read_only": True,
        "cap_drop": ["ALL"],
        "cap_add": ["NET_BIND_SERVICE", "CHOWN", "DAC_OVERRIDE"],
        "healthcheck": {"test": ["CMD-SHELL", "exit 0"], "interval": "30s"},
        "no_new_privileges": True,
    },
    "hardened": {
        "read_only": True,
        "cap_drop": ["ALL"],
        "cap_add": ["NET_BIND_SERVICE"],
        "no_new_privileges": True,
        "security_opt": ["seccomp:default", "no-new-privileges:true"],
        "healthcheck": {"test": ["CMD-SHELL", "exit 0"], "interval": "30s"},
    },
}
```

---

## Phase 4: API Routes

### Task 4.1: registry.py — /api/registry

```
GET /api/registry          — list all components with manifest metadata
GET /api/registry/{slug}   — get full component manifest + Dockerfile content
GET /api/registry/{slug}/artifacts — list available artifacts (sbom, trivy, tar)
```

### Task 4.2: constructor.py — /api/constructor

```
POST /api/constructor
Body: { "components": ["nextcloud", "nginx"], "profile": "standard" }
→ Auto-adds postgresql dependency
→ Generates ZIP with: docker-compose.yml + build/ dir + SBOM + Trivy + deploy.sh
```

### Task 4.3: Update generate.py — add profile support

- [ ] Add `security_profile` field to GenerateRequest
- [ ] Pass profile context through GenerateService → TemplateService

---

## Phase 5: Frontend

### Task 5.1: RegistryView.vue

- Card grid of all 7 components with manifest metadata
- Each card shows: source_url, Dockerfile status, SBOM badge, Trivy badge
- Detail modal with full Dockerfile view + download buttons per artifact

### Task 5.2: ConstructorView.vue

- Select components (checkboxes)
- Shows dependency auto-additions
- Security profile selector (basic | standard | hardened)
- Generate button → downloads ZIP
- Stack preview (compose YAML before download)

### Task 5.3: Update router + types + useApi

- [ ] Add /registry and /constructor routes
- [ ] Add RegistryComponent and ConstructorRequest types
- [ ] Add fetchRegistry, fetchConstructor API methods

---

## Phase 6: Integration & Verification

- [ ] Reseed database with registry-aware seed.py
- [ ] Verify: `python -c "from app.pipeline import Pipeline"` — no import errors
- [ ] Verify: `curl -s http://localhost:8000/api/registry` — returns 7 components
- [ ] Verify: `curl -s -X POST http://localhost:8000/api/constructor -H 'Content-Type: application/json' -d '{"components":["nextcloud"],"profile":"standard"}'` — returns ZIP with docker-compose.yml + build/nextcloud/Dockerfile
- [ ] Verify: `curl -s http://localhost:8000/api/registry/nginx/manifest` — contains all YAML fields
- [ ] Verify frontend build: `cd frontend && npm run build` — success
