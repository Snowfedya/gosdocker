# GosDocker

Каталог Docker Compose-сборок для государственных и образовательных организаций.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green)
![Vue.js](https://img.shields.io/badge/Vue.js-3.4-brightgreen)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue)
![License](https://img.shields.io/badge/License-MIT-yellow)

## Описание

GosDocker — веб-платформа для автоматизированной генерации Docker Compose сборок с использованием отечественного программного обеспечения из Единого реестра российского ПО Минцифры.

## Возможности

- 📦 Каталог компонентов из Реестра Минцифры (Angie PRO, PostgreSQL РЕД ОС, Nextcloud)
- 🌐 Компоненты комьюнити (nginx, PostgreSQL, Prometheus, Grafana)
- ⚙️ Визуальная настройка параметров (порты, переменные окружения, тома)
- 📥 Генерация docker-compose.yml в один клик
- 🔍 Фильтрация по категориям (Веб, Базы данных, Файловые хранилища, Мониторинг)

## Быстрый старт

```bash
# Клонирование
git clone https://github.com/markfl/gosdocker.git
cd gosdocker

# Конфигурация
cp .env.example .env

# Запуск платформы
docker compose up -d

# Заполнение базы данных
docker compose exec backend python seed.py

# Открыть в браузере
open http://localhost
```

## Стек технологий

| Компонент | Технология |
|-----------|-----------|
| Backend | FastAPI + SQLAlchemy 2.0 + asyncpg |
| Frontend | Vue 3 + TypeScript + Tailwind CSS |
| База данных | PostgreSQL 15 |
| Веб-сервер | nginx:alpine |
| Контейнеризация | Docker + Docker Compose |

## Источники образов

- **registry.red-soft.ru** — РЕД ОС (основной для российского ПО)
- **dh-mirror.gitverse.ru** — GitVerse Docker Mirror (зеркало Docker Hub от Сбера)

## API Endpoints

| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | `/api/categories` | Список категорий |
| GET | `/api/components` | Список компонентов |
| GET | `/api/components/{slug}` | Детали компонента |
| GET | `/api/stacks` | Список сборок |
| GET | `/api/stacks/{slug}` | Детали сборки |
| POST | `/api/generate` | Генерация docker-compose.zip |
| GET | `/health` | Проверка здоровья |

## Структура проекта

```
gosdocker/
├── backend/           # FastAPI API
│   ├── app/
│   │   ├── api/       # API routes
│   │   ├── models/    # SQLAlchemy models
│   │   ├── schemas/    # Pydantic schemas
│   │   ├── services/   # Business logic
│   │   └── templates/  # Jinja2 compose templates
│   ├── Dockerfile
│   ├── requirements.txt
│   └── seed.py
├── frontend/          # Vue 3 SPA
│   ├── src/
│   ├── Dockerfile
│   └── package.json
├── nginx/
│   └── nginx.conf
├── docs/              # Documentation
├── docker-compose.yml
├── .env.example
├── README.md
└── LICENSE
```

## Разработка

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

## Лицензия

MIT License — подробности в файле [LICENSE](LICENSE).

## Автор

Петленко Фёдор Дмитриевич
Группа УВПв-521
Российский университет транспорта (МИИТ, РУТ)
2026