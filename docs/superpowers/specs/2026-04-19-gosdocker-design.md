# GosDocker — Спецификация

> **Тип проекта:** FULL-STACK (Backend + Frontend + Infrastructure)
> **Дата:** 2026-04-19
> **Домен:** GosCompose.ru
> **Версия:** 1.0
> **Статус:** Финальная

---

## 1. Концепция и цель

### 1.1 Назначение

Веб-платформа **GosDocker** (GosCompose.ru) — каталог готовых Docker Compose-сборок для государственных и образовательных организаций. Позволяет системным администраторам быстро развёртывать проверенное ПО без глубокого знания Docker.

### 1.2 Ключевые особенности

- **3 компонента из Реестра РФ** — решения для импортозамещения
- **3 компонента комьюнити** — популярные open-source альтернативы
- **Два режима использования:**
  - Готовые сборки для скачивания
  - Конфигуратор для настройки параметров
- **Источники образов из РФ** — работает в условиях санкций

### 1.3 Для кого

- Сисадмины государственных учреждений
- Сисадмины образовательных организаций
- Организации с политикой импортозамещения

---

## 2. Компоненты каталога

### 2.1 Из Реестра РФ (3)

| # | Компонент | Категория | Описание | Образ | Источник |
|---|----------|-----------|---------|-------|----------|
| 1 | **Angie PRO** | Web | Российский веб-сервер (форк Nginx), внесён в Реестр ПО Минцифры №17604 | `riftbit/angie` | `dh-mirror.gitverse.ru` |
| 2 | **PostgreSQL (РЕД ОС)** | Data | Российская СУБД на базе PostgreSQL 17, реестр РЕД ОС | `registry.red-soft.ru/ubi8/postgresql-17` | `registry.red-soft.ru` |
| 3 | **Nextcloud** | Files | Облачное хранилище файлов с совместной работой | `nextcloud` | `dh-mirror.gitverse.ru` |

### 2.2 Комьюнити (3)

| # | Компонент | Категория | Описание | Образ | Источник |
|---|----------|-----------|---------|-------|----------|
| 1 | **nginx** | Web | Веб-сервер, стандарт индустрии | `registry.red-soft.ru/ubi8/nginx` | `registry.red-soft.ru` |
| 2 | **PostgreSQL** | Data | Популярная СУБД, проверенная временем | `postgres:15-alpine` | `dh-mirror.gitverse.ru` |
| 3 | **Prometheus + Grafana** | Monitoring | Мониторинг и визуализация метрик | `prom/prometheus`, `grafana/grafana` | `dh-mirror.gitverse.ru` |

### 2.3 Покрытие категорий

| Категория | Из реестра | Комьюнити | Балансировка |
|-----------|------------|-----------|--------------|
| **Web** | Angie PRO | nginx | ✅ nginx/Angie upstream |
| **Data** | PostgreSQL (РЕД ОС) | PostgreSQL | — |
| **Files** | Nextcloud | — | — |
| **Monitoring** | — | Prometheus + Grafana | — |

---

## 3. Источники Docker-образов

### 3.1 Основные источники

```
┌─────────────────────────────────────────────────────────────────┐
│                     ИСТОЧНИКИ ОБРАЗОВ                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ registry.red-soft.ru (РЕД ОС)                            │   │
│  │ • Публичный реестр РЕД СОФТ                              │   │
│  │ • Не требует авторизации                                 │   │
│  │ • Основной источник для РФ-образов                       │   │
│  │                                                         │   │
│  │ Образы: nginx, postgresql-17, httpd, gitea, golang      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ dh-mirror.gitverse.ru (GitVerse, Сбер)                  │   │
│  │ • Зеркало Docker Hub                                    │   │
│  │ • Для образов без РФ-аналогов                           │   │
│  │ • Создано после блокировки Docker Hub (30.05.2024)      │   │
│  │                                                         │   │
│  │ Образы: Angie, Nextcloud, postgres, prometheus, grafana │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Приоритеты использования

| Компонент | Основной источник | Резервный источник |
|-----------|-------------------|-------------------|
| **nginx** | `registry.red-soft.ru` | `dh-mirror.gitverse.ru` |
| **postgresql** (РЕД ОС) | `registry.red-soft.ru` | — |
| **Angie PRO** | `dh-mirror.gitverse.ru` | `docker.angie.software` |
| **Nextcloud** | `dh-mirror.gitverse.ru` | `nextcloud` (Docker Hub) |
| **PostgreSQL** | `dh-mirror.gitverse.ru` | `postgres` (Docker Hub) |
| **Prometheus** | `dh-mirror.gitverse.ru` | `prom` (Docker Hub) |
| **Grafana** | `dh-mirror.gitverse.ru` | `grafana` (Docker Hub) |

### 3.3 Почему выбраны эти источники

| Источник | Преимущества | Примечание |
|----------|--------------|------------|
| **registry.red-soft.ru** | Российская компания, бесплатно, надёжно | Для nginx, postgresql |
| **dh-mirror.gitverse.ru** | Полный Docker Hub, backup от Сбера | Для остального |

---

## 4. Архитектура платформы

### 4.1 Tech Stack

| Слой | Технология | Версия |
|------|------------|--------|
| **Frontend** | Vue 3 + Vite + TailwindCSS | 3.4+ |
| **TypeScript** | TypeScript | 5.0+ |
| **Backend** | FastAPI | 0.100+ |
| **ORM** | SQLAlchemy 2.0 (Async) | 2.0+ |
| **Database** | PostgreSQL 15 | 15+ |
| **Templates** | Jinja2 | 3.1+ |
| **Orchestration** | Docker Compose | 2.0+ |

### 4.2 Структура проекта

```
gosdocker/
├── docker-compose.yml              # Orchestrator (platform)
├── .env.example                   # Environment template
├── README.md                       # Documentation
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/
│   │   └── versions/              # DB migrations
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                # FastAPI entry point
│   │   ├── config.py              # Pydantic Settings
│   │   ├── database.py            # Async SQLAlchemy engine
│   │   ├── models/                # SQLAlchemy models
│   │   │   ├── __init__.py
│   │   │   ├── component.py       # Component entity
│   │   │   ├── category.py        # Category entity
│   │   │   ├── stack.py           # Pre-built stack
│   │   │   └── template.py        # Jinja2 template
│   │   ├── schemas/               # Pydantic schemas
│   │   │   ├── __init__.py
│   │   │   ├── component.py
│   │   │   └── generate.py        # Generation request
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── router.py
│   │   │   ├── categories.py       # GET /api/categories
│   │   │   ├── components.py      # GET /api/components
│   │   │   ├── stacks.py          # GET /api/stacks
│   │   │   └── generate.py        # POST /api/generate
│   │   ├── services/
│   │   │   ├── template_service.py  # Jinja2 rendering
│   │   │   └── generate_service.py   # ZIP creation
│   │   └── templates/             # Jinja2 templates
│   │       ├── angie/
│   │       │   └── docker-compose.yml.j2
│   │       ├── nginx/
│   │       │   └── docker-compose.yml.j2
│   │       ├── postgresql-redos/
│   │       │   └── docker-compose.yml.j2
│   │       ├── postgresql/
│   │       │   └── docker-compose.yml.j2
│   │       ├── nextcloud/
│   │       │   └── docker-compose.yml.j2
│   │       ├── prometheus/
│   │       │   └── docker-compose.yml.j2
│   │       ├── grafana/
│   │       │   └── docker-compose.yml.j2
│   │       └── stacks/
│   │           ├── web-stack.yml.j2
│   │           └── full-stack.yml.j2
│   └── seed.py                    # Database seeder
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
│       ├── router/
│       │   └── index.ts
│       ├── views/
│       │   ├── HomeView.vue       # Landing page
│       │   ├── CatalogView.vue    # Categories grid
│       │   ├── CategoryView.vue   # Components list
│       │   ├── ComponentView.vue   # Component detail
│       │   └── StacksView.vue      # Pre-built stacks
│       ├── components/
│       │   ├── CategoryCard.vue
│       │   ├── ComponentCard.vue
│       │   ├── StackCard.vue
│       │   ├── SourceBadge.vue    # РФ / Community
│       │   ├── ConfigWizard.vue    # Configuration modal
│       │   ├── GenerateButton.vue
│       │   └── Footer.vue
│       ├── composables/
│       │   ├── useCategories.ts
│       │   ├── useComponents.ts
│       │   ├── useStacks.ts
│       │   └── useGenerate.ts
│       ├── types/
│       │   └── index.ts
│       └── assets/
│           ├── logo.svg
│           └── main.css
└── nginx/
    ├── Dockerfile
    └── nginx.conf                 # Reverse proxy config
```

---

## 5. Модели данных

### 5.1 Category (Категория)

```python
class Category(SQLModel, table=True):
    id: UUID = Field(primary_key=True)
    name: str                      # "Web", "Data", "Files", "Monitoring"
    slug: str                      # "web", "data", "files", "monitoring"
    icon: str                      # emoji или icon class
    description: str              # Краткое описание категории
    sort_order: int = 0           # Для сортировки
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

### 5.2 Component (Компонент)

```python
class Component(SQLModel, table=True):
    id: UUID = Field(primary_key=True)
    name: str                      # "Angie PRO", "PostgreSQL (РЕД ОС)"
    slug: str                      # "angie-pro", "postgresql-redos"
    category_id: UUID = Field(foreign_key="category.id")

    # Docker
    image: str                      # "riftbit/angie"
    image_source: str               # "registry.red-soft.ru" / "dh-mirror.gitverse.ru"
    registry_url: str               # Полный URL для pull

    # Метаданные
    description: str               # Описание компонента
    version: str                   # Рекомендуемая версия
    is_registry: bool             # True = из реестра РФ

    # Настройки по умолчанию
    default_ports: dict            # {"80": 80, "443": 443}
    default_volumes: dict          # {"/data": "/var/lib/data"}
    default_env: dict              # {"TZ": "Europe/Moscow"}

    # Конфигурация
    variables_schema: dict         # JSON schema для ConfigWizard
    template_file: str            # Путь к Jinja2 шаблону

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

### 5.3 Stack (Готовая сборка)

```python
class Stack(SQLModel, table=True):
    id: UUID = Field(primary_key=True)
    name: str                      # "Веб-сервер + СУБД"
    slug: str                      # "web-database-stack"
    description: str               # Описание сборки
    components: list[UUID]        # Список ID компонентов
    is_featured: bool = False     # Показать на главной
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

### 5.4 ER-диаграмма

```
┌─────────────────┐       ┌─────────────────┐
│    Category     │       │     Stack        │
├─────────────────┤       ├─────────────────┤
│ id (PK)         │       │ id (PK)         │
│ name            │       │ name            │
│ slug            │       │ slug            │
│ icon            │       │ description     │
│ description     │       │ is_featured     │
│ sort_order      │       │ created_at       │
│ created_at      │       └────────┬────────┘
└───────┬─────────┘                │
        │                          │
        │ 1:N                     M:N
        ▼                          │
┌─────────────────┐       ┌───────┴─────────┐
│   Component     │◄──────│   StackComponent │
├─────────────────┤       └─────────────────┘
│ id (PK)         │
│ name            │
│ slug            │
│ category_id(FK) │
│ image          │
│ image_source   │
│ registry_url   │
│ description    │
│ version        │
│ is_registry    │
│ default_ports  │
│ default_volumes│
│ default_env    │
│ variables_schema│
│ template_file  │
│ created_at     │
│ updated_at     │
└─────────────────┘
```

---

## 6. API Endpoints

### 6.1 Categories

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/categories` | Список всех категорий |
| GET | `/api/categories/{slug}` | Одна категория с компонентами |

**GET /api/categories response:**
```json
{
  "categories": [
    {
      "id": "uuid",
      "name": "Web",
      "slug": "web",
      "icon": "🌐",
      "description": "Веб-серверы и прокси",
      "components_count": 2,
      "registry_count": 1,
      "community_count": 1
    }
  ]
}
```

### 6.2 Components

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/components` | Все компоненты (с фильтрами) |
| GET | `/api/components/{slug}` | Один компонент с шаблоном |

**GET /api/components?category=web response:**
```json
{
  "components": [
    {
      "id": "uuid",
      "name": "Angie PRO",
      "slug": "angie-pro",
      "category": "web",
      "image": "riftbit/angie",
      "image_source": "dh-mirror.gitverse.ru",
      "is_registry": true,
      "registry_number": "№17604",
      "description": "Российский веб-сервер (форк Nginx)",
      "version": "1.10.0",
      "default_ports": {"80": 80, "443": 443},
      "default_env": {"TZ": "Europe/Moscow"}
    }
  ]
}
```

### 6.3 Stacks

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/stacks` | Готовые сборки |
| GET | `/api/stacks/{slug}` | Одна сборка с компонентами |

**GET /api/stacks response:**
```json
{
  "stacks": [
    {
      "id": "uuid",
      "name": "Веб + СУБД",
      "slug": "web-database",
      "description": "Angie PRO + PostgreSQL (РЕД ОС)",
      "is_featured": true,
      "components": [
        {"name": "Angie PRO", "slug": "angie-pro", "is_registry": true},
        {"name": "PostgreSQL (РЕД ОС)", "slug": "postgresql-redos", "is_registry": true}
      ]
    }
  ]
}
```

### 6.4 Generate

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/generate` | Генерация docker-compose |

**POST /api/generate request:**
```json
{
  "components": ["angie-pro", "postgresql-redos"],
  "config": {
    "angie-pro": {
      "ports": {"80": 8080},
      "volumes": {"/data": "/var/www/data"},
      "env": {"DOMAIN": "gos.server.ru"}
    },
    "postgresql-redos": {
      "ports": {"5432": 5432},
      "volumes": {"/pgdata": "/var/lib/postgresql/data"},
      "env": {"POSTGRES_PASSWORD": "changeme"}
    }
  },
  "include_sources": true
}
```

**POST /api/generate response:**
```json
{
  "filename": "gosdocker-stack-20260419.zip",
  "size_bytes": 4096,
  "files": [
    "docker-compose.yml",
    ".env.example",
    "README.md"
  ]
}
```

---

## 7. Frontend Views

### 7.1 HomeView (Главная страница)

```
┌──────────────────────────────────────────────────────────────┐
│  GosCompose.ru                                               │
│  ────────────────────────────────────────────────────────   │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐   │
│  │  Каталог Docker Compose-сборок для госструктур       │   │
│  │                                                        │   │
│  │  3 решения из Реестра РФ                              │   │
│  │  3 решения комьюнити                                   │   │
│  │  Готовые сборки + Конфигуратор                        │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │   🌐     │  │   🗄️     │  │   📁     │  │   📊     │      │
│  │   Web    │  │   Data   │  │  Files   │  │ Monitor  │      │
│  │  2 + 2   │  │  1 + 1   │  │    1    │  │   0+2    │      │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘      │
│                                                              │
│  Готовые сборки:                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ 🏛 Веб + СУБД (РФ)                                      │ │
│  │    Angie PRO + PostgreSQL (РЕД ОС)                       │ │
│  │    [Скачать] [Настроить]                                │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ 📊 Мониторинг                                           │ │
│  │    Prometheus + Grafana                                 │ │
│  │    [Скачать] [Настроить]                                │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ────────────────────────────────────────────────────────   │
│  © 2026 GosCompose.ru | Источники образов                   │
└──────────────────────────────────────────────────────────────┘
```

### 7.2 ComponentView (Детали компонента)

```
┌──────────────────────────────────────────────────────────────┐
│  ← Назад к Web                                              │
│  ────────────────────────────────────────────────────────   │
│                                                              │
│  ┌──────────────────────────────────────────────────┐     │
│  │  🏛 Angie PRO                    [Из Реестра РФ] │     │
│  │  ──────────────────────────────────────────────── │     │
│  │  Реестровая запись: №17604 от 17.05.2023           │     │
│  │  Версия: 1.10.0                                    │     │
│  └──────────────────────────────────────────────────┘     │
│                                                              │
│  Описание:                                                   │
│  Angie PRO — высокопроизводительный веб-сервер, созданный     │
│  как форк Nginx. Внесён в Единый реестр российского ПО.      │
│                                                              │
│  Источник образа:                                            │
│  ┌──────────────────────────────────────────────────┐     │
│  │  dh-mirror.gitverse.ru/riftbit/angie               │     │
│  └──────────────────────────────────────────────────┘     │
│                                                              │
│  Порты по умолчанию:                                         │
│  ┌──────────────────────────────────────────────────┐     │
│  │  80 → 80   HTTP                                    │     │
│  │  443 → 443 HTTPS                                  │     │
│  └──────────────────────────────────────────────────┘     │
│                                                              │
│  Томов:                                                      │
│  ┌──────────────────────────────────────────────────┐     │
│  │  /data  →  /var/www/html                          │     │
│  └──────────────────────────────────────────────────┘     │
│                                                              │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │  📥 Скачать     │  │  ⚙️ Настроить    │                  │
│  └─────────────────┘  └─────────────────┘                  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 7.3 ConfigWizard (Модальное окно настройки)

```
┌──────────────────────────────────────────────────────────────┐
│  ⚙️ Настройка: Angie PRO                                     │
│  ────────────────────────────────────────────────────────   │
│                                                              │
│  ПОРТЫ                                                       │
│  ┌──────────────────────────────────────────────────┐     │
│  │ HTTP  80  ──────► [ 8080 ] (внешний)             │     │
│  └──────────────────────────────────────────────────┘     │
│                                                              │
│  ТОМА                                                       │
│  ┌──────────────────────────────────────────────────┐     │
│  │ /data  ──────► [ /opt/angie/data ]                │     │
│  │            [+ Добавить том]                       │     │
│  └──────────────────────────────────────────────────┘     │
│                                                              │
│  ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ                                       │
│  ┌──────────────────────────────────────────────────┐     │
│  │ DOMAIN    [ gos.server.ru ]                        │     │
│  │ TZ       [ Europe/Moscow ]                        │     │
│  │ [+ Добавить переменную]                            │     │
│  └──────────────────────────────────────────────────┘     │
│                                                              │
│  ┌────────────────────────┐  ┌──────────────────────┐        │
│  │       Отмена           │  │  📥 Скачать сборку   │        │
│  └────────────────────────┘  └──────────────────────┘        │
└──────────────────────────────────────────────────────────────┘
```

---

## 8. Jinja2 Шаблоны

### 8.1 Структура шаблонов

```
backend/app/templates/
├── single/
│   ├── angie/
│   │   └── docker-compose.yml.j2
│   ├── nginx/
│   │   └── docker-compose.yml.j2
│   ├── postgresql-redos/
│   │   └── docker-compose.yml.j2
│   ├── postgresql/
│   │   └── docker-compose.yml.j2
│   ├── nextcloud/
│   │   └── docker-compose.yml.j2
│   ├── prometheus/
│   │   └── docker-compose.yml.j2
│   └── grafana/
│       └── docker-compose.yml.j2
└── stacks/
    ├── web-stack.yml.j2
    ├── database-stack.yml.j2
    └── monitoring-stack.yml.j2
```

### 8.2 Пример шаблона (angie)

```yaml
# docker-compose.yml.j2
# GosDocker - {{ component.name }}
# Источник: {{ component.registry_url }}
# Обновлено: {{ now.strftime('%Y-%m-%d') }}

services:
  angie:
    image: {{ component.registry_url }}
    container_name: angie
    restart: unless-stopped
    ports:
{% for ext, int in config.ports.items() %}
      - "{{ ext }}:{{ int }}"
{% endfor %}
    volumes:
{% for host, container in config.volumes.items() %}
      - {{ host }}:{{ container }}
{% endfor %}
    environment:
{% for key, value in config.env.items() %}
      {{ key }}: {{ value }}
{% endfor %}
    networks:
      - gosdocker

networks:
  gosdocker:
    driver: bridge
```

### 8.3 Пример шаблона стека (web-database-stack)

```yaml
# docker-compose.yml.j2
# GosDocker - {{ stack.name }}
# Готовая сборка: {{ stack.description }}
# Обновлено: {{ now.strftime('%Y-%m-%d') }}

services:
{% for component in components %}
  {{ component.slug }}:
    image: {{ component.registry_url }}
    container_name: {{ component.slug }}
    restart: unless-stopped
    ports:
      # ports из config
    environment:
      # env из config
    networks:
      - gosdocker
{% endfor %}

networks:
  gosdocker:
    driver: bridge
```

---

## 9. Юзабилити и UX

### 9.1 Ключевые принципы

| Принцип | Реализация |
|---------|------------|
| **Минимум кликов** | Скачивание в 1 клик |
| **Безопасные умолчания** | Разумные значения по умолчанию |
| **Валидация** | Проверка портов, путей, переменных |
| **Подсказки** | Inline help для каждого поля |
| **Адаптивность** | Mobile-first дизайн |

### 9.2 Цветовая схема (для госструктур)

| Элемент | Цвет | HEX |
|---------|------|-----|
| Primary (РФ) | Зелёный | `#059669` |
| Secondary (Community) | Синий | `#2563EB` |
| Background | Белый | `#FFFFFF` |
| Surface | Серый | `#F9FAFB` |
| Text Primary | Тёмный | `#111827` |
| Text Secondary | Серый | `#6B7280` |

### 9.3 Бейджи

| Бейдж | Когда показывать |
|-------|-----------------|
| 🏛 **Из Реестра РФ** | `is_registry = true` |
| 📦 **Community** | `is_registry = false` |
| ✅ **Проверено** | Протестированная сборка |
| 🔒 **Безопасная** | Нет критических CVE |

---

## 10. Развёртывание платформы

### 10.1 Требования

- Docker 24.0+
- Docker Compose 2.20+
- 2 GB RAM минимум
- 10 GB диск

### 10.2 Быстрый старт

```bash
# Клонирование
git clone https://github.com/user/gosdocker.git
cd gosdocker

# Конфигурация
cp .env.example .env
# Отредактируйте .env при необходимости

# Запуск
docker compose up -d

# Проверка
curl http://localhost/api/categories
```

### 10.3 Docker Compose платформы

```yaml
# docker-compose.yml
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

---

## 11. Success Criteria

### 11.1 Функциональные критерии

| Критерий | Проверка | Метод |
|----------|----------|-------|
| Платформа запускается | `docker compose up -d` | Ручная проверка |
| API возвращает данные | `curl localhost/api/categories` | Автоматический тест |
| Готовые сборки отображаются | UI показывает стеки | UI проверка |
| Скачивание работает | ZIP с docker-compose.yml | Загрузка и проверка |
| Конфигуратор работает | Форма → Валидация → Генерация | UI проверка |

### 11.2 Компонентные критерии

| Компонент | Критерий |
|-----------|----------|
| **Angie PRO** | Скачивается с `dh-mirror.gitverse.ru`, запуск без ошибок |
| **PostgreSQL (РЕД ОС)** | Скачивается с `registry.red-soft.ru`, подключение к БД |
| **Nextcloud** | Запуск с PostgreSQL, веб-интерфейс доступен |
| **nginx** | Скачивается с `registry.red-soft.ru`, статика отдаётся |
| **PostgreSQL** | Скачивается с `dh-mirror.gitverse.ru`, репликация работает |
| **Prometheus + Grafana** | Метрики собираются, дашборды отображаются |

### 11.3 Нефункциональные критерии

| Критерий | Целевое значение |
|----------|------------------|
| Время загрузки UI | < 2 секунд |
| Генерация docker-compose | < 1 секунда |
| Размер ZIP-архива | < 10 KB |

---

## 12. Глоссарий

| Термин | Определение |
|--------|-------------|
| **GosDocker** | Название платформы |
| **GosCompose** | Домен проекта |
| **Компонент** | Единица ПО в каталоге (nginx, PostgreSQL и т.д.) |
| **Стек** | Готовая сборка из нескольких компонентов |
| **Реестр РФ** | Единый реестр российского ПО Минцифры |
| **РФ-источник** | Образ из российского реестра (registry.red-soft.ru) |
| **Комьюнити** | Open-source образы |
| **dh-mirror** | Зеркало Docker Hub от GitVerse/Сбер |

---

## 13. Источники и ссылки

### 13.1 Реестры и источники

| Источник | URL | Примечание |
|----------|-----|------------|
| registry.red-soft.ru | https://registry.red-soft.ru | Реестр РЕД ОС |
| dh-mirror.gitverse.ru | https://dh-mirror.gitverse.ru | Зеркало Docker Hub |
| Реестр ПО Минцифры | https://reestr.digital.gov.ru | Проверка компонентов |

### 13.2 Компоненты

| Компонент | Документация | Реестр |
|-----------|--------------|--------|
| Angie PRO | https://angie.software | №17604 |
| PostgreSQL (РЕД ОС) | https://redos.red-soft.ru | — |
| Nextcloud | https://nextcloud.com | — |
| Prometheus | https://prometheus.io | — |
| Grafana | https://grafana.com | — |

---

**Автор:** GosDocker Project
**Дата создания:** 2026-04-19
**Версия:** 1.0
