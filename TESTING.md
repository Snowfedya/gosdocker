# Тестирование GosDocker

## Проверка платформы

### 1. Запуск

```bash
docker compose up -d
docker compose exec backend python seed.py
```

### 2. Проверка API

```bash
# Категории
curl http://localhost/api/categories
# Ожидается: JSON с 4 категориями

# Компоненты
curl http://localhost/api/components
# Ожидается: JSON с 7 компонентами

# Стеки
curl http://localhost/api/stacks
# Ожидается: JSON с 4 стеками

# Проверка здоровья
curl http://localhost/health
# Ожидается: {"status":"ok"}
```

### 3. Генерация docker-compose

```bash
curl -X POST http://localhost/api/generate \
  -H "Content-Type: application/json" \
  -d '{"components": ["angie-pro"], "config": {"angie-pro": {"ports": {"80": 80}}}}' \
  -o test.zip

unzip -l test.zip
# Ожидается: docker-compose.yml, .env.example, README.md

# Проверка здоровья
curl http://localhost/health
# Ожидается: {"status":"ok"}
```

### 4. UI

```bash
open http://localhost
# Ожидается: главная страница GosDocker
```

## Проверка образов

### Angie PRO
```bash
docker pull dh-mirror.gitverse.ru/riftbit/angie
docker run --rm dh-mirror.gitverse.ru/riftbit/angie -v 2>&1 | head -1
```

### PostgreSQL (РЕД ОС)
```bash
docker pull registry.red-soft.ru/ubi8/postgresql-17
docker run --rm registry.red-soft.ru/ubi8/postgresql-17 --version
```

### nginx (РЕД ОС)
```bash
docker pull registry.red-soft.ru/ubi8/nginx
docker run --rm registry.red-soft.ru/ubi8/nginx -v 2>&1 | head -1
```

## Остановка

```bash
docker compose down
```