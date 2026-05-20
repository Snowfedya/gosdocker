"""
Seed script — fills database with components and stacks.
"""
import asyncio
from app.database import async_session, engine, Base
from app.models import Category, Component, Stack

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
        "image_source": "dh-mirror.gitverse.ru",
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
        "name": "PostgreSQL РЕД ОС",
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
        "default_env": {"POSTGRES_PASSWORD": "changeme", "TZ": "Europe/Moscow"},
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
        "description": "Angie PRO + PostgreSQL (РЕД ОС) + Nextcloud — все компоненты из Реестра РФ",
        "is_featured": True,
        "component_slugs": ["angie-pro", "postgresql-redos", "nextcloud"]
    },
    {
        "name": "Полный стек Community",
        "slug": "full-community",
        "description": "nginx + PostgreSQL + Prometheus + Grafana — все open-source компоненты",
        "is_featured": False,
        "component_slugs": ["nginx", "postgresql", "prometheus", "grafana"]
    },
]


async def seed():
    """Seed the database with categories, components, and stacks."""
    # Create tables
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

        print(f"Seeded {len(CATEGORIES)} categories, {len(COMPONENTS)} components, {len(STACKS)} stacks")


if __name__ == "__main__":
    asyncio.run(seed())
