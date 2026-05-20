# GosDocker — Версионирование и поддержка образов

> **Тип проекта:** Расширение существующей платформы GosDocker
> **Цель:** Безопасный механизм выбора версий — только одобренные администратором версии доступны пользователям

---

## 🎯 Goal

Пользователь получает только проверенные версии софта. Администратор контролирует, какие версии доступны для выбора. При скачивании docker-compose подставляется конкретный тег образа.

---

## ✅ Success Criteria

| Критерий | Проверка |
|----------|----------|
| В конфигураторе отображается только одобренный список версий | UI показывает dropdown с версиями |
| По умолчанию выбрана рекомендуемая версия | current_version подставлена в шаблон |
| Скачанный docker-compose содержит конкретный тег | `image: registry:tag` вместо `image: registry` |
| 3+ версии одобрены для каждого компонента | seed.py содержит approved_versions |

---

## 📋 Changes

### 1. Модель Component

Добавить поля:

```python
approved_versions: Column(JSON, default=list)  # ["1.10.0", "1.9.0"]
current_version: Column(String(50))           # "1.10.0" — рекомендуемая
```

### 2. Schema ComponentDetail

Добавить в API response:

```python
approved_versions: list[str]  # доступные версии
current_version: str           # рекомендуемая
```

### 3. Jinja2 шаблоны

Изменить `image:` чтобы подставлялся тег:

```yaml
image: {{ registry_url }}:{{ current_version }}
```

Или через config (для гибкости):

```yaml
image: {{ registry_url }}:{{ config.get('version', current_version) }}
```

### 4. Seed data

Обновить seed.py — добавить approved_versions и current_version:

| Компонент | current_version | approved_versions |
|----------|----------------|-------------------|
| Angie PRO | 1.10.0 | ["1.10.0", "1.9.0", "1.8.0"] |
| nginx | 1.28 | ["1.28", "1.27", "1.26"] |
| PostgreSQL РЕД ОС | 17 | ["17", "16"] |
| PostgreSQL | 15-alpine | ["15-alpine", "16-alpine"] |
| Nextcloud | latest | ["30", "29", "28"] |
| Prometheus | latest | ["3.2.0", "3.1.0", "3.0.0"] |
| Grafana | latest | ["11.5.0", "11.4.0", "11.3.0"] |

### 5. Frontend — ConfigWizard

- Добавить dropdown выбора версии
- Показать только approved_versions
- По умолчанию current_version
- Передавать выбранную версию в config при генерации

### 6. Процесс обновления

1. Администратор видит новую версию (ручной мониторинг источников)
2. Тестирует у себя (проверяет совместимость, CVE)
3. Добавляет версию в approved_versions
4. При необходимости обновляет current_version
5. Пользователи автоматически видят новую версию

---

## 📁 Files to Change

### Backend
- `backend/app/models/component.py` — добавить поля
- `backend/app/schemas/component.py` — добавить поля в schema
- `backend/app/api/components.py` — включить новые поля в response
- `backend/app/services/generate_service.py` — подставлять версию в image
- `backend/app/templates/single/*/docker-compose.yml.j2` — использовать `:{{ version }}`
- `backend/seed.py` — заполнить approved_versions и current_version

### Frontend
- `frontend/src/types/index.ts` — добавить поля в Component interface
- `frontend/src/components/ConfigWizard.vue` — добавить dropdown версий

---

## Self-Review

- ✅ Scope focused: только версионирование, не затрагивает другие части
- ✅ No placeholders: все версии заполнены
- ✅ Process clear: админ сам решает когда обновлять
- ✅ Backward compatible: current_version по умолчанию

---

## Next Step

Создать план реализации → writing-plans
