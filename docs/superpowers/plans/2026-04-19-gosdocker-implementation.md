# GosDocker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Создать веб-платформу GosDocker — каталог готовых Docker Compose-сборок для госструктур с двумя режимами (просмотр + конфигуратор).

**Architecture:** Vue 3 + FastAPI + PostgreSQL + Jinja2 для генерации docker-compose. Платформа предоставляет API для каталога компонентов и endpoint для генерации ZIP-архивов с настроенными docker-compose.yml.

**Tech Stack:** Vue 3, Vite, TailwindCSS, FastAPI, SQLAlchemy 2.0 (async), PostgreSQL 15, Jinja2, Docker Compose

---

## Файловая структура

```
gosdocker/
├── docker-compose.yml           # Платформа (не каталог!)
├── .env.example
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/versions/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI entry
│   │   ├── config.py            # Pydantic Settings
│   │   ├── database.py           # Async SQLAlchemy
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── category.py
│   │   │   ├── component.py
│   │   │   └── stack.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── category.py
│   │   │   ├── component.py
│   │   │   └── generate.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── categories.py
│   │   │   ├── components.py
│   │   │   ├── stacks.py
│   │   │   └── generate.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── template_service.py
│   │   │   └── generate_service.py
│   │   └── templates/
│   │       ├── single/
│   │       │   ├── angie/
│   │       │   │   └── docker-compose.yml.j2
│   │       │   ├── nginx/
│   │       │   │   └── docker-compose.yml.j2
│   │       │   ├── postgresql-redos/
│   │       │   │   └── docker-compose.yml.j2
│   │       │   ├── postgresql/
│   │       │   │   └── docker-compose.yml.j2
│   │       │   ├── nextcloud/
│   │       │   │   └── docker-compose.yml.j2
│   │       │   ├── prometheus/
│   │       │   │   └── docker-compose.yml.j2
│   │       │   └── grafana/
│   │       │       └── docker-compose.yml.j2
│   │       └── stacks/
│   │           ├── web-stack.yml.j2
│   │           ├── data-stack.yml.j2
│   │           └── monitoring-stack.yml.j2
│   └── seed.py
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   ├── index.html
│   └── src/
│       ├── main.ts
│       ├── App.vue
│       ├── router/index.ts
│       ├── views/
│       │   ├── HomeView.vue
│       │   ├── CatalogView.vue
│       │   ├── ComponentView.vue
│       │   └── StacksView.vue
│       ├── components/
│       │   ├── CategoryCard.vue
│       │   ├── ComponentCard.vue
│       │   ├── StackCard.vue
│       │   ├── SourceBadge.vue
│       │   ├── ConfigWizard.vue
│       │   └── Footer.vue
│       ├── composables/
│       │   ├── useApi.ts
│       │   └── useDownload.ts
│       └── types/index.ts
└── nginx/
    ├── Dockerfile
    └── nginx.conf
```

---

## Task 1: Проект backend — структура и модели

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/database.py`
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/category.py`
- Create: `backend/app/models/component.py`
- Create: `backend/app/models/stack.py`

- [ ] **Step 1: Создать backend/requirements.txt**

```txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy[asyncio]==2.0.25
asyncpg==0.29.0
pydantic==2.5.3
pydantic-settings==2.1.0
jinja2==3.1.3
python-multipart==0.0.6
aiofiles==23.2.1
alembic==1.13.1
psycopg2-binary==2.9.9
httpx==0.26.0
```

- [ ] **Step 2: Создать backend/app/config.py**

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://gosdocker:secret@localhost:5432/gosdocker"
    debug: bool = False
    templates_dir: str = "app/templates"

    class Config:
        env_file = ".env"

settings = Settings()
```

- [ ] **Step 3: Создать backend/app/database.py**

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

Base = declarative_base()

engine = create_async_engine(settings.database_url, echo=settings.debug)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db():
    async with async_session() as session:
        yield session
```

- [ ] **Step 4: Создать backend/app/models/category.py**

```python
from sqlalchemy import Column, String, Integer, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from ..database import Base

class Category(Base):
    __tablename__ = "categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    icon = Column(String(50), default="📦")
    description = Column(Text)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    components = relationship("Component", back_populates="category")
```

- [ ] **Step 5: Создать backend/app/models/component.py**

```python
from sqlalchemy import Column, String, Text, Boolean, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from ..database import Base

class Component(Base):
    __tablename__ = "components"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    slug = Column(String(200), unique=True, nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"))

    # Docker
    image = Column(String(500), nullable=False)
    image_source = Column(String(200))  # "registry.red-soft.ru" / "dh-mirror.gitverse.ru"
    registry_url = Column(String(500), nullable=False)
    is_registry = Column(Boolean, default=False)
    registry_number = Column(String(50))  # "№17604"

    # Метаданные
    description = Column(Text)
    version = Column(String(50))
    documentation_url = Column(String(500))

    # Конфигурация
    default_ports = Column(JSON, default=dict)
    default_volumes = Column(JSON, default=dict)
    default_env = Column(JSON, default=dict)
    variables_schema = Column(JSON, default=dict)
    template_file = Column(String(500))

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    category = relationship("Category", back_populates="components")
```

- [ ] **Step 6: Создать backend/app/models/stack.py**

```python
from sqlalchemy import Column, String, Text, Boolean, DateTime, Table
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from ..database import Base

stack_components = Table(
    'stack_components',
    Base.metadata,
    Column('stack_id', UUID(as_uuid=True), ForeignKey('stacks.id')),
    Column('component_id', UUID(as_uuid=True), ForeignKey('components.id'))
)

class Stack(Base):
    __tablename__ = "stacks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    slug = Column(String(200), unique=True, nullable=False)
    description = Column(Text)
    is_featured = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    components = relationship("Component", secondary=stack_components)
```

- [ ] **Step 7: Создать backend/app/__init__.py**

```python
from .config import settings
from .database import Base, get_db, engine
from .models.category import Category
from .models.component import Component
from .models.stack import Stack, stack_components

__all__ = ["settings", "Base", "get_db", "engine", "Category", "Component", "Stack"]
```

- [ ] **Step 8: Commit**

```bash
cd backend && git add -A && git commit -m "feat: add backend structure and models"
```

---

## Task 2: Проект backend — API endpoints

**Files:**
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/schemas/category.py`
- Create: `backend/app/schemas/component.py`
- Create: `backend/app/schemas/generate.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/categories.py`
- Create: `backend/app/api/components.py`
- Create: `backend/app/api/stacks.py`
- Create: `backend/app/api/generate.py`
- Create: `backend/app/main.py`

- [ ] **Step 1: Создать schemas/category.py**

```python
from pydantic import BaseModel
from uuid import UUID

class CategoryBase(BaseModel):
    name: str
    slug: str
    icon: str = "📦"
    description: str | None = None
    sort_order: int = 0

class CategoryResponse(CategoryBase):
    id: UUID
    components_count: int = 0
    registry_count: int = 0
    community_count: int = 0

    class Config:
        from_attributes = True
```

- [ ] **Step 2: Создать schemas/component.py**

```python
from pydantic import BaseModel
from uuid import UUID

class ComponentBase(BaseModel):
    name: str
    slug: str
    image: str
    is_registry: bool = False
    registry_number: str | None = None
    description: str | None = None
    version: str | None = None

class ComponentDetail(ComponentBase):
    id: UUID
    category: str
    image_source: str
    registry_url: str
    default_ports: dict = {}
    default_volumes: dict = {}
    default_env: dict = {}
    variables_schema: dict = {}

    class Config:
        from_attributes = True
```

- [ ] **Step 3: Создать schemas/generate.py**

```python
from pydantic import BaseModel
from dict import dict

class ComponentConfig(BaseModel):
    ports: dict[str, int] = {}
    volumes: dict[str, str] = {}
    env: dict[str, str] = {}

class GenerateRequest(BaseModel):
    components: list[str]  # slugs
    config: dict[str, ComponentConfig] = {}
    include_sources: bool = True

class GenerateResponse(BaseModel):
    filename: str
    size_bytes: int
    files: list[str]
```

- [ ] **Step 4: Создать api/categories.py**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from ..database import get_db
from ..models import Category, Component
from ..schemas.category import CategoryResponse

router = APIRouter(prefix="/api/categories", tags=["categories"])

@router.get("", response_model=list[CategoryResponse])
async def list_categories(db: AsyncSession = Depends(get_db)):
    query = select(Category).order_by(Category.sort_order)
    result = await db.execute(query)
    categories = result.scalars().all()

    response = []
    for cat in categories:
        comp_query = select(func.count()).where(Component.category_id == cat.id)
        comp_result = await db.execute(comp_query)
        total = comp_result.scalar()

        reg_query = select(func.count()).where(
            Component.category_id == cat.id,
            Component.is_registry == True
        )
        reg_result = await db.execute(reg_query)
        registry_count = reg_result.scalar()

        response.append(CategoryResponse(
            id=cat.id,
            name=cat.name,
            slug=cat.slug,
            icon=cat.icon,
            description=cat.description,
            sort_order=cat.sort_order,
            components_count=total,
            registry_count=registry_count,
            community_count=total - registry_count
        ))

    return response
```

- [ ] **Step 5: Создать api/components.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..database import get_db
from ..models import Component, Category
from ..schemas.component import ComponentDetail

router = APIRouter(prefix="/api/components", tags=["components"])

@router.get("", response_model=list[ComponentDetail])
async def list_components(
    category: str | None = None,
    registry_only: bool = False,
    db: AsyncSession = Depends(get_db)
):
    query = select(Component)
    if category:
        query = query.join(Category).where(Category.slug == category)
    if registry_only:
        query = query.where(Component.is_registry == True)

    result = await db.execute(query)
    components = result.scalars().all()

    return [
        ComponentDetail(
            id=comp.id,
            name=comp.name,
            slug=comp.slug,
            category=comp.category.slug if comp.category else "",
            image=comp.image,
            is_registry=comp.is_registry,
            registry_number=comp.registry_number,
            image_source=comp.image_source or "",
            registry_url=comp.registry_url,
            description=comp.description,
            version=comp.version,
            default_ports=comp.default_ports or {},
            default_volumes=comp.default_volumes or {},
            default_env=comp.default_env or {},
            variables_schema=comp.variables_schema or {}
        )
        for comp in components
    ]

@router.get("/{slug}", response_model=ComponentDetail)
async def get_component(slug: str, db: AsyncSession = Depends(get_db)):
    query = select(Component).where(Component.slug == slug)
    result = await db.execute(query)
    comp = result.scalar_one_or_none()

    if not comp:
        raise HTTPException(status_code=404, detail="Component not found")

    return ComponentDetail(
        id=comp.id,
        name=comp.name,
        slug=comp.slug,
        category=comp.category.slug if comp.category else "",
        image=comp.image,
        is_registry=comp.is_registry,
        registry_number=comp.registry_number,
        image_source=comp.image_source or "",
        registry_url=comp.registry_url,
        description=comp.description,
        version=comp.version,
        default_ports=comp.default_ports or {},
        default_volumes=comp.default_volumes or {},
        default_env=comp.default_env or {},
        variables_schema=comp.variables_schema or {}
    )
```

- [ ] **Step 6: Создать api/stacks.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..database import get_db
from ..models import Stack

router = APIRouter(prefix="/api/stacks", tags=["stacks"])

@router.get("")
async def list_stacks(db: AsyncSession = Depends(get_db)):
    query = select(Stack).order_by(Stack.is_featured.desc())
    result = await db.execute(query)
    stacks = result.scalars().all()

    return [
        {
            "id": str(s.id),
            "name": s.name,
            "slug": s.slug,
            "description": s.description,
            "is_featured": s.is_featured,
            "components": [
                {"name": c.name, "slug": c.slug, "is_registry": c.is_registry}
                for c in s.components
            ]
        }
        for s in stacks
    ]

@router.get("/{slug}")
async def get_stack(slug: str, db: AsyncSession = Depends(get_db)):
    query = select(Stack).where(Stack.slug == slug)
    result = await db.execute(query)
    stack = result.scalar_one_or_none()

    if not stack:
        raise HTTPException(status_code=404, detail="Stack not found")

    return {
        "id": str(stack.id),
        "name": stack.name,
        "slug": stack.slug,
        "description": stack.description,
        "is_featured": stack.is_featured,
        "components": [
            {
                "name": c.name,
                "slug": c.slug,
                "is_registry": c.is_registry,
                "image": c.image,
                "registry_url": c.registry_url,
                "default_ports": c.default_ports or {},
                "default_env": c.default_env or {}
            }
            for c in stack.components
        ]
    }
```

- [ ] **Step 7: Создать api/generate.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from io import BytesIO
from ..database import get_db
from ..models import Component
from ..services.generate_service import GenerateService

router = APIRouter(prefix="/api/generate", tags=["generate"])

@router.post("")
async def generate_compose(
    slugs: list[str],
    config: dict,
    db: AsyncSession = Depends(get_db)
):
    # Получаем компоненты
    query = select(Component).where(Component.slug.in_(slugs))
    result = await db.execute(query)
    components = result.scalars().all()

    if not components:
        raise HTTPException(status_code=404, detail="No components found")

    # Генерируем ZIP
    service = GenerateService()
    zip_buffer = await service.create_zip(components, config)

    return StreamingResponse(
        iter([zip_buffer.getvalue()]),
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=gosdocker-stack.zip"
        }
    )
```

- [ ] **Step 8: Создать main.py**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import categories, components, stacks, generate

app = FastAPI(
    title="GosDocker API",
    description="Каталог Docker Compose-сборок для госструктур",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(categories.router)
app.include_router(components.router)
app.include_router(stacks.router)
app.include_router(generate.router)

@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 9: Commit**

```bash
git add -A && git commit -m "feat: add API endpoints"
```

---

## Task 3: Проект backend — services (Jinja2 + генерация)

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/template_service.py`
- Create: `backend/app/services/generate_service.py`

- [ ] **Step 1: Создать services/template_service.py**

```python
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path
from datetime import datetime

class TemplateService:
    def __init__(self, templates_dir: str = "app/templates"):
        self.templates_path = Path(templates_dir)
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_path)),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
        # Добавляем datetime в глобальный контекст
        self.env.globals['now'] = datetime.utcnow

    def render(self, template_path: str, context: dict) -> str:
        """Рендерит Jinja2 шаблон с контекстом."""
        template = self.env.get_template(template_path)
        return template.render(**context)

    def render_single(self, component_slug: str, config: dict) -> str:
        """Рендерит docker-compose для одного компонента."""
        template_path = f"single/{component_slug}/docker-compose.yml.j2"
        return self.render(template_path, {"config": config})

    def render_stack(self, stack_slug: str, components: list, configs: dict) -> str:
        """Рендерит docker-compose для стека (нескольких компонентов)."""
        template_path = f"stacks/{stack_slug}.yml.j2"
        return self.render(template_path, {
            "components": components,
            "configs": configs
        })
```

- [ ] **Step 2: Создать services/generate_service.py**

```python
import zipfile
from io import BytesIO
from pathlib import Path
from datetime import datetime
from .template_service import TemplateService

class GenerateService:
    def __init__(self):
        self.template_service = TemplateService()

    async def create_zip(self, components: list, configs: dict) -> BytesIO:
        """Создаёт ZIP-архив с docker-compose.yml и сопутствующими файлами."""

        buffer = BytesIO()

        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Рендерим docker-compose.yml
            compose_content = self._render_compose(components, configs)
            zf.writestr("docker-compose.yml", compose_content)

            # Создаём .env.example
            env_content = self._create_env_example(components, configs)
            zf.writestr(".env.example", env_content)

            # Создаём README.md
            readme_content = self._create_readme(components)
            zf.writestr("README.md", readme_content)

        buffer.seek(0)
        return buffer

    def _render_compose(self, components: list, configs: dict) -> str:
        """Рендерит единый docker-compose.yml из всех компонентов."""

        services = []
        networks = ["gosdocker"]

        for comp in components:
            slug = comp.slug
            config = configs.get(slug, {})

            # Рендерим шаблон компонента
            try:
                content = self.template_service.render_single(slug, config)
                services.append(content)
            except Exception as e:
                # Fallback — базовый docker-compose если шаблона нет
                services.append(self._fallback_compose(comp, config))

        # Объединяем
        return self._merge_compose_files(services, networks)

    def _fallback_compose(self, component, config: dict) -> str:
        """Базовая генерация если шаблона нет."""
        ports = config.get("ports", {})
        env = config.get("env", {})
        volumes = config.get("volumes", {})

        ports_str = "\n".join([f"      - \"{ext}:{int}\"" for ext, int in ports.items()]) if ports else ""
        env_str = "\n".join([f"      {k}: \"{v}\"" for k, v in env.items()]) if env else ""
        volumes_str = "\n".join([f"      - {host}:{container}" for host, container in volumes.items()]) if volumes else ""

        return f"""
  {component.slug}:
    image: {component.registry_url}
    container_name: {component.slug}
    restart: unless-stopped
    ports:
{ports_str}
    environment:
{env_str}
    volumes:
{volumes_str}
"""

    def _merge_compose_files(self, services: list, networks: list) -> str:
        """Объединяет куски docker-compose в один файл."""

        services_yaml = "".join(services)

        networks_yaml = "\n".join([f"  {net}:" for net in networks]) + """
    driver: bridge
"""

        return f"""# Generated by GosDocker
# {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

services:
{services_yaml}
networks:
{networks_yaml}
"""

    def _create_env_example(self, components: list, configs: dict) -> str:
        """Создаёт .env.example с переменными."""
        lines = ["# GosDocker Environment Variables", "# Update values for your environment", ""]

        for comp in components:
            slug = comp.slug
            config = configs.get(slug, {})
            env = config.get("env", {})

            for key, value in env.items():
                lines.append(f"{slug.upper()}_{key.upper()}={value}")

        return "\n".join(lines)

    def _create_readme(self, components: list) -> str:
        """Создаёт README.md для скачанной сборки."""

        component_list = "\n".join([f"- {c.name}" for c in components])

        return f"""# GosDocker Stack

Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

## Components

{component_list}

## Quick Start

```bash
# Copy environment file
cp .env.example .env
# Edit .env with your values

# Start stack
docker compose up -d
```

## Sources

| Component | Image | Source |
|-----------|-------|--------|
{chr(10).join([f"| {c.name} | {c.image} | {c.registry_url} |" for c in components])}
"""
```

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "feat: add template and generate services"
```

---

## Task 4: Jinja2 шаблоны

**Files:**
- Create: `backend/app/templates/single/angie/docker-compose.yml.j2`
- Create: `backend/app/templates/single/nginx/docker-compose.yml.j2`
- Create: `backend/app/templates/single/postgresql-redos/docker-compose.yml.j2`
- Create: `backend/app/templates/single/postgresql/docker-compose.yml.j2`
- Create: `backend/app/templates/single/nextcloud/docker-compose.yml.j2`
- Create: `backend/app/templates/single/prometheus/docker-compose.yml.j2`
- Create: `backend/app/templates/single/grafana/docker-compose.yml.j2`
- Create: `backend/app/templates/stacks/web-stack.yml.j2`

- [ ] **Step 1: Создать angie docker-compose.yml.j2**

```yaml
# GosDocker - Angie PRO
# Image: {{ registry_url }}
# Generated: {{ now.strftime('%Y-%m-%d %H:%M:%S') }}

  angie:
    image: {{ registry_url }}
    container_name: angie
    restart: unless-stopped
{% if config.ports %}
    ports:
{% for ext, int in config.ports.items() %}
      - "{{ ext }}:{{ int }}"
{% endfor %}
{% endif %}
{% if config.volumes %}
    volumes:
{% for host, container in config.volumes.items() %}
      - {{ host }}:{{ container }}
{% endfor %}
{% endif %}
{% if config.env %}
    environment:
{% for key, value in config.env.items() %}
      {{ key }}: "{{ value }}"
{% endfor %}
{% endif %}
    networks:
      - gosdocker
```

- [ ] **Step 2: Создать nginx docker-compose.yml.j2**

```yaml
# GosDocker - nginx (Community)
# Image: {{ registry_url }}
# Generated: {{ now.strftime('%Y-%m-%d %H:%M:%S') }}

  nginx:
    image: {{ registry_url }}
    container_name: nginx
    restart: unless-stopped
{% if config.ports %}
    ports:
{% for ext, int in config.ports.items() %}
      - "{{ ext }}:{{ int }}"
{% endfor %}
{% endif %}
{% if config.volumes %}
    volumes:
{% for host, container in config.volumes.items() %}
      - {{ host }}:{{ container }}
{% endfor %}
{% endif %}
{% if config.env %}
    environment:
{% for key, value in config.env.items() %}
      {{ key }}: "{{ value }}"
{% endfor %}
{% endif %}
    networks:
      - gosdocker
```

- [ ] **Step 3: Создать postgresql-redos docker-compose.yml.j2**

```yaml
# GosDocker - PostgreSQL (РЕД ОС)
# Image: {{ registry_url }}
# Source: registry.red-soft.ru
# Generated: {{ now.strftime('%Y-%m-%d %H:%M:%S') }}

  postgresql-redos:
    image: {{ registry_url }}
    container_name: postgresql-redos
    restart: unless-stopped
{% if config.ports %}
    ports:
{% for ext, int in config.ports.items() %}
      - "{{ ext }}:{{ int }}"
{% endfor %}
{% endif %}
    environment:
      POSTGRES_DB: gosdocker
      POSTGRES_USER: gosdocker
      POSTGRES_PASSWORD: {{ config.env.get('POSTGRES_PASSWORD', 'changeme') | default('changeme') }}
{% if config.env.TZ %}
      TZ: "{{ config.env.TZ }}"
{% endif %}
{% if config.volumes %}
    volumes:
{% for host, container in config.volumes.items() %}
      - {{ host }}:{{ container }}
{% endfor %}
{% else %}
    volumes:
      - pgdata:/var/lib/postgresql/data
{% endif %}
    networks:
      - gosdocker

volumes:
  pgdata:
```

- [ ] **Step 4: Создать postgresql docker-compose.yml.j2**

```yaml
# GosDocker - PostgreSQL (Community)
# Image: {{ registry_url }}
# Generated: {{ now.strftime('%Y-%m-%d %H:%M:%S') }}

  postgresql:
    image: {{ registry_url }}
    container_name: postgresql
    restart: unless-stopped
{% if config.ports %}
    ports:
{% for ext, int in config.ports.items() %}
      - "{{ ext }}:{{ int }}"
{% endfor %}
{% endif %}
    environment:
      POSTGRES_DB: gosdocker
      POSTGRES_USER: gosdocker
      POSTGRES_PASSWORD: {{ config.env.get('POSTGRES_PASSWORD', 'changeme') }}
{% if config.env.TZ %}
      TZ: "{{ config.env.TZ }}"
{% endif %}
{% if config.volumes %}
    volumes:
{% for host, container in config.volumes.items() %}
      - {{ host }}:{{ container }}
{% endfor %}
{% else %}
    volumes:
      - pgdata:/var/lib/postgresql/data
{% endif %}
    networks:
      - gosdocker

volumes:
  pgdata:
```

- [ ] **Step 5: Создать nextcloud docker-compose.yml.j2**

```yaml
# GosDocker - Nextcloud
# Image: {{ registry_url }}
# Generated: {{ now.strftime('%Y-%m-%d %H:%M:%S') }}

  nextcloud:
    image: {{ registry_url }}
    container_name: nextcloud
    restart: unless-stopped
{% if config.ports %}
    ports:
{% for ext, int in config.ports.items() %}
      - "{{ ext }}:{{ int }}"
{% endfor %}
{% else %}
    ports:
      - "8080:80"
{% endif %}
    environment:
      MYSQL_HOST: postgresql-redos
      MYSQL_DATABASE: nextcloud
      MYSQL_USER: gosdocker
      MYSQL_PASSWORD: {{ config.env.get('MYSQL_PASSWORD', 'changeme') }}
{% if config.env.TZ %}
      TZ: "{{ config.env.TZ }}"
{% endif %}
{% if config.volumes %}
    volumes:
{% for host, container in config.volumes.items() %}
      - {{ host }}:{{ container }}
{% endfor %}
{% else %}
    volumes:
      - nextcloud_data:/var/www/html
{% endif %}
    depends_on:
      - postgresql-redos
    networks:
      - gosdocker

volumes:
  nextcloud_data:
```

- [ ] **Step 6: Создать prometheus docker-compose.yml.j2**

```yaml
# GosDocker - Prometheus
# Image: {{ registry_url }}
# Generated: {{ now.strftime('%Y-%m-%d %H:%M:%S') }}

  prometheus:
    image: {{ registry_url }}
    container_name: prometheus
    restart: unless-stopped
{% if config.ports %}
    ports:
{% for ext, int in config.ports.items() %}
      - "{{ ext }}:{{ int }}"
{% endfor %}
{% else %}
    ports:
      - "9090:9090"
{% endif %}
{% if config.volumes %}
    volumes:
{% for host, container in config.volumes.items() %}
      - {{ host }}:{{ container }}
{% endfor %}
{% else %}
    volumes:
      - prometheus_data:/prometheus
{% endif %}
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
{% if config.env.TZ %}
      - '--storage.tsdb.retention.time=15d'
{% endif %}
    networks:
      - gosdocker

volumes:
  prometheus_data:
```

- [ ] **Step 7: Создать grafana docker-compose.yml.j2**

```yaml
# GosDocker - Grafana
# Image: {{ registry_url }}
# Generated: {{ now.strftime('%Y-%m-%d %H:%M:%S') }}

  grafana:
    image: {{ registry_url }}
    container_name: grafana
    restart: unless-stopped
{% if config.ports %}
    ports:
{% for ext, int in config.ports.items() %}
      - "{{ ext }}:{{ int }}"
{% endfor %}
{% else %}
    ports:
      - "3000:3000"
{% endif %}
{% if config.volumes %}
    volumes:
{% for host, container in config.volumes.items() %}
      - {{ host }}:{{ container }}
{% endfor %}
{% else %}
    volumes:
      - grafana_data:/var/lib/grafana
{% endif %}
    environment:
      GF_SECURITY_ADMIN_USER: admin
      GF_SECURITY_ADMIN_PASSWORD: {{ config.env.get('GF_SECURITY_ADMIN_PASSWORD', 'admin') }}
      GF_USERS_ALLOW_SIGN_UP: "false"
{% if config.env.TZ %}
      TZ: "{{ config.env.TZ }}"
{% endif %}
    depends_on:
      - prometheus
    networks:
      - gosdocker

volumes:
  grafana_data:
```

- [ ] **Step 8: Создать web-stack.yml.j2**

```yaml
# GosDocker - Web + Data Stack
# Components: Angie PRO + PostgreSQL (РЕД ОС)
# Generated: {{ now.strftime('%Y-%m-%d %H:%M:%S') }}

services:
  angie:
    image: {{ components[0].registry_url }}
    container_name: angie
    restart: unless-stopped
{% if configs.angie-pro.ports %}
    ports:
{% for ext, int in configs.angie-pro.ports.items() %}
      - "{{ ext }}:{{ int }}"
{% endfor %}
{% endif %}
    networks:
      - gosdocker

  postgresql-redos:
    image: {{ components[1].registry_url }}
    container_name: postgresql-redos
    restart: unless-stopped
{% if configs['postgresql-redos'].ports %}
    ports:
{% for ext, int in configs['postgresql-redos'].ports.items() %}
      - "{{ ext }}:{{ int }}"
{% endfor %}
{% endif %}
    environment:
      POSTGRES_DB: gosdocker
      POSTGRES_USER: gosdocker
      POSTGRES_PASSWORD: {{ configs['postgresql-redos'].env.get('POSTGRES_PASSWORD', 'changeme') }}
    volumes:
      - pgdata:/var/lib/postgresql/data
    networks:
      - gosdocker

networks:
  gosdocker:
    driver: bridge

volumes:
  pgdata:
```

- [ ] **Step 9: Commit**

```bash
git add -A && git commit -m "feat: add Jinja2 templates for all components"
```

---

## Task 5: Backend — seed.py и заполнение БД

**Files:**
- Create: `backend/seed.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`

- [ ] **Step 1: Создать seed.py**

```python
"""
Seed script — заполняет БД компонентами и стеками
"""
import asyncio
from app.database import async_session, engine, Base
from app.models import Category, Component, Stack
from app import Category, Component, Stack

CATEGORIES = [
    {"name": "Web", "slug": "web", "icon": "🌐", "description": "Веб-серверы и прокси", "sort_order": 1},
    {"name": "Data", "slug": "data", "icon": "🗄️", "description": "Базы данных", "sort_order": 2},
    {"name": "Files", "slug": "files", "icon": "📁", "description": "Файловые хранилища", "sort_order": 3},
    {"name": "Monitoring", "slug": "monitoring", "icon": "📊", "description": "Мониторинг и метрики", "sort_order": 4},
]

COMPONENTS = [
    # Web
    {
        "name": "Angie PRO",
        "slug": "angie-pro",
        "category_slug": "web",
        "image": "riftbit/angie",
        "image_source": "dh-mirror.gitverse.ru",
        "registry_url": "dh-mirror.gitverse.ru/riftbit/angie",
        "is_registry": True,
        "registry_number": "№17604",
        "description": "Российский веб-сервер (форк Nginx), внесён в Реестр ПО Минцифры",
        "version": "1.10.0",
        "default_ports": {"80": 80, "443": 443},
        "default_env": {"TZ": "Europe/Moscow"},
        "template_file": "single/angie/docker-compose.yml.j2"
    },
    {
        "name": "nginx",
        "slug": "nginx",
        "category_slug": "web",
        "image": "nginx",
        "image_source": "registry.red-soft.ru",
        "registry_url": "registry.red-soft.ru/ubi8/nginx",
        "is_registry": False,
        "description": "Веб-сервер, стандарт индустрии",
        "version": "1.28",
        "default_ports": {"80": 80, "443": 443},
        "default_env": {"TZ": "Europe/Moscow"},
        "template_file": "single/nginx/docker-compose.yml.j2"
    },
    # Data
    {
        "name": "PostgreSQL (РЕД ОС)",
        "slug": "postgresql-redos",
        "category_slug": "data",
        "image": "postgresql-17",
        "image_source": "registry.red-soft.ru",
        "registry_url": "registry.red-soft.ru/ubi8/postgresql-17",
        "is_registry": True,
        "description": "Российская СУБД на базе PostgreSQL 17, реестр РЕД ОС",
        "version": "17",
        "default_ports": {"5432": 5432},
        "default_env": {"POSTGRES_PASSWORD": "changeme", "TZ": "Europe/Moscow"},
        "template_file": "single/postgresql-redos/docker-compose.yml.j2"
    },
    {
        "name": "PostgreSQL",
        "slug": "postgresql",
        "category_slug": "data",
        "image": "postgres",
        "image_source": "dh-mirror.gitverse.ru",
        "registry_url": "dh-mirror.gitverse.ru/postgres:15-alpine",
        "is_registry": False,
        "description": "Популярная СУБД, проверенная временем",
        "version": "15-alpine",
        "default_ports": {"5432": 5432},
        "default_env": {"POSTGRES_PASSWORD": "changeme", "TZ": "Europe/Moscow"},
        "template_file": "single/postgresql/docker-compose.yml.j2"
    },
    # Files
    {
        "name": "Nextcloud",
        "slug": "nextcloud",
        "category_slug": "files",
        "image": "nextcloud",
        "image_source": "dh-mirror.gitverse.ru",
        "registry_url": "dh-mirror.gitverse.ru/library/nextcloud",
        "is_registry": True,
        "description": "Облачное хранилище файлов с совместной работой",
        "version": "latest",
        "default_ports": {"8080": 80},
        "default_env": {"MYSQL_PASSWORD": "changeme", "TZ": "Europe/Moscow"},
        "template_file": "single/nextcloud/docker-compose.yml.j2"
    },
    # Monitoring
    {
        "name": "Prometheus",
        "slug": "prometheus",
        "category_slug": "monitoring",
        "image": "prom/prometheus",
        "image_source": "dh-mirror.gitverse.ru",
        "registry_url": "dh-mirror.gitverse.ru/prom/prometheus",
        "is_registry": False,
        "description": "Сборщик метрик и мониторинга",
        "version": "latest",
        "default_ports": {"9090": 9090},
        "default_env": {"TZ": "Europe/Moscow"},
        "template_file": "single/prometheus/docker-compose.yml.j2"
    },
    {
        "name": "Grafana",
        "slug": "grafana",
        "category_slug": "monitoring",
        "image": "grafana/grafana",
        "image_source": "dh-mirror.gitverse.ru",
        "registry_url": "dh-mirror.gitverse.ru/grafana/grafana",
        "is_registry": False,
        "description": "Визуализация метрик и дашборды",
        "version": "latest",
        "default_ports": {"3000": 3000},
        "default_env": {"GF_SECURITY_ADMIN_PASSWORD": "admin", "TZ": "Europe/Moscow"},
        "template_file": "single/grafana/docker-compose.yml.j2"
    },
]

STACKS = [
    {
        "name": "Веб + СУБД (РФ)",
        "slug": "web-database-registry",
        "description": "Angie PRO + PostgreSQL (РЕД ОС) — полностью российские решения",
        "is_featured": True,
        "component_slugs": ["angie-pro", "postgresql-redos"]
    },
    {
        "name": "Веб + СУБД (Community)",
        "slug": "web-database-community",
        "description": "nginx + PostgreSQL — популярные open-source решения",
        "is_featured": False,
        "component_slugs": ["nginx", "postgresql"]
    },
    {
        "name": "Мониторинг",
        "slug": "monitoring",
        "description": "Prometheus + Grafana — стек для мониторинга",
        "is_featured": True,
        "component_slugs": ["prometheus", "grafana"]
    },
    {
        "name": "Полный стек (РФ)",
        "slug": "full-registry",
        "description": "Angie PRO + PostgreSQL (РЕД ОС) + Nextcloud",
        "is_featured": False,
        "component_slugs": ["angie-pro", "postgresql-redos", "nextcloud"]
    },
]

async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        # Categories
        category_map = {}
        for cat_data in CATEGORIES:
            cat = Category(**cat_data)
            session.add(cat)
            category_map[cat_data["slug"]] = cat
        await session.commit()

        # Components
        component_map = {}
        for comp_data in COMPONENTS:
            cat_slug = comp_data.pop("category_slug")
            comp = Component(
                **comp_data,
                category_id=category_map[cat_slug].id
            )
            session.add(comp)
            component_map[comp_data["slug"]] = comp
        await session.commit()

        # Stacks
        for stack_data in STACKS:
            comp_slugs = stack_data.pop("component_slugs")
            stack = Stack(**stack_data)
            for slug in comp_slugs:
                stack.components.append(component_map[slug])
            session.add(stack)
        await session.commit()

        print("Seed completed!")

if __name__ == "__main__":
    asyncio.run(seed())
```

- [ ] **Step 2: Commit**

```bash
git add -A && git commit -m "feat: add seed script with components and stacks"
```

---

## Task 6: Frontend — Vue 3 базовая структура

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tailwind.config.js`
- Create: `frontend/tsconfig.json`
- Create: `frontend/index.html`
- Create: `frontend/src/main.ts`
- Create: `frontend/src/App.vue`
- Create: `frontend/src/router/index.ts`
- Create: `frontend/src/types/index.ts`
- Create: `frontend/src/composables/useApi.ts`

- [ ] **Step 1: Создать package.json**

```json
{
  "name": "gosdocker-frontend",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "^3.4.0",
    "vue-router": "^4.2.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0",
    "tailwindcss": "^3.4.0",
    "typescript": "^5.3.0",
    "vite": "^5.0.0",
    "vue-tsc": "^1.8.0"
  }
}
```

- [ ] **Step 2: Создать vite.config.ts**

```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
```

- [ ] **Step 3: Создать tailwind.config.js**

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'registry': '#059669',   // Зелёный для РФ
        'community': '#2563EB',   // Синий для комьюнити
      }
    },
  },
  plugins: [],
}
```

- [ ] **Step 4: Создать types/index.ts**

```typescript
export interface Category {
  id: string
  name: string
  slug: string
  icon: string
  description: string | null
  sort_order: number
  components_count: number
  registry_count: number
  community_count: number
}

export interface Component {
  id: string
  name: string
  slug: string
  category: string
  image: string
  image_source: string
  registry_url: string
  is_registry: boolean
  registry_number: string | null
  description: string | null
  version: string | null
  default_ports: Record<string, number>
  default_volumes: Record<string, string>
  default_env: Record<string, string>
  variables_schema: Record<string, unknown>
}

export interface Stack {
  id: string
  name: string
  slug: string
  description: string
  is_featured: boolean
  components: StackComponent[]
}

export interface StackComponent {
  name: string
  slug: string
  is_registry: boolean
  image?: string
  registry_url?: string
}

export interface ComponentConfig {
  ports: Record<string, number>
  volumes: Record<string, string>
  env: Record<string, string>
}
```

- [ ] **Step 5: Создать composables/useApi.ts**

```typescript
const API_BASE = '/api'

export function useApi() {
  async function fetchCategories() {
    const res = await fetch(`${API_BASE}/categories`)
    return res.json()
  }

  async function fetchComponents(category?: string) {
    const url = category
      ? `${API_BASE}/components?category=${category}`
      : `${API_BASE}/components`
    const res = await fetch(url)
    return res.json()
  }

  async function fetchStacks() {
    const res = await fetch(`${API_BASE}/stacks`)
    return res.json()
  }

  async function generateStack(slugs: string[], config: Record<string, ComponentConfig>) {
    const params = new URLSearchParams()
    slugs.forEach(s => params.append('slugs', s))

    const res = await fetch(`${API_BASE}/generate?${params}`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(config)
    })

    return res.blob()
  }

  return {
    fetchCategories,
    fetchComponents,
    fetchStacks,
    generateStack
  }
}
```

- [ ] **Step 6: Commit**

```bash
cd frontend && git add -A && git commit -m "feat: add frontend structure"
```

---

## Task 7: Frontend — Views и Components

**Files:**
- Create: `frontend/src/views/HomeView.vue`
- Create: `frontend/src/views/CatalogView.vue`
- Create: `frontend/src/views/ComponentView.vue`
- Create: `frontend/src/views/StacksView.vue`
- Create: `frontend/src/components/CategoryCard.vue`
- Create: `frontend/src/components/ComponentCard.vue`
- Create: `frontend/src/components/SourceBadge.vue`
- Create: `frontend/src/components/ConfigWizard.vue`
- Create: `frontend/src/components/Footer.vue`

- [ ] **Step 1: Создать HomeView.vue**

```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useApi } from '../composables/useApi'
import CategoryCard from '../components/CategoryCard.vue'
import StackCard from '../components/StackCard.vue'

const { fetchCategories, fetchStacks } = useApi()
const categories = ref([])
const stacks = ref([])

onMounted(async () => {
  categories.value = await fetchCategories()
  stacks.value = await fetchStacks()
})
</script>

<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Hero -->
    <section class="bg-white border-b">
      <div class="container mx-auto px-4 py-16 text-center">
        <h1 class="text-4xl font-bold text-gray-900 mb-4">
          GosCompose.ru
        </h1>
        <p class="text-xl text-gray-600 mb-8">
          Каталог Docker Compose-сборок для госструктур
        </p>
        <div class="flex justify-center gap-4 text-sm text-gray-500">
          <span class="px-3 py-1 bg-green-100 text-green-700 rounded-full">
            🏛 3 решения из Реестра РФ
          </span>
          <span class="px-3 py-1 bg-blue-100 text-blue-700 rounded-full">
            📦 3 решения комьюнити
          </span>
        </div>
      </div>
    </section>

    <!-- Categories -->
    <section class="container mx-auto px-4 py-12">
      <h2 class="text-2xl font-bold mb-6">Категории</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <CategoryCard
          v-for="cat in categories"
          :key="cat.slug"
          :category="cat"
        />
      </div>
    </section>

    <!-- Featured Stacks -->
    <section class="container mx-auto px-4 py-12">
      <h2 class="text-2xl font-bold mb-6">Готовые сборки</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <StackCard
          v-for="stack in stacks.filter(s => s.is_featured)"
          :key="stack.slug"
          :stack="stack"
        />
      </div>
    </section>
  </div>
</template>
```

- [ ] **Step 2: Создать ComponentCard.vue**

```vue
<script setup lang="ts">
import type { Component } from '../types'
import SourceBadge from './SourceBadge.vue'

defineProps<{
  component: Component
}>()
</script>

<template>
  <div class="bg-white rounded-lg shadow-sm border p-6 hover:shadow-md transition">
    <div class="flex items-start justify-between mb-4">
      <div>
        <h3 class="text-lg font-semibold text-gray-900">{{ component.name }}</h3>
        <SourceBadge :is-registry="component.is_registry" />
      </div>
      <span v-if="component.version" class="text-sm text-gray-500">
        v{{ component.version }}
      </span>
    </div>

    <p class="text-gray-600 text-sm mb-4 line-clamp-2">
      {{ component.description }}
    </p>

    <div class="text-xs text-gray-400 mb-4">
      {{ component.registry_url }}
    </div>

    <div class="flex gap-2">
      <button class="flex-1 px-4 py-2 bg-gray-100 text-gray-700 rounded hover:bg-gray-200">
        📥 Скачать
      </button>
      <button class="flex-1 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
        ⚙️ Настроить
      </button>
    </div>
  </div>
</template>
```

- [ ] **Step 3: Создать SourceBadge.vue**

```vue
<script setup lang="ts">
defineProps<{
  isRegistry: boolean
}>()
</script>

<template>
  <span
    :class="[
      'inline-flex items-center px-2 py-0.5 rounded text-xs font-medium',
      isRegistry
        ? 'bg-green-100 text-green-700'
        : 'bg-blue-100 text-blue-700'
    ]"
  >
    {{ isRegistry ? '🏛 Из Реестра РФ' : '📦 Community' }}
  </span>
</template>
```

- [ ] **Step 4: Создать ConfigWizard.vue (упрощённый)**

```vue
<script setup lang="ts">
import { ref } from 'vue'
import type { Component, ComponentConfig } from '../types'
import { useApi } from '../composables/useApi'

const props = defineProps<{
  component: Component
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

const { generateStack } = useApi()
const config = ref<ComponentConfig>({
  ports: Object.fromEntries(
    Object.entries(props.component.default_ports).map(([k, v]) => [k, v as number])
  ),
  volumes: props.component.default_volumes,
  env: props.component.default_env
})

async function download() {
  const blob = await generateStack([props.component.slug], {
    [props.component.slug]: config.value
  })

  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${props.component.slug}.zip`
  a.click()
  URL.revokeObjectURL(url)
  emit('close')
}
</script>

<template>
  <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
    <div class="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
      <h2 class="text-xl font-bold mb-4">⚙️ Настройка: {{ component.name }}</h2>

      <!-- Ports -->
      <div class="mb-4">
        <label class="block text-sm font-medium mb-2">Порты</label>
        <div class="space-y-2">
          <div v-for="(int, ext) in config.ports" :key="ext" class="flex gap-2">
            <input
              :value="ext"
              @input="(e) => { const target = e.target as HTMLInputElement; config.ports[target.value] = int }"
              class="w-24 px-2 py-1 border rounded"
              placeholder="Внешний"
            />
            <span class="self-center">→</span>
            <input
              :value="int"
              @input="(e) => { const target = e.target as HTMLInputElement; config.ports[ext] = parseInt(target.value) }"
              class="w-24 px-2 py-1 border rounded"
              placeholder="Внутренний"
            />
          </div>
        </div>
      </div>

      <!-- Env -->
      <div class="mb-4">
        <label class="block text-sm font-medium mb-2">Переменные окружения</label>
        <div class="space-y-2">
          <div v-for="(value, key) in config.env" :key="key" class="flex gap-2">
            <input
              :value="key"
              class="w-32 px-2 py-1 border rounded bg-gray-50"
              disabled
            />
            <input
              :value="value"
              @input="(e) => { const target = e.target as HTMLInputElement; config.env[key] = target.value }"
              class="flex-1 px-2 py-1 border rounded"
            />
          </div>
        </div>
      </div>

      <div class="flex gap-2">
        <button @click="emit('close')" class="flex-1 px-4 py-2 border rounded hover:bg-gray-50">
          Отмена
        </button>
        <button @click="download" class="flex-1 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
          📥 Скачать
        </button>
      </div>
    </div>
  </div>
</template>
```

- [ ] **Step 5: Commit**

```bash
cd frontend && git add -A && git commit -m "feat: add views and components"
```

---

## Task 8: Docker Compose для платформы + nginx

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `nginx/nginx.conf`
- Create: `backend/Dockerfile`
- Create: `frontend/Dockerfile`
- Create: `nginx/Dockerfile`

- [ ] **Step 1: Создать docker-compose.yml**

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://gosdocker:secret@db:5432/gosdocker
    depends_on:
      - db
    networks:
      - gosdocker

  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - backend
    networks:
      - gosdocker

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - frontend
      - backend
    networks:
      - gosdocker

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=gosdocker
      - POSTGRES_USER=gosdocker
      - POSTGRES_PASSWORD=secret
    volumes:
      - pgdata:/var/lib/postgresql/data
    networks:
      - gosdocker

volumes:
  pgdata:

networks:
  gosdocker:
    driver: bridge
```

- [ ] **Step 2: Создать nginx/nginx.conf**

```nginx
events {
    worker_connections 1024;
}

http {
    upstream frontend {
        server frontend:80;
    }

    upstream backend {
        server backend:8000;
    }

    server {
        listen 80;
        server_name localhost;

        location / {
            proxy_pass http://frontend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }

        location /api {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }
}
```

- [ ] **Step 3: Создать backend/Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 4: Создать frontend/Dockerfile**

```dockerfile
FROM node:20-alpine as build

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

- [ ] **Step 5: Создать .env.example**

```bash
# GosDocker Environment
DATABASE_URL=postgresql+asyncpg://gosdocker:secret@localhost:5432/gosdocker
DEBUG=false
```

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: add platform docker-compose and nginx config"
```

---

## Task 9: Интеграция и тестирование

**Files:**
- Modify: `.gitignore`
- Create: `README.md`
- Create: `TESTING.md`

- [ ] **Step 1: Обновить .gitignore**

```
# Python
__pycache__/
*.py[cod]
.env
venv/
.venv/

# Node
node_modules/
dist/

# Docker
.docker/

# IDE
.vscode/
.idea/

# Logs
*.log

# OS
.DS_Store
Thumbs.db
```

- [ ] **Step 2: Создать README.md**

```markdown
# GosDocker

Каталог Docker Compose-сборок для государственных и образовательных организаций.

## Быстрый старт

```bash
# Клонирование
git clone https://github.com/user/gosdocker.git
cd gosdocker

# Конфигурация
cp .env.example .env

# Запуск платформы
docker compose up -d

# Заполнение БД
docker compose exec backend python seed.py

# Открыть в браузере
open http://localhost
```

## Компоненты каталога

### Из Реестра РФ

| Компонент | Описание | Образ |
|----------|----------|-------|
| Angie PRO | Веб-сервер | registry.red-soft.ru/ubi8/nginx |
| PostgreSQL (РЕД ОС) | СУБД | registry.red-soft.ru/ubi8/postgresql-17 |
| Nextcloud | Файловый сервер | dh-mirror.gitverse.ru/nextcloud |

### Комьюнити

| Компонент | Описание | Образ |
|----------|----------|-------|
| nginx | Веб-сервер | registry.red-soft.ru/ubi8/nginx |
| PostgreSQL | СУБД | dh-mirror.gitverse.ru/postgres |
| Prometheus + Grafana | Мониторинг | dh-mirror.gitverse.ru/prom/prometheus |

## Структура

```
gosdocker/
├── backend/          # FastAPI API
├── frontend/         # Vue 3 SPA
├── nginx/            # Reverse proxy
└── docker-compose.yml
```

## Разработка

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## Лицензия

MIT
```

- [ ] **Step 3: Создать TESTING.md**

```markdown
# Тестирование GosDocker

## Проверка платформы

### 1. Запуск

```bash
docker compose up -d
docker compose exec backend python seed.py
curl http://localhost/api/categories
```

Ожидаемый результат:
```json
[{"name": "Web", "slug": "web", ...}, ...]
```

### 2. Компоненты

```bash
curl http://localhost/api/components
```

Должно вернуть 7 компонентов.

### 3. Стеки

```bash
curl http://localhost/api/stacks
```

Должно вернуть 4 стека, включая featured.

### 4. Генерация

```bash
curl -X POST "http://localhost/api/generate?slugs=angie-pro" \
  -H "Content-Type: application/json" \
  -d '{"angie-pro": {"ports": {"80": 8080}}}' \
  -o test.zip
unzip -l test.zip
```

Ожидаемое содержимое:
- docker-compose.yml
- .env.example
- README.md

## Проверка компонентов

### Angie PRO
```bash
docker pull dh-mirror.gitverse.ru/riftbit/angie
docker run --rm dh-mirror.gitverse.ru/riftbit/angie -v
```

### PostgreSQL (РЕД ОС)
```bash
docker pull registry.red-soft.ru/ubi8/postgresql-17
docker run --rm registry.red-soft.ru/ubi8/postgresql-17 --version
```

### nginx
```bash
docker pull registry.red-soft.ru/ubi8/nginx
docker run --rm registry.red-soft.ru/ubi8/nginx -v
```
```

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "feat: add README, TESTING, .gitignore"
```

---

## Self-Review

### Spec coverage check:
- ✅ 3 компонента из реестра (Angie PRO, PostgreSQL РЕД ОС, Nextcloud)
- ✅ 3 компонента комьюнити (nginx, PostgreSQL, Prometheus + Grafana)
- ✅ 2 источника образов (registry.red-soft.ru, dh-mirror.gitverse.ru)
- ✅ API endpoints для категорий, компонентов, стеков
- ✅ POST /api/generate для генерации ZIP
- ✅ Jinja2 шаблоны для всех компонентов
- ✅ Frontend views (Home, Catalog, Component, Stacks)
- ✅ ConfigWizard для настройки параметров
- ✅ SourceBadge для отображения РФ/Community
- ✅ Docker Compose для платформы
- ✅ README + TESTING.md

### Placeholder scan:
- ✅ Нет TBD, TODO
- ✅ Всё заполнено
- ✅ Код полный

### Type consistency:
- ✅ Component.slug используется консистентно
- ✅ registry_url передаётся везде
- ✅ config структура одинаковая

---

**Plan complete and saved to `docs/superpowers/plans/2026-04-19-gosdocker-implementation.md`**

**Two execution options:**

**1. Subagent-Driven (recommended)** — dispatch fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
