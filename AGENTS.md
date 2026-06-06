# GosDocker — AGENTS.md (проектный контекст)

> **Платформа контейнеризации для государственных учреждений.**
> ВКР Петленко Ф.Д., УВПв-521. Защита: 15-18 июня 2026.
> GitHub: `github.com/Snowfedya/gosdocker.git`
> Прочитай этот файл ПЕРВЫМ при любой работе с GosDocker.

---

## Текущий статус (02.06.2026)

🔴 **Нормоконтроль 05.06** — через 3 дня. Защита 15-18.06.
🟢 Backend: FastAPI работающий, pipeline (build → OWASP → sign → register) написан
🟢 Frontend: Vue 3, каталог компонентов, конструктор сборок
🟢 Docker Compose: локально собирается
🔴 **Требования Заманова** (преподаватель, готовит рецензию): source-build + SBOM(CDX) + signed images(Cosign) + OWASP + tar/deploy.sh + скриншоты в ВКР
🟡 Тесты: P0 тест-план готов (02.06), но не все написаны
🟡 Аутентификация: отсутствует (TODO)

---

## Архитектура

```
gosdocker/
├── backend/               # FastAPI (Python 3.11)
│   ├── app/
│   │   ├── api/           # Роуты: components, stacks, categories, generate, constructor, registry
│   │   ├── models/        # SQLAlchemy: Component, Category, Stack
│   │   ├── schemas/       # Pydantic схемы
│   │   ├── services/      # Бизнес-логика: generate, template_service, dependency_resolver, security_profiles
│   │   ├── pipeline/      # CI-пайплайн: build, owasp, scan, sign, package, register
│   │   ├── templates/     # Jinja2 шаблоны docker-compose
│   │   ├── main.py        # Точка входа FastAPI
│   │   ├── config.py      # Pydantic Settings
│   │   └── database.py    # AsyncSession + engine
│   ├── Dockerfile
│   ├── requirements.txt
│   └── seed.py
├── frontend/              # Vue 3 + TypeScript + Tailwind
│   ├── src/
│   │   ├── views/         # Home, Catalog, Component, Constructor, StackDetail, SecurityReport, Stacks, NotFound
│   │   ├── components/    # UI: ComponentCard, StackCard, ConfigWizard, security/*, Footer, SourceBadge...
│   │   ├── composables/   # useApi, useSecurityReport
│   │   ├── types/         # TypeScript интерфейсы
│   │   ├── utils/         # security.ts, format helpers
│   │   └── router/        # Vue Router
│   └── Dockerfile
├── nginx/
│   └── nginx.conf
├── docker-compose.yml     # backend + frontend + nginx + PostgreSQL 15
├── docs/                  # VERIFICATION-CHECKLIST, TEST-RESULTS, VALIDATION-REPORT, container-baseline
├── TESTING.md
├── TESTING_INFRASTRUCTURE_PLAN.md
└── README.md
```

### Сервисы (Docker Compose)

| Сервис | Порт | Роль |
|--------|------|------|
| **backend** | 8000 | FastAPI + asyncpg |
| **frontend** | — (через nginx) | Vue 3 SPA |
| **nginx** | 8080→80 | Reverse proxy |
| **db** | 5432 | PostgreSQL 15-alpine |

### Pipeline (backend/app/pipeline/)

```
build.py → scan.py (Trivy) → owasp.py (OWASP ZAP) → sign.py (Cosign) → package.py (tar) → register.py
```

---

## Ключевые файлы

| Файл | Что делает |
|------|------------|
| `backend/app/api/generate.py` | Генерация docker-compose.yml из шаблонов |
| `backend/app/services/dependency_resolver.py` | Разрешение зависимостей компонентов |
| `backend/app/services/template_service.py` | Jinja2-шаблонизация compose |
| `backend/app/pipeline/owasp.py` | OWASP ZAP-скан (dependency-check) |
| `backend/app/pipeline/sign.py` | Cosign-подпись образов |
| `backend/app/pipeline/build.py` | Source-build образов |
| `frontend/src/views/ConstructorView.vue` | Главная UX-точка: визуальный конструктор |
| `frontend/src/components/security/*.vue` | Дашборд безопасности (CveTable, SeverityBar и т.д.) |

---

## Правила разработки

### Docker/контейнеры
- Все образы — source-build из Dockerfile, не pull готовых (требование Заманова)
- Для registry-образов (РЕД ОС, GitVerse): `registry.red-soft.ru` и `dh-mirror.gitverse.ru`
- После сборки: SBOM (CycloneDX) → Cosign sign → OWASP scan → упаковка в tar

### Тестирование
- Тест-план: `/opt/gosdocker/docs/VERIFICATION-CHECKLIST.md` и `TESTING.md`
- Инфраструктура тестов: `TESTING_INFRASTRUCTURE_PLAN.md`
- P0: dependency_resolver отстаёт от registry (3 компонента) — завести issue
- P0: CVE-2024-XXXX заглушки — убрать заглушки, реальные CVE
- P0: нет аутентификации
- P1: Docker restart policy отсутствует
- P1: нет CI/CD автоматизации

### Заманов (преподаватель-рецензент)
Требования к ВКР со стороны преподавателя:
1. **Source-build** — образы собираются из исходников, не из готовых
2. **SBOM (CycloneDX)** — Software Bill of Materials в формате CDX
3. **Cosign sign** — подпись образов
4. **OWASP** — Dependency-Check / ZAP
5. **tar/deploy.sh** — скрипт развёртывания
6. **Скриншоты** — в приложении ВКР

### ВКР-связанное
- ВКР лежит в `/root/.hermes/vkr-workspace/ВКР_Петленко_УВПв_521_ИСПРАВЛЕННЫЙ_fixed.docx`
- GAP-анализ: `/root/.hermes/vkr-workspace/VKR_GAP_ANALYSIS_01-06-2026.md`
- Верификация: `/root/.hermes/vkr-workspace/VKR_VERIFICATION_PLAN_02-06-2026.md`
- Для полного контекста ВКР: читай `/root/.hermes/vkr-workspace/AGENTS.md`

### Git
- origin: `https://github.com/Snowfedya/gosdocker.git`
- Основная ветка: main
- Коммиты с осмысленными сообщениями (pref: feat/fix/docs prefix)
- Перед коммитом: проверить что тесты проходят

---

## Известные проблемы

1. **dependency_resolver** — не синхронизирован с registry (3+ компонента расходятся)
2. **CVE-2024-XXXX заглушки** — в security report используются placeholder CVE
3. **Нет аутентификации** — любой может генерировать сборки
4. **Нет CI/CD** — всё ручное
5. **Docker restart policy** — не задана (контейнеры не перезапускаются после падения)
6. **Backup** — нет бекапа БД
7. **Нормоконтроль 05.06** — deadline на исправление замечаний

---

## Быстрые команды

```bash
# Сборка
docker compose build

# Запуск
docker compose up -d

# Логи
docker compose logs -f backend

# Seed БД
docker compose exec backend python seed.py

# Тесты backend (если есть)
cd backend && pytest -v

# Очистка
docker compose down -v
```
