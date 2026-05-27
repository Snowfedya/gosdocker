# GosDocker: Реестр государственных ИТ-компонентов с доказательной базой

## Контекст

GosDocker — платформа контейнеризации для государственных учреждений.
Текущая версия генерирует docker-compose.yml с `image:` директивами,
тянущими образы из внешних реестров. Критика преподавателей ВКР:
«Вы не строите ПО — вы просто скачиваете готовые образы».

**Поворот тезиса:** От «генератор docker-compose» к
**«Реестр гос. ИТ-компонентов с доказательной базой»**.

## Цели

1. Реестр 7 компонентов с манифестами + Dockerfile'ами из исходников
2. Pipeline: сборка из исходников → сканирование (SBOM/Trivy) → упаковка (tar+deploy.sh)
3. Конструктор с автоматическим резолвом зависимостей
4. 3 уровня безопасности compose (basic / standard / hardened)
5. Два режима поставки: сам собрал ИЛИ скачал tar для air-gapped

## Архитектура

```
┌─────────────────────────────────────────────────────────┐
│                    GosDocker Platform                     │
├─────────────────────┬───────────────────────────────────┤
│   РЕЕСТР (данные)   │      КОНСТРУКТОР (интерактив)     │
│   registry/{slug}/  │  POST /api/constructor             │
│   ├── manifest.yml  │  1. Выбор компонентов              │
│   ├── Dockerfile    │  2. Резолв зависимостей            │
│   └── artifacts/   │  3. Выбор профиля безопасности      │
│       ├── sbom.json │  4. Pipeline → готовый ZIP         │
│       ├── trivy.json│                                     │
│       ├── image.tar │                                     │
│       └── deploy.sh │                                     │
└─────────────────────┴───────────────────────────────────┘
         │                         │
         └─────── Pipeline ────────┘
         Build → Scan → Package → Register
```

### Pipeline Module

```python
# pipeline/base.py
class Step(ABC):
    def applicable(self, ctx: PipelineContext) -> bool: ...
    def execute(self, ctx: PipelineContext) -> None: ...

class Pipeline:
    steps: list[Step]  # [BuildStep, ScanStep, PackageStep, RegisterStep]
    
    def run(self, manifest: ComponentManifest, profile: str) -> PipelineContext:
        ctx = PipelineContext(manifest, profile)
        for step in self.steps:
            if step.applicable(ctx):
                step.execute(ctx)
        return ctx.artifacts
```

### Component Manifest (manifest.yml)

```yaml
component:
  slug: nginx
  name: nginx
  version: "1.27.4"
  category: web-servers
  description: "High-performance HTTP server and reverse proxy"
  source_url: "https://nginx.org/download/nginx-1.27.4.tar.gz"
  build_method: configure_make  # configure_make | go_build | php_extract | node_go
  build_args:
    VERSION: "1.27.4"
  dependencies:
    requires: []
    provides: [web-server]
  security:
    basic: { read_only: false, drop_caps: [] }
    standard: { read_only: true, drop_caps: [ALL], add_caps: [NET_BIND_SERVICE], healthcheck: ... }
    hardened: { read_only: true, drop_caps: [ALL], no_new_privileges: true, seccomp: default }
  ports:
    http: 80
    https: 443
  default_env:
    TZ: Europe/Moscow
```

## Файловая структура (изменения)

```
backend/
├── app/
│   ├── api/
│   │   ├── __init__.py           # + registry_router, constructor_router
│   │   ├── registry.py           # NEW: /api/registry
│   │   └── constructor.py        # NEW: /api/constructor
│   ├── pipeline/                  # NEW: modular pipeline module
│   │   ├── __init__.py
│   │   ├── base.py               # Pipeline, Step, PipelineContext
│   │   ├── build.py              # BuildStep
│   │   ├── scan.py               # ScanStep → SBOM + Trivy
│   │   ├── package.py            # PackageStep → tar + deploy.sh
│   │   └── register.py           # RegisterStep → update registry metadata
│   ├── services/
│   │   ├── generate_service.py   # UPDATED: pipeline-aware
│   │   ├── template_service.py   # UPDATED: security_profiles context
│   │   ├── dependency_resolver.py # NEW: DAG resolution
│   │   └── security_profiles.py  # NEW: 3 compose presets
│   └── templates/
│       └── single/{slug}/docker-compose.yml.j2  # UPDATED: build: + profile
├── registry/                      # NEW: component manifests
│   ├── nginx/manifest.yml, Dockerfile
│   ├── angie-pro/manifest.yml, Dockerfile
│   ├── postgresql/manifest.yml, Dockerfile
│   ├── postgresql-redos/manifest.yml, Dockerfile
│   ├── nextcloud/manifest.yml, Dockerfile
│   ├── prometheus/manifest.yml, Dockerfile
│   └── grafana/manifest.yml, Dockerfile
├── seed.py                       # UPDATED: registry fields
└── requirements.txt              # + trivy, cyclonedx-bom
```

## Component Dependency Graph

```
nextcloud ──requires──> postgresql or postgresql-redos
grafana   ──requires──> prometheus
```

Transitive: constructor auto-adds 'postgresql' when user picks 'nextcloud',
auto-adds 'prometheus' when user picks 'grafana'.

## Security Profiles — влияют на compose

### basic
```yaml
services:
  nginx:
    build: ./build/nginx
    ports: [80:80]
    networks: [gosdocker]
```

### standard (adds)
```yaml
    read_only: true
    cap_drop: [ALL]
    cap_add: [NET_BIND_SERVICE]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### hardened (adds)
```yaml
    read_only: true
    cap_drop: [ALL]
    cap_add: [NET_BIND_SERVICE]
    no_new_privileges: true
    security_opt: [seccomp:default, apparmor:docker-default]
    healthcheck: ...
```

## Non-Goals

- Подпись образов cosign (в перспективе — в тексте ВКР)
- Динамическое обнаружение плагинов (пишется руками через pipeline)
- CI/CD интеграция (только build_all.sh для batch-сборки)
- UI для администрирования реестра (только каталог + конструктор)
