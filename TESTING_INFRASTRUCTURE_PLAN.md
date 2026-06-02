# План тестирования инфраструктуры и деплоя GosDocker

**Дата:** 2 июня 2026
**Версия:** 1.0
**Автор:** Hermes Agent (инфраструктурный аудит)

---

## Содержание

1. [Общая информация](#1-общая-информация)
2. [Раздел 1: Docker Compose развёртывание](#2-раздел-1-docker-compose-развёртывание)
3. [Раздел 2: Nginx (HTTPS, HSTS, rate limiting, error pages)](#3-раздел-2-nginx)
4. [Раздел 3: Production-ready (graceful shutdown, resource limits, OOM)](#4-раздел-3-production-ready)
5. [Раздел 4: Backup/Restore](#5-раздел-4-backuprestore)
6. [Раздел 5: CI/CD Pipeline (GitHub Actions)](#6-раздел-5-cicd-pipeline)
7. [Раздел 6: Monitoring (Prometheus + Grafana)](#7-раздел-6-monitoring)
8. [Раздел 7: Zero-downtime deploy](#8-раздел-7-zero-downtime-deploy)
9. [Раздел 8: Air-gapped deployment](#9-раздел-8-air-gapped-deployment)
10. [Раздел 9: Load testing](#10-раздел-9-load-testing)
11. [Раздел 10: Disaster recovery](#11-раздел-10-disaster-recovery)
12. [Сводная таблица](#12-сводная-таблица)

---

## 1. Общая информация

### Текущее состояние инфраструктуры (на 2 июня 2026)

| Параметр | Значение |
|----------|----------|
| VPS | 62.152.59.45, Ubuntu 20.04, 7.8GB RAM, 74GB SSD |
| Диск | 75% (52/74G использовано) |
| RAM | 2.7/7.8G used, 4.7G available |
| Swap | 1.1/3.9G used (swapfile + /dev/sda3) |
| Uptime | 7d 22h |
| Load average | 3.23, 1.88, 1.55 |
| Docker | 11 images (6.17GB), 11 containers, 9 volumes (1.33GB) |
| HTTPS | Let's Encrypt — валиден до 2026-08-24 (83 дня) |
| Сервисы | 4 основных (backend, frontend, nginx, db) + 3 мониторинга + 2 дублирующихся (gosdocker-fix) |
| CI/CD | Отсутствует полностью |
| Бэкапы | Отсутствуют |
| Мониторинг | Prometheus + Grafana запущены, но Prometheus собирает только себя. Дашбордов GosDocker нет |
| Graceful shutdown | Не настроен |
| Resource limits | Не заданы |
| Restart policy | Не задана (кроме db healthcheck) |

### Легенда приоритетов

| Приоритет | Описание |
|-----------|----------|
| **P0** | Критично — блокирует production. Необходимо исправить до ввода в эксплуатацию |
| **P1** | Высокий — значительный риск. Желательно исправить в ближайший спринт |
| **P2** | Средний — улучшение надежности. Плановая работа |
| **P3** | Низкий — nice-to-have. При наличии ресурсов |

### Оценка трудозатрат

- **S** (Small) — до 2 часов
- **M** (Medium) — 2-4 часа
- **L** (Large) — 4-8 часов
- **XL** (Extra Large) — 8+ часов

---

## 2. Раздел 1: Docker Compose развёртывание

### Контекст

`docker-compose.yml` (63 строки) — 4 сервиса: backend, frontend, nginx, db.
- Отсутствуют: restart policy, healthchecks (кроме db), deploy strategy, resource limits
- `docker compose up -d` неидепотентен: нет проверок состояния при старте
- Нет `stop_grace_period`
- Нет `depends_on` с condition (кроме backend→db)

### Тест-кейсы

| ID | Тест-кейс | Ожидаемый результат | Приоритет | Трудозатраты | Инструмент |
|----|-----------|---------------------|-----------|--------------|------------|
| TC-1.1 | **Идемпотентность `docker compose up -d`** — выполнить `docker compose up -d` дважды подряд | Второй запуск возвращает "Service is up-to-date" для всех сервисов. Никакие контейнеры не пересоздаются | **P1** | S | `docker compose up -d`, `docker ps` |
| TC-1.2 | **Restart policy отсутствует** — проверить, что при `docker stop gosdocker-backend-1` контейнер НЕ перезапускается автоматически | `docker stop backend` → контейнер остаётся в статусе Exited. Docker не перезапускает его | **P0** | S | `docker stop`, `docker ps`, `docker compose ps` |
| TC-1.3 | **Добавление restart: unless-stopped** — модифицировать compose, выполнить `up -d`. Проверить, что docker restart policy установлена | После `docker stop backend`: контейнер автоматически перезапускается в течение 10 секунд | **P0** | S | `docker inspect`, `docker stop`, таймер |
| TC-1.4 | **Healthcheck backend** — добавить healthcheck на backend: curl http://localhost:8000/health. Проверить, что здоров | `docker inspect gosdocker-backend-1 --format '{{.State.Health.Status}}'` → `healthy` | **P1** | S | curl, `docker inspect` |
| TC-1.5 | **Healthcheck frontend** — добавить healthcheck на frontend Docker-nginx | Frontend healthcheck: curl на порт 80 → 200 | **P1** | S | curl, `docker inspect` |
| TC-1.6 | **Healthcheck Docker nginx** — добавить healthcheck на reverse proxy nginx | Nginx healthcheck: curl на порт 80 → 200 | **P1** | S | curl, `docker inspect` |
| TC-1.7 | **depends_on с condition=healthy для всех upstream** — nginx должен ждать backend+frontend, frontend ждать backend | При старте: порядок db→backend→frontend→nginx. Все healthcheck статусы корректны | **P1** | M | `docker compose up`, `docker compose ps` |
| TC-1.8 | **Проверка сетей** — все сервисы должны быть в одной сети gosdocker | `docker network inspect gosdocker_gosdocker` — все 4 контейнера подключены | **P2** | S | `docker network inspect` |
| TC-1.9 | **Проверка монтирования volume** — `docker exec` проверить, что registry:ro, docker.sock, constructor shared volume доступны | backend: `/app/registry` (ro, readable), `/var/run/docker.sock` (rw), `/tmp/gosdocker-constructor` (rw) | **P2** | S | `docker exec`, `ls -la`, `stat` |
| TC-1.10 | **Idempotent volume create** — `docker compose up -d` не должен пересоздавать volumes с потерей данных | После повторного `up -d`: pgdata intact, syft_cache intact, trivy_cache intact | **P1** | S | `docker volume inspect`, проверка данных |
| TC-1.11 | **Удаление дублирующихся сервисов gosdocker-fix** — проверить, что `gosdocker-fix-backend-1` (Created) не влияет на основной compose. Принять решение об удалении | Решение: оставить (не мешает) или `docker compose -f /opt/gosdocker-fix/docker-compose.yml down && rm -rf /opt/gosdocker-fix` | **P2** | S | `docker ps -a` |
| TC-1.12 | **Docker socket security** — проверить, что DooD socket не даёт полного доступа к хосту внутри контейнера | `docker exec gosdocker-backend-1 docker ps` — работает. Но контейнер не может выполнить `docker exec --privileged` на хосте | **P2** | S | `docker exec` |

### Необходимые изменения перед тестированием

```yaml
# В секцию каждого сервиса (кроме db — у него уже есть healthcheck) добавить:
restart: unless-stopped
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]  # для backend
  # или для nginx/frontend:
  # test: ["CMD", "nginx", "-t"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s

# Для frontend:
depends_on:
  backend:
    condition: service_healthy

# Для nginx:
depends_on:
  backend:
    condition: service_healthy
  frontend:
    condition: service_started
```

---

## 3. Раздел 2: Nginx

### Контекст

Два уровня Nginx:
1. **System nginx** (systemd, Let's Encrypt) — `/etc/nginx/sites-enabled/gosdocker`
2. **Docker nginx** (gosdocker-nginx-1) — `/opt/gosdocker/nginx/nginx.conf`

### Текущие проблемы
- Нет rate limiting
- Нет кастомных error pages
- Нет security headers кроме HSTS
- Нет `proxy_next_upstream` — при падении backend не переключается
- Нет healthcheck на upstream
- `/health` идёт напрямую в backend (минует Docker nginx) — может показывать OK при падении Docker nginx

### Тест-кейсы

| ID | Тест-кейс | Ожидаемый результат | Приоритет | Трудозатраты | Инструмент |
|----|-----------|---------------------|-----------|--------------|------------|
| **TC-2.1 HTTPS** | | | | | |
| TC-2.1.1 | **HTTPS доступен** — `curl -I https://gosdocker.ru` | HTTP/2, статус 200 или 302 (SPA redirect) | **P0** | S | curl |
| TC-2.1.2 | **HSTS header** — проверить `Strict-Transport-Security` | `max-age=31536000; includeSubDomains`, `always` | **P0** | S | `curl -sI https://gosdocker.ru` |
| TC-2.1.3 | **HTTP → HTTPS redirect** — `curl -I http://gosdocker.ru` | `301 Moved Permanently` → `https://gosdocker.ru` | **P0** | S | curl |
| TC-2.1.4 | **Direct IP — return 444** — `curl -I http://62.152.59.45` | Соединение сброшено (444) | **P0** | S | curl |
| TC-2.1.5 | **SSL protocols** — проверить TLS 1.2 и TLS 1.3 доступны, deprecated (TLS 1.0/1.1) — нет | TLS 1.2: OK, TLS 1.3: OK, TLS 1.1: rejected | **P1** | S | `openssl s_client` |
| TC-2.1.6 | **SSL certificate expiry** — проверить дату истечения сертификата | > 60 дней (текущий: до 24.08.2026, ~83 дня) | **P1** | S | `certbot certificates` или openssl |
| TC-2.1.7 | **Auto-renewal cron** — проверить, настроен ли `certbot renew` | `systemctl status certbot.timer` или `crontab -l | grep certbot` | **P0** | S | systemctl, crontab |
| **TC-2.2 Proxy** | | | | | |
| TC-2.2.1 | **`/health` endpoint** — `curl https://gosdocker.ru/health` | 200 OK | **P0** | S | curl |
| TC-2.2.2 | **`/api` proxy** — `curl https://gosdocker.ru/api/categories` | 200, JSON response | **P0** | S | curl |
| TC-2.2.3 | **Frontend routing** — `curl https://gosdocker.ru/` | 200, HTML (SPA) | **P0** | S | curl |
| TC-2.2.4 | **SPA fallback** — `curl https://gosdocker.ru/some/deep/link` | 200, index.html (SPA routing) | **P1** | S | curl |
| TC-2.2.5 | **Proxy timeout** — `/api` запрос, который длится >60s (эмуляция долгой сборки) | Должен выдержать 300s timeout (not 504 до 300s). Проверить, что 200 возвращается | **P1** | M | `curl --max-time 310` на долгий запрос |
| **TC-2.3 Security** | | | | | |
| TC-2.3.1 | **Rate limiting** — 1000 запросов к `/api` за 1 секунду | После N запросов — 429 Too Many Requests (нужно добавить limit_req в nginx) | **P1** | M | ab/wrk/`seq 1000 | xargs curl` |
| TC-2.3.2 | **Security headers** — проверить наличие Content-Security-Policy, X-Content-Type-Options, X-Frame-Options | HSTS есть. Остальные заголовки отсутствуют — тест падает, план: добавить | **P2** | S | `curl -sI` + grep |
| TC-2.3.3 | **No sensitive headers** — проверить, что server version не протекает | Server header: не содержит nginx/VERSION (добавить `server_tokens off`) | **P2** | S | `curl -sI` |
| TC-2.3.4 | **Error pages — 404/502 кастомные** — проверить, что отдаётся при ошибках | Сейчас: default nginx error page. План: кастомные страницы | **P3** | S | curl несуществующий URL |
| TC-2.3.5 | **Body size limit** — проверить, что `client_max_body_size 50m` работает | Файл >50m → 413, <50m → проходит | **P2** | M | `curl -X POST -F "file=@large_file.bin"` |
| **TC-2.4 Infrastructure** | | | | | |
| TC-2.4.1 | **Nginx systemd** — проверить, что system nginx под systemd и включён в автозагрузку | `systemctl is-enabled nginx` → enabled; `systemctl is-active nginx` → active | **P1** | S | systemctl |
| TC-2.4.2 | **Access/error logs** — проверить, что логи nginx ротируются | `/var/log/nginx/access.log` — не пуст, ротация настроена | **P2** | S | `ls -la /var/log/nginx/` |
| TC-2.4.3 | **Nginx config test** — проверить синтаксис конфигурации | `nginx -t` → test is successful | **P1** | S | `nginx -t` |

---

## 4. Раздел 3: Production-ready

### Контекст

Текущий compose не имеет:
- `restart` policy (кроме дефолтного `no`)
- `deploy.resources.limits` (CPU, memory)
- `stop_grace_period`
- `oom_kill_disable`
- Backend uvicorn запущен без `--timeout-graceful-shutdown`

### Тест-кейсы

| ID | Тест-кейс | Ожидаемый результат | Приоритет | Трудозатраты | Инструмент |
|----|-----------|---------------------|-----------|--------------|------------|
| **TC-3.1 Restart Policy** | | | | | |
| TC-3.1.1 | **restart: unless-stopped (backend)** — `docker stop gosdocker-backend-1` | Контейнер перезапускается Docker daemon в течение 10-30s | **P0** | S | `docker stop`, `docker wait`, `docker ps` |
| TC-3.1.2 | **restart: unless-stopped (nginx)** — `docker stop gosdocker-nginx-1` | Перезапускается автоматически | **P0** | S | `docker stop`, `docker ps` |
| TC-3.1.3 | **restart: unless-stopped (frontend)** — `docker stop gosdocker-frontend-1` | Перезапускается автоматически | **P0** | S | `docker stop`, `docker ps` |
| TC-3.1.4 | **restart: unless-stopped (db)** — `docker stop gosdocker-db-1` | Перезапускается автоматически (данные pgdata сохраняются) | **P0** | S | `docker stop`, проверка данных |
| **TC-3.2 Resource Limits** | | | | | |
| TC-3.2.1 | **Memory limit backend** — добавить `deploy.resources.limits.memory: 1g` и проверить | `docker inspect` показывает Memory=1073741824 | **P1** | S | `docker inspect`, `docker stats` |
| TC-3.2.2 | **Memory limit nginx** — `memory: 256m` | Memory limit установлен | **P2** | S | `docker inspect` |
| TC-3.2.3 | **Memory limit frontend** — `memory: 128m` (статический nginx, почти без нагрузки) | Memory limit установлен | **P2** | S | `docker inspect` |
| TC-3.2.4 | **Memory limit db** — `memory: 2g` (PostgreSQL) | Memory limit установлен | **P1** | S | `docker inspect` |
| TC-3.2.5 | **CPU limit backend** — `deploy.resources.limits.cpus: "2.0"` | CPU shares установлены | **P2** | S | `docker inspect` |
| TC-3.2.6 | **OOM killer** — `oom_kill_disable: false` (default). При превышении memory limit контейнер должен быть убит, а не зависнуть | При memory leak backend → OOM kill → restart по policy | **P1** | L | стресс-тест памятью (специальный тест) |
| **TC-3.3 Graceful Shutdown** | | | | | |
| TC-3.3.1 | **Backend SIGTERM handling** — `docker stop gosdocker-backend-1` (graceful) | Uvicorn ловит SIGTERM, завершает текущие запросы (--timeout-graceful-shutdown 30), закрывает соединение с БД | **P0** | M | `docker stop -t 30`, проверка логов `docker logs --tail 20` |
| TC-3.3.2 | **stop_grace_period** — добавить `stop_grace_period: 60s` в compose для backend | При `docker compose down`, контейнеру даётся 60s на graceful shutdown | **P1** | S | `docker inspect`, `docker compose down` |
| TC-3.3.3 | **DB connection pool drain** — при shutdown backend должен закрыть asyncpg pool | В логах: "Closing database connection pool..." или аналогично | **P1** | M | `docker logs`, проверка uvicorn lifespan |
| TC-3.3.4 | **Nginx graceful reload** — `docker exec gosdocker-nginx-1 nginx -s reload` | Reload без drop соединений (0 failed requests) | **P1** | M | `nginx -s reload` под нагрузкой |
| **TC-3.4 Docker Daemon** | | | | | |
| TC-3.4.1 | **Docker daemon.json** — проверить наличие и корректность настроек | Нет daemon.json → default settings → нет `log-opts max-size`, нет `live-restore` | **P1** | S | `cat /etc/docker/daemon.json` |
| TC-3.4.2 | **Docker logs size limit** — добавить `log-opts max-size: 10m max-file: 3` в daemon.json | Логи контейнеров ротируются при 10MB | **P1** | M | `docker inspect`, `ls -la /var/lib/docker/containers/*/*.log` |
| TC-3.4.3 | **live-restore** — включить `live-restore: true` в daemon.json | При перезапуске Docker daemon контейнеры не умирают | **P2** | M | `systemctl restart docker`, проверка uptime контейнеров |

### Необходимые изменения в docker-compose.yml

```yaml
services:
  backend:
    restart: unless-stopped
    stop_grace_period: 60s
    deploy:
      resources:
        limits:
          cpus: "2.0"
          memory: 1g
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  frontend:
    restart: unless-stopped
    stop_grace_period: 30s
    depends_on:
      backend:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "nginx", "-t"]
      interval: 30s
      timeout: 10s
      retries: 3

  nginx:
    restart: unless-stopped
    stop_grace_period: 30s
    depends_on:
      backend:
        condition: service_healthy
      frontend:
        condition: service_started
    healthcheck:
      test: ["CMD-SHELL", "nginx -t || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3

  db:
    restart: unless-stopped
    stop_grace_period: 120s
    deploy:
      resources:
        limits:
          memory: 2g
```

### В app/main.py добавить lifespan для graceful shutdown:

```python
import asyncio
from contextlib import asynccontextmanager
from app.database import db_pool  # или как реализовано

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.db_pool = await asyncpg.create_pool(dsn=settings.database_url)
    yield
    # Shutdown
    logger.info("Shutting down database connection pool...")
    await app.state.db_pool.close()
    logger.info("Database pool closed gracefully")
```

---

## 5. Раздел 4: Backup/Restore

### Контекст

- `pg_dump` установлен (PostgreSQL client)
- Нет backup-скрипта
- Нет backup-директории
- Docker volumes: pgdata (~неизвестный размер), syft_cache, trivy_cache
- Нет crontab с backup
- На диске свободно ~19GB

### Тест-кейсы

| ID | Тест-кейс | Ожидаемый результат | Приоритет | Трудозатраты | Инструмент |
|----|-----------|---------------------|-----------|--------------|------------|
| **TC-4.1 PostgreSQL Backup** | | | | | |
| TC-4.1.1 | **pg_dump connectivity** — `pg_dump -U gosdocker -h localhost -d gosdocker > /tmp/test_dump.sql` | Успешный дамп, файл не пустой | **P0** | S | pg_dump |
| TC-4.1.2 | **pg_dump внутри Docker** — `docker exec gosdocker-db-1 pg_dump -U gosdocker | ...` | Работает; проверить, что pg_dump есть внутри контейнера | **P0** | S | `docker exec` |
| TC-4.1.3 | **Automated backup script** — написать `/opt/gosdocker/scripts/backup.sh` с ежедневным дампом, хранением 7 дней | Скрипт: pg_dump → `/opt/gosdocker/backups/db/YYYY-MM-DD.sql.gz` (сжатый), автоочистка старых (>7 дней) | **P0** | M | bash, pg_dump, gzip |
| TC-4.1.4 | **Backup crontab** — добавить ежедневный pg_dump в 3:00 AM | `0 3 * * * /opt/gosdocker/scripts/backup.sh` — выполняется, файлы создаются | **P0** | S | crontab |
| TC-4.1.5 | **Restore test** — `psql -U gosdocker -d gosdocker < backup.sql` на test DB (не production) | Данные восстанавливаются, все таблицы целы, приложение работает | **P0** | M | psql |
| TC-4.1.6 | **Volume backup** — pg_dump — это logical backup. Проверить, что volume snapshot также нужен | Решение: pg_dump достаточно (logical backup восстанавливается в любую PostgreSQL версии) | **P2** | S | исследование |
| **TC-4.2 Volume Backup** | | | | | |
| TC-4.2.1 | **syft_cache backup** — оценить размер (`docker run --rm -v gosdocker_syft_cache:/data alpine tar czf - -C /data . | wc -c`) | Оценить, нужно ли бэкапить cache volumes (обычно не нужно — пересоздаются автоматически) | **P3** | S | tar, docker |
| TC-4.2.2 | **trivy_cache backup** — оценить размер | Оценить (trivy cache — несколько сотен MB) | **P3** | S | tar, docker |
| TC-4.2.3 | **Backup to remote** — проверить возможность S3/scp/rsync backup | Настроить scp/rsync на внешнее хранилище или S3-совместимое | **P2** | M | rsync, s3cmd |
| TC-4.2.4 | **Backup monitoring** — добавить проверку: "backup file не старше 24 часов" | Alert если backup отсутствует > 24h | **P2** | S | cron check скрипт |
| **TC-4.3 Configuration Backup** | | | | | |
| TC-4.3.1 | **Backup nginx config** — сохранить cron-задачу: `tar czf` всех nginx конфигов | Архив `/etc/nginx/`, `/opt/gosdocker/nginx/nginx.conf` | **P1** | S | tar, cron |
| TC-4.3.2 | **Backup docker-compose.yml** — сохранять compose файл | Копия в backup Dir при изменении | **P1** | S | tar, cron |
| TC-4.3.3 | **Backup .env** — сохранять .env (без секретов в открытом виде) | Зашифрованный .env в backup dir | **P1** | S | gpg/openssl |

### Шаблон backup.sh

```bash
#!/bin/bash
# /opt/gosdocker/scripts/backup.sh
BACKUP_DIR="/opt/gosdocker/backups"
DB_DIR="${BACKUP_DIR}/db"
CONFIG_DIR="${BACKUP_DIR}/config"
DATE=$(date +%Y-%m-%d)
RETENTION_DAYS=7

mkdir -p "$DB_DIR" "$CONFIG_DIR"

# Database dump
docker exec gosdocker-db-1 pg_dump -U gosdocker gosdocker | gzip > "${DB_DIR}/${DATE}.sql.gz"

# Config backup
tar czf "${CONFIG_DIR}/${DATE}-config.tar.gz" \
  /etc/nginx/sites-enabled/gosdocker \
  /opt/gosdocker/docker-compose.yml \
  /opt/gosdocker/nginx/nginx.conf \
  /opt/gosdocker/.env 2>/dev/null

# Clean old backups
find "$DB_DIR" -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete
find "$CONFIG_DIR" -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: $(date)"
```

---

## 6. Раздел 5: CI/CD Pipeline

### Контекст

- GitHub: `Snowfedya/gosdocker`
- Branches: `master`, `security-fixes`
- `.github/workflows/` — отсутствует
- 8 uncommitted файлов (149 insertions, 30 deletions)
- Нет CI/CD вообще

### Тест-кейсы

| ID | Тест-кейс | Ожидаемый результат | Приоритет | Трудозатраты | Инструмент |
|----|-----------|---------------------|-----------|--------------|------------|
| **TC-5.1 GitHub Actions — Backend** | | | | | |
| TC-5.1.1 | **Python lint** — workflow: `flake8` или `ruff` на backend/ | Все файлы проходят lint (или количество ошибок известное и не растёт) | **P1** | M | GitHub Actions |
| TC-5.1.2 | **Python tests** — `pytest` на backend + PostgreSQL service | Все существующие тесты (27) проходят. Проверить regression | **P0** | M | `pytest`, `docker compose exec db` |
| TC-5.1.3 | **Docker build backend** — `docker build -t gosdocker-backend ./backend` | Image собирается без ошибок | **P1** | M | GitHub Actions |
| TC-5.1.4 | **Dockerfile lint** — `hadolint` на Dockerfile | Dockerfile следует best practices | **P2** | S | `hadolint` |
| **TC-5.2 GitHub Actions — Frontend** | | | | | |
| TC-5.2.1 | **Vite build** — `npm ci && npm run build` (без vue-tsc) | Build проходит (с учётом, что vue-tsc отключён) | **P0** | M | GitHub Actions |
| TC-5.2.2 | **Vitest unit tests** — `npx vitest run` | Unit + integration tests проходят | **P1** | M | GitHub Actions |
| TC-5.2.3 | **Docker build frontend** — `docker build -t gosdocker-frontend ./frontend` | Image собирается | **P1** | M | GitHub Actions |
| TC-5.2.4 | **Lint frontend** — `eslint`/`prettier` check | No errors | **P2** | S | GitHub Actions |
| **TC-5.3 CI/CD Pipeline — Full** | | | | | |
| TC-5.3.1 | **PR check** — при создании PR в master: lint + test + build | Все 3 этапа проходят. PR сливается только при зелёном статусе | **P0** | L | GitHub Actions |
| TC-5.3.2 | **Deploy to VPS** — `git push to master` → автоматический деплой на VPS | После push: `git pull` на VPS → `docker compose up -d --build` | **P1** | L | GitHub Actions + SSH deploy |
| TC-5.3.3 | **Rollback** — workflow "Rollback to previous image version" | Есть тег `:prev`, кнопка rollback в GitHub Actions | **P2** | M | GitHub Actions |
| TC-5.3.4 | **Trivy scan in CI** — `trivy image gosdocker-backend:latest --severity CRITICAL` | Критические CVE: warn (не fail) | **P2** | S | `trivy` в CI |
| **TC-5.4 Git Hygiene** | | | | | |
| TC-5.4.1 | **Uncommitted changes check** — 8 файлов не закоммичены. Создать PR для них | Все изменения закоммичены в master или security-fixes | **P1** | M | git |
| TC-5.4.2 | **Branch protection** — включить branch protection на master | Нельзя push напрямую в master, только через PR | **P2** | S | GitHub Settings |

### Пример GitHub Actions workflow (`.github/workflows/ci.yml`)

```yaml
name: CI/CD

on:
  push:
    branches: [master, security-fixes]
  pull_request:
    branches: [master]

jobs:
  backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_DB: gosdocker_test
          POSTGRES_USER: gosdocker
          POSTGRES_PASSWORD: secret
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r backend/requirements.txt
      - run: pip install pytest pytest-asyncio httpx
      - run: |
          cd backend
          DATABASE_URL=postgresql+asyncpg://gosdocker:secret@postgres:5432/gosdocker_test \
          pytest tests/ -v

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '22'
      - run: cd frontend && npm ci
      - run: cd frontend && npm run build
      - run: cd frontend && npx vitest run --reporter=verbose

  deploy:
    if: github.ref == 'refs/heads/master'
    needs: [backend, frontend]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to VPS
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.VPS_HOST }}
          username: ${{ secrets.VPS_USER }}
          key: ${{ secrets.VPS_SSH_KEY }}
          script: |
            cd /opt/gosdocker
            git pull origin master
            docker compose build backend
            docker compose up -d --no-deps --force-recreate backend
            docker compose up -d --no-deps --force-recreate frontend
            docker restart gosdocker-nginx-1
            docker image prune -f
```

---

## 7. Раздел 6: Monitoring

### Контекст

- Grafana (`gosd-grafana`): порт 3000, admin/admin, запущен 5 дней
- Prometheus (`gosd-prometheus`): порт 9090, запущен 5 дней
- **Проблема:** Prometheus собирает ТОЛЬКО себя (`localhost:9090`)
- Нет scrape targets для Docker, host, backend
- Нет GosDocker-specific дашбордов
- Нет alerting
- Нет uptime monitoring

### Тест-кейсы

| ID | Тест-кейс | Ожидаемый результат | Приоритет | Трудозатраты | Инструмент |
|----|-----------|---------------------|-----------|--------------|------------|
| **TC-6.1 Prometheus Configuration** | | | | | |
| TC-6.1.1 | **Prometheus доступен** — `curl http://localhost:9090/-/healthy` | 200 OK | **P1** | S | curl |
| TC-6.1.2 | **Node exporter** — запустить node-exporter контейнер, добавить scrape target | Сбор метрик CPU, RAM, disk, network с хоста | **P1** | M | node-exporter (prom/node-exporter) |
| TC-6.1.3 | **Docker daemon metrics** — включить experimental metrics на Docker daemon, добавить scrape target | Docker container metrics (cpu, mem, net io per container) | **P1** | M | Docker daemon, prometheus |
| TC-6.1.4 | **Backend /metrics** — добавить endpoint `/metrics` в FastAPI (prometheus_client) | Prometheus собирает request duration, request count, DB pool size | **P1** | M | `prometheus_client` Python lib |
| TC-6.1.5 | **cAdvisor** — добавить cAdvisor контейнер для контейнерных метрик | Метрики per-container CPU, memory, filesystem, network | **P2** | M | google/cadvisor |
| TC-6.1.6 | **Prometheus config test** — проверить валидность prometheus.yml | `docker exec gosd-prometheus promtool check config /etc/prometheus/prometheus.yml` → OK | **P1** | S | promtool |
| **TC-6.2 Grafana Dashboards** | | | | | |
| TC-6.2.1 | **Grafana доступна** — `curl http://localhost:3000/api/health` | 200 OK | **P1** | S | curl |
| TC-6.2.2 | **Prometheus datasource** — Grafana должна иметь datasource "Prometheus" с URL http://prometheus:9090 | Datasource валиден, Test Pass | **P1** | S | Grafana API |
| TC-6.2.3 | **GosDocker Dashboard** — создать дашборд: Container CPU, Memory, Network, Disk, Uptime | Визуализация всех Docker контейнеров | **P1** | M | Grafana API + import |
| TC-6.2.4 | **Backend Dashboard** — дашборд: Request rate, P50/P95/P99 latency, Error rate, DB pool size | Визуализация производительности API | **P2** | M | Grafana |
| TC-6.2.5 | **Disk usage panel** — процент заполнения диска, прогноз заполнения | Тренд заполнения диска + alert threshold | **P1** | S | Grafana |
| TC-6.2.6 | **Uptime panel** — uptime host + uptime containers | Визуализация времени безотказной работы | **P2** | S | Grafana |
| **TC-6.3 Alerting** | | | | | |
| TC-6.3.1 | **Disk >85% alert** — Prometheus alert rule: disk_usage > 85% → Alertmanager | Telegram/webhook notification при заполнении диска | **P1** | M | Prometheus + Alertmanager |
| TC-6.3.2 | **Container down alert** — любой GosDocker контейнер не running > 1 min | Alert | **P1** | M | Prometheus blackbox/up exporter |
| TC-6.3.3 | **Backend 5xx rate > 1%** — HTTP errors > 1% за 5 min | Alert | **P2** | M | Prometheus |
| TC-6.3.4 | **Backup stale alert** — backup file не обновлялся > 28h | Alert | **P2** | S | Prometheus + exporter |
| TC-6.3.5 | **Certificate expiry alert** — SSL cert expires < 30 days | Alert | **P1** | S | blackbox_exporter |
| TC-6.3.6 | **Alertmanager Telegram** — настроить Telegram webhook для уведомлений | Alertmanager отправляет уведомления в Telegram | **P1** | M | Alertmanager |
| **TC-6.4 Uptime Monitoring** | | | | | |
| TC-6.4.1 | **External uptime** — настроить мониторинг с uptimerobot.com или аналога | Healthcheck для https://gosdocker.ru каждые 5 минут | **P1** | S | uptimerobot.com |
| TC-6.4.2 | **Pingdom/Checkly synthetic** — синтетический мониторинг: login → API → logout | Полный user flow | **P3** | M | Checkly, Playwright |
| **TC-6.5 Logging** | | | | | |
| TC-6.5.1 | **Docker logs** — настроить centralized logging (Loki или ELK) | Логи всех container доступны для поиска | **P3** | L | Grafana Loki |
| TC-6.5.2 | **Nginx access log to stdout** — Docker nginx уже пишет в stdout | `docker logs gosdocker-nginx-1 --tail 50` — показывает access log | **P2** | S | `docker logs` |

### Пример прометеевой конфигурации (`prometheus.yml`)

```yaml
scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']

  - job_name: 'docker'
    static_configs:
      - targets: ['cadvisor:8080']

  - job_name: 'gosdocker-backend'
    static_configs:
      - targets: ['host.docker.internal:8000']
    metrics_path: '/metrics'
```

### Пример docker-compose для мониторинга (дополнительные сервисы):

```yaml
services:
  node-exporter:
    image: prom/node-exporter:latest
    network_mode: host
    pid: host
    restart: unless-stopped

  cadvisor:
    image: gcr.io/cadvisor/cadvisor:latest
    ports:
      - "8080:8080"
    volumes:
      - /:/rootfs:ro
      - /var/run:/var/run:ro
      - /sys:/sys:ro
      - /var/lib/docker/:/var/lib/docker:ro
    restart: unless-stopped

  alertmanager:
    image: prom/alertmanager:latest
    ports:
      - "9093:9093"
    volumes:
      - ./alertmanager.yml:/etc/alertmanager/alertmanager.yml
    restart: unless-stopped
```

---

## 8. Раздел 7: Zero-downtime Deploy

### Контекст

- Все развёртывания сейчас — stop + start → downtime
- Нет rolling update
- Нет healthcheck-gated deploy
- Backend — single instance

### Тест-кейсы

| ID | Тест-кейс | Ожидаемый результат | Приоритет | Трудозатраты | Инструмент |
|----|-----------|---------------------|-----------|--------------|------------|
| **TC-7.1 Blue-Green Strategy** | | | | | |
| TC-7.1.1 | **Backend scale to 2 replicas** — `docker compose up -d --scale backend=2` | Два backend контейнера, nginx балансирует (round-robin) | **P2** | M | `docker compose`, `curl` |
| TC-7.1.2 | **Zero-downtime backend deploy** — запустить 2 инстанса. Обновить один, переключить nginx, затем второй | 0 failed requests во время деплоя | **P1** | L | `ab`/`wrk` во время деплоя |
| **TC-7.2 Nginx Upstream** | | | | | |
| TC-7.2.1 | **Nginx upstream multiple backend** — добавить upstream backend { server backend:8000 max_fails=3 fail_timeout=10s; } | При падении одного backend — nginx автоматически переключается на другой | **P1** | M | Docker nginx config |
| TC-7.2.2 | **Nginx passive health check** — `max_fails=3 fail_timeout=30s` в upstream | После 3 failed запросов — backend выводится из ротации на 30s | **P2** | M | nginx upstream |
| TC-7.2.3 | **Nginx upstream frontend** — frontend статика, не требует upstream. Но nginx должен корректно обслуживать статику при падении backend | SPA страницы работают, /api не отвечает — это нормально | **P1** | S | `curl` |
| **TC-7.3 Graceful Deploy Script** | | | | | |
| TC-7.3.1 | **Deploy script** — `./deploy.sh backend` должен выполнить zero-downtime обновление | Deploy завершается без простоев | **P1** | M | bash + docker compose |
| TC-7.3.2 | **Pre-deploy healthcheck** — перед заменой контейнера убедиться, что старый здоров | Если старый backend не healthy — abort deploy | **P1** | S | bash + curl |
| TC-7.3.3 | **Post-deploy healthcheck** — после запуска нового контейнера ждать healthcheck (max 60s) | Если новый backend не стал healthy — rollback | **P1** | S | bash |

### Пример zero-downtime deploy.sh (backup)

```bash
#!/bin/bash
# /opt/gosdocker/scripts/deploy-backend.sh
set -e

echo "=== GosDocker Backend Zero-Downtime Deploy ==="

# 1. Build new image
docker build -t gosdocker-backend:new ./backend

# 2. Start new container alongside existing
docker compose up -d --no-deps --scale backend=2 --no-recreate backend_new
# Alternative approach: use docker compose with healthcheck-based rolling

# 3. Wait for new container to pass healthcheck
for i in $(seq 1 12); do
  STATUS=$(docker inspect --format='{{.State.Health.Status}}' gosdocker-backend-1 2>/dev/null || echo "starting")
  if [ "$STATUS" = "healthy" ]; then
    echo "New backend healthy after ${i}s"
    break
  fi
  sleep 5
done

# 4. Reload nginx to switch to new backend
docker exec gosdocker-nginx-1 nginx -s reload

# 5. Stop old backend
# docker compose up -d --scale backend=1 --no-recreate

echo "=== Deploy complete ==="
```

---

## 9. Раздел 8: Air-gapped Deployment

### Контекст

- GosDocker предназначен для government deployment (изолированные сети)
- Нет существующего tar+deploy.sh механизма
- Backend использует `docker build` (нужен registry)
- OWASP DC требует pull образа
- syft/trivy/cosign бандлятся в образ backend

### Тест-кейсы

| ID | Тест-кейс | Ожидаемый результат | Приоритет | Трудозатраты | Инструмент |
|----|-----------|---------------------|-----------|--------------|------------|
| **TC-8.1 Export Artifacts** | | | | | |
| TC-8.1.1 | **Docker image save** — `docker save gosdocker-backend:latest -o gosdocker-backend.tar` | TAR файл создаётся, gzip сжимает | **P1** | S | `docker save` |
| TC-8.1.2 | **Docker image save all** — сохранить все 4 GosDocker образа | backend.tar, frontend.tar, nginx-alpine.tar, postgres-15.tar (+ monitoring) | **P1** | M | `docker save` |
| TC-8.1.3 | **Archive script** — `tar czf gosdocker-deploy.tar.gz` всех образов + compose + .env + nginx configs | Единый архив для air-gapped передачи | **P1** | S | tar |
| **TC-8.2 Deploy in Air-gap** | | | | | |
| TC-8.2.1 | **Deploy script** — `deploy-airgap.sh` на целевой машине без доступа в интернет | Скрипт: docker load всех образов → docker compose up -d | **P1** | M | bash |
| TC-8.2.2 | **Air-gap verification** — в целевой среде заблокировать весь исходящий трафик (iptables) | `docker compose up -d` работает, приложение отвечает | **P1** | M | `iptables -A OUTPUT ... DROP` |
| TC-8.2.3 | **Mirror registry** — если нужен docker pull во время работы — настроить локальный registry mirror | Все образы доступны из mirror | **P2** | L | Docker registry mirror |
| TC-8.2.4 | **Offline OWASP DC** — сохранить `owasp/dependency-check:latest` образ | `docker load` на целевой машине, OWASP работает | **P2** | S | `docker save/load` |
| **TC-8.3 Alternative: Docker Registry** | | | | | |
| TC-8.3.1 | **Self-hosted registry** — установить локальный Docker registry | `docker push` → `docker pull` из localhost registry работает | **P3** | M | `registry:2` |
| TC-8.3.2 | **Registry auth** — добавить basic auth на registry | Без авторизации — pull работает (внутренняя сеть) | **P3** | M | registry config |

### Пример deploy-airgap.sh

```bash
#!/bin/bash
# deploy-airgap.sh — запуск в изолированной среде
set -e

ARCHIVE_DIR="$(dirname "$0")/gosdocker-deploy"

echo "=== GosDocker Air-Gapped Deployment ==="

# 1. Load Docker images
for tarfile in "$ARCHIVE_DIR"/images/*.tar; do
  echo "Loading $tarfile..."
  docker load -i "$tarfile"
done

# 2. Create required directories
mkdir -p /tmp/gosdocker-constructor

# 3. Copy compose + configs
cp "$ARCHIVE_DIR"/docker-compose.yml /opt/gosdocker/
cp "$ARCHIVE_DIR"/nginx/nginx.conf /opt/gosdocker/nginx/

# 4. Start services
cd /opt/gosdocker
docker compose up -d

# 5. Verify
echo "Waiting for healthcheck..."
sleep 10
curl -f http://localhost:8000/health || echo "WARNING: healthcheck failed"

echo "=== Deployment complete ==="
```

---

## 10. Раздел 9: Load Testing

### Контекст

- Backend: FastAPI + asyncpg, uvicorn workers
- Pipeline: 12-23s per component (Build → Scan → Package → Sign → Register)
- Один uvicorn worker (single-threaded event loop)
- 7.8GB RAM, 4.7GB available
- Load average сейчас: 3.23 (высоковат для 8 логических ядер?)

### Тест-кейсы

| ID | Тест-кейс | Ожидаемый результат | Приоритет | Трудозатраты | Инструмент |
|----|-----------|---------------------|-----------|--------------|------------|
| **TC-9.1 Backend API Load** | | | | | |
| TC-9.1.1 | **Лёгкая нагрузка** — `/api/categories` 1000 запросов, 50 concurrent | P95 < 200ms, 0 errors | **P1** | M | `wrk` / `ab` |
| TC-9.1.2 | **Средняя нагрузка** — `/api/components` 500 запросов, 100 concurrent | P95 < 500ms, 0 errors | **P1** | M | `wrk` |
| TC-9.1.3 | **Максимальная нагрузка** — `/api/components` + `/api/categories` + `/api/stacks` 2000 rpm | P95 < 1s, error rate < 0.1% | **P2** | M | `wrk`, `vegeta` |
| TC-9.1.4 | **DB connection pool limit** — 200 concurrent запросов к БД | asyncpg pool limit (default 10) не исчерпан. Запросы ждут в очереди, не падают | **P1** | M | `wrk`, `docker logs` |
| **TC-9.2 Pipeline Load** | | | | | |
| TC-9.2.1 | **1 параллельная сборка** — `POST /api/registry/nginx/build?profile=basic` | Pipeline завершается за 15-30s | **P0** | S | curl, watch |
| TC-9.2.2 | **2 параллельные сборки** — два компонента одновременно (nginx + postgresql) | Обе завершаются за 30-60s. Взаимной блокировки нет | **P1** | M | background curl |
| TC-9.2.3 | **3 параллельные сборки** — nginx + postgresql + prometheus | Обе завершаются. Check: нет конфликтов docker build, syft cache используется | **P1** | M | background curl |
| TC-9.2.4 | **Constructor 5 компонентов** — `POST /api/constructor` с 5 компонентами | Pipeline завершается за 60-120s. Нет OOM | **P1** | L | curl + timeout 180 |
| TC-9.2.5 | **10 компонентов (все)** — `POST /api/constructor` со всеми 10 компонентами | Pipeline завершается (может быть медленно). Оценить bottleneck | **P2** | L | curl + timeout 300 |
| **TC-9.3 System Resources** | | | | | |
| TC-9.3.1 | **CPU under load** — во время пиковой нагрузки CPU < 80% (не упирается) | CPU user < 80%, iowait < 10% | **P1** | M | `top`, `mpstat` |
| TC-9.3.2 | **Memory under load** — во время 3 pipeline сборок RAM не превышает 80% | Доступной памяти > 1GB (не уходит в swap активно) | **P1** | M | `free -h`, `docker stats` |
| TC-9.3.3 | **Disk I/O under load** — iostat при строительстве | iowait < 20%, disk util < 80% | **P2** | M | `iostat -x 1` |
| **TC-9.4 Benchmark Decision** | | | | | |
| TC-9.4.1 | **Определить max parallel builds** — последовательно увеличивать число параллельных сборок до degradation | Документировать: N параллельных сборок — безопасный максимум | **P1** | L | grad. load test |
| TC-9.4.2 | **Uvicorn workers** — протестировать с `workers: 4` (gunicorn + uvicorn workers) | Сравнить throughput без workers vs с workers=4 | **P2** | M | wrk A/B |
| TC-9.4.3 | **AsyncPG pool sizing** — протестировать pool_size=5 vs 10 vs 20 | Найти оптимальный pool_size для текущих нагрузок | **P2** | M | wrk +

 pool config |

### Пример load test команды

```bash
# API load with wrk
wrk -t4 -c50 -d30s --latency https://gosdocker.ru/api/categories
wrk -t4 -c100 -d30s --latency https://gosdocker.ru/api/components

# Pipeline build timing
time curl -s -X POST http://127.0.0.1:8000/api/registry/nginx/build?profile=basic

# Parallel builds
for slug in nginx postgresql prometheus; do
  curl -s -X POST "http://127.0.0.1:8000/api/registry/$slug/build?profile=basic" &
done
wait
```

---

## 11. Раздел 10: Disaster Recovery

### Контекст

- Нет backup strategy
- Нет DR plan
- Нет tested restore procedure
- Диск 75% — может привести к проблемам
- Нет swap monitoring (1.1/3.9G used)

### Тест-кейсы

| ID | Тест-кейс | Ожидаемый результат | Приоритет | Трудозатраты | Инструмент |
|----|-----------|---------------------|-----------|--------------|------------|
| **TC-10.1 Restore from Backup** | | | | | |
| TC-10.1.1 | **Полное восстановление** — сценарий: сервер упал. Поднять новый VPS, восстановить все данные | 1. Setup Docker + compose<br>2. `docker load` images<br>3. `docker compose up -d`<br>4. `psql < backup.sql`<br>5. Приложение работает | **P0** | M | bash + psql |
| TC-10.1.2 | **Документирование DR** — создать `DISASTER_RECOVERY.md` с пошаговыми инструкциями | Документ: 1 страница, чёткие шаги, команды копировать-вставить | **P0** | S | markdown |
| **TC-10.2 Data Loss Scenarios** | | | | | |
| TC-10.2.1 | **Corrupted database** — `TRUNCATE` таблиц components. Восстановить из backup | `psql < backup.sql` → все данные восстановлены | **P0** | M | psql |
| TC-10.2.2 | **Volume loss** — `docker volume rm gosdocker_pgdata`. Восстановить | `docker compose up -d db` → fresh volume → `psql < backup.sql` | **P0** | M | docker + psql |
| TC-10.2.3 | **Host disk full** — смоделировать 100% disk (dd). Освободить место | Скрипт cleanup (cleanup-cache.sh, docker image prune, log rotation) | **P1** | M | dd, docker system prune |
| TC-10.2.4 | **Container image corrupted** — удалить образ, container in Exited | `docker compose pull` или `docker compose build` + `up -d` | **P1** | S | docker compose |
| **TC-10.3 Fail-over Scenarios** | | | | | |
| TC-10.3.1 | **PostgreSQL restart** — `docker restart gosdocker-db-1` | Backend должен автоматически переподключиться (asyncpg retry) | **P1** | M | docker restart |
| TC-10.3.2 | **Full host reboot** — `reboot` (запланировано) | После reboot: Docker daemon → containers restart → all healthy | **P0** | L | scheduled reboot |
| TC-10.3.3 | **Docker socket disconnect** — `docker exec gosdocker-backend-1` перестаёт видеть host | Pipeline OWASP DC и BuildStep падают gracefully (placeholder artifacts) | **P1** | M | `docker exec` + check pipeline |
| TC-10.3.4 | **Network partition** — контейнеры не видят друг друга | Nginx 502 для /api, healthcheck frontend падает. При восстановлении сети — всё оживает | **P2** | M | `docker network disconnect` |
| **TC-10.4 Security Incidents** | | | | | |
| TC-10.4.1 | **Compromised backend container** — злоумышленник получил shell в backend | `docker ps` показывает подозрительный процесс. Kill + restart из чистой image | **P0** | M | docker |
| TC-10.4.2 | **Compromised SSH** — SSH key leaked. Rotate keys, check access | `~/.ssh/authorized_keys` — только authorised keys. Fail2ban работает | **P0** | S | `fail2ban-client status` |
| **TC-10.5 Disk Cleanup** | | | | | |
| TC-10.5.1 | **Cleanup script** — запустить `docker system prune -af` (аккуратно) | Освободить ~1GB (build cache + dangling images) | **P0** | S | `docker system prune` |
| TC-10.5.2 | **Old images** — удалить образы >30 дней, не используемые running containers | Список unused images → remove | **P1** | S | `docker image prune -a --filter "until=720h"` |
| TC-10.5.3 | **Docker build cache** — очистить build cache | `docker builder prune` → освободить build cache | **P1** | S | `docker builder prune` |
| TC-10.5.4 | **Log rotation** — настроить logrotate для Docker container logs | `/var/lib/docker/containers/*/*.log` ротируются | **P1** | M | logrotate + daemon.json |

---

## 12. Сводная таблица

### Приоритеты тест-кейсов

| Раздел | P0 | P1 | P2 | P3 | Всего |
|--------|----|----|----|----|-------|
| 1. Docker Compose | 3 | 4 | 4 | 1 | 12 |
| 2. Nginx | 5 | 5 | 4 | 1 | 15 |
| 3. Production-ready | 5 | 8 | 3 | 0 | 16 |
| 4. Backup/Restore | 6 | 6 | 4 | 2 | 18 |
| 5. CI/CD | 3 | 8 | 5 | 0 | 16 |
| 6. Monitoring | 0 | 10 | 5 | 3 | 18 |
| 7. Zero-downtime | 0 | 5 | 3 | 0 | 8 |
| 8. Air-gapped | 0 | 5 | 3 | 2 | 10 |
| 9. Load testing | 1 | 10 | 5 | 0 | 16 |
| 10. Disaster recovery | 7 | 6 | 3 | 0 | 16 |
| **Итого** | **30** | **67** | **39** | **9** | **145** |

### Трудозатраты

| Размер | Кол-во | Часы |
|--------|--------|------|
| S (до 2h) | ~65 | ~65h |
| M (2-4h) | ~65 | ~195h |
| L (4-8h) | ~15 | ~90h |
| **Всего** | **145** | **~350h** |

### Приоритетная дорожная карта

| Этап | Срок | Фокус | Часы | ТС |
|------|------|-------|------|----|
| **Sprint 1: "Стабильность"** | 1-3 дня | Restart policy, healthchecks, graceful shutdown, backup script, certbot cron, cleanup disk | ~30h | TC-1.2-1.5, TC-3.1-3.3, TC-4.1, TC-10.5 |
| **Sprint 2: "CI/CD"** | 3-5 дней | GitHub Actions, git commit, lint, test, build, deploy to VPS | ~25h | TC-5.1-5.4 |
| **Sprint 3: "Мониторинг"** | 3-5 дней | Prometheus targets, Grafana dashboards, Alertmanager, node-exporter, backend metrics | ~30h | TC-6.1-6.4 |
| **Sprint 4: "Production hardening"** | 2-4 дня | Rate limiting, security headers, resource limits, OOM, daemon.json | ~25h | TC-2.3, TC-3.2, TC-3.4 |
| **Sprint 5: "Load & DR"** | 3-5 дней | Load test, max parallel builds, DR doc, restore test, air-gapped script | ~25h | TC-9, TC-10, TC-8 |
| **Sprint 6: "Zero-downtime"** | 2-3 дня | Scale, nginx upstream, deploy script with healthcheck | ~15h | TC-7 |

### Инструменты

| Инструмент | Назначение | Команда установки |
|-----------|-----------|-------------------|
| `wrk` / `ab` | HTTP load testing | `apt install wrk` / `apache2-utils` |
| `vegeta` | Load testing with reports | `go install github.com/tsenart/vegeta/v12@latest` |
| `promtool` | Validate Prometheus config | В составе Prometheus |
| `hadolint` | Dockerfile lint | `docker run hadolint/hadolint` |
| `ruff` | Python linter | `pip install ruff` |
| `node-exporter` | Host metrics | `docker run prom/node-exporter` |
| `cadvisor` | Container metrics | `docker run gcr.io/cadvisor/cadvisor` |
| `uptimerobot` | External uptime | https://uptimerobot.com |
| `pg_dump`/`psql` | PostgreSQL backup/restore | `apt install postgresql-client` |

---

## Приложение A: Чек-лист быстрой проверки production (5 минут)

```bash
# 1. Все ли контейнеры запущены?
docker ps --filter "name=gosdocker" --format "table {{.Names}}\t{{.Status}}"

# 2. Healthcheck статус
docker inspect --format='{{.Name}} → {{.State.Health.Status}}' $(docker ps -q --filter "name=gosdocker")

# 3. HTTPS доступен?
curl -sI https://gosdocker.ru | head -5

# 4. HSTS header?
curl -sI https://gosdocker.ru | grep -i strict-transport

# 5. API работает?
curl -s https://gosdocker.ru/health

# 6. Free disk?
df -h /

# 7. Backup свежий?
ls -la /opt/gosdocker/backups/db/

# 8. SSL expires?
certbot certificates | grep -A2 "gosdocker.ru"
```

## Приложение B: Известные проблемы на 2 июня 2026

| # | Проблема | Раздел | Статус |
|---|----------|--------|--------|
| 1 | Нет restart policy ни у одного сервиса (кроме default `no`) | TC-1.2 | 🔴 Критично |
| 2 | Нет graceful shutdown (SIGTERM не обрабатывается) | TC-3.3 | 🔴 Критично |
| 3 | Нет backup стратегии и скрипта | TC-4.1 | 🔴 Критично |
| 4 | Нет CI/CD | TC-5.0 | 🔴 Критично |
| 5 | Диск 75% — требуется очистка | TC-10.5 | 🟡 Высокий |
| 6 | Prometheus собирает только себя | TC-6.1 | 🟡 Высокий |
| 7 | Нет resource limits | TC-3.2 | 🟡 Высокий |
| 8 | Нет rate limiting | TC-2.3 | 🟡 Средний |
| 9 | Security headers неполные | TC-2.3.2 | 🟡 Средний |
| 10 | Frontend healthcheck unhealthy (но работает) | TC-1.5 | 🟡 Средний |
| 11 | Нет zero-downtime deploy | TC-7.0 | 🟡 Средний |
| 12 | Нет air-gapped deploy скрипта | TC-8.0 | 🟡 Средний |
| 13 | gosdocker-fix дублирующиеся сервисы (Created) | TC-1.11 | 🔵 Низкий |
| 14 | Swap usage 1.1/3.9GB | TC-10.3 | 🔵 Низкий |
| 15 | Load average 3.23 (требует изучения) | TC-9.3 | 🔵 Низкий |
