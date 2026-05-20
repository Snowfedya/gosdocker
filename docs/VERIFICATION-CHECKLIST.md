# Verification Checklist - GosDocker

**Purpose:** Manual verification that each solution deploys and works correctly.
**Generated:** 2026-03-15

---

## Overview

This checklist provides step-by-step verification for all 7 solutions available in GosDocker platform. Follow each section to verify that containers start, healthchecks pass, and services respond correctly.

### Solutions Covered

| # | Solution | Category | Registry |
|---|---------|----------|----------|
| 1 | PostgreSQL | Databases | Docker Hub |
| 2 | Nginx | Web Servers | Docker Hub |
| 3 | Redis | Caching | Docker Hub |
| 4 | Angie | Russian Software | Yandex Cloud |
| 5 | Tarantool | Russian Software | Yandex Cloud |
| 6 | Postgres Pro | Russian Software | Yandex Cloud |
| 7 | Bitrix24 | Business Apps | Yandex Cloud |

---

## Prerequisites

Before starting verification:

- [ ] Docker 24.0+ installed and running
- [ ] Docker Compose v2 available
- [ ] GosDocker platform running (`docker compose up -d` from Diplom/)
- [ ] For Russian software: `YANDEX_REGISTRY_ID` configured in `.env`

### Yandex Container Registry Setup (Russian Software)

For Angie, Tarantool, Postgres Pro, and Bitrix24:

```bash
# 1. Set YANDEX_REGISTRY_ID in .env
echo "YANDEX_REGISTRY_ID=your-registry-id" >> .env

# 2. Login to Yandex Container Registry
docker login cr.yandex
# Use OAuth token or IAM token from Yandex Cloud
```

---

## Verification Steps (Per Solution)

For each solution, complete these 4 steps:

1. **Download YAML** - Get docker-compose.yml from GosDocker UI
2. **Start Container** - Run `docker compose up -d`
3. **Healthcheck** - Verify container is healthy
4. **Service Response** - Test service responds correctly

---

## 1. PostgreSQL

### Step 1: Download YAML
- [ ] Open GosDocker catalog at http://localhost
- [ ] Navigate to "Базы данных" (Databases) category
- [ ] Select PostgreSQL
- [ ] Click "Скачать" (Download) button
- [ ] Save file as `postgres-compose.yml`

### Step 2: Start Container
```bash
# Create data directory
mkdir -p pgdata

# Start container
docker compose -f postgres-compose.yml up -d

# Verify status
docker compose ps
# Expected: "running" or "healthy"
```

### Step 3: Healthcheck
```bash
# Check PostgreSQL readiness
docker compose -f postgres-compose.yml exec postgres pg_isready -U postgres

# Expected output: "postgres:5432 - accepting connections"
```

### Step 4: Service Response
```bash
# Connect and run test query
docker compose -f postgres-compose.yml exec postgres psql -U postgres -c "SELECT version();"

# Expected: PostgreSQL version string (e.g., "PostgreSQL 15.5 ...")
```

### Cleanup
- [ ] Leave container running for demo (per verification decision)

---

## 2. Nginx

### Step 1: Download YAML
- [ ] Open GosDocker catalog at http://localhost
- [ ] Navigate to "Веб-серверы" (Web Servers) category
- [ ] Select Nginx
- [ ] Click "Скачать" (Download) button
- [ ] Save file as `nginx-compose.yml`

### Step 2: Start Container
```bash
# Create html directory with test content
mkdir -p html
echo '<h1>GosDocker Nginx Test</h1>' > html/index.html

# Start container
docker compose -f nginx-compose.yml up -d

# Verify status
docker compose ps
# Expected: "running" or "healthy"
```

### Step 3: Healthcheck
```bash
# Check Nginx configuration
docker compose -f nginx-compose.yml exec nginx nginx -t

# Expected output:
# nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
# nginx: configuration file /etc/nginx/nginx.conf test is successful
```

### Step 4: Service Response
```bash
# Test HTTP response
curl -I http://localhost:80

# Expected: HTTP/1.1 200 OK
# Or test content:
curl http://localhost:80
# Expected: <h1>GosDocker Nginx Test</h1>
```

### Cleanup
- [ ] Leave container running for demo

---

## 3. Redis

### Step 1: Download YAML
- [ ] Open GosDocker catalog at http://localhost
- [ ] Navigate to "Кэширование" (Caching) category
- [ ] Select Redis
- [ ] Click "Скачать" (Download) button
- [ ] Save file as `redis-compose.yml`

### Step 2: Start Container
```bash
# Start container
docker compose -f redis-compose.yml up -d

# Verify status
docker compose ps
# Expected: "running" or "healthy"
```

### Step 3: Healthcheck
```bash
# Check Redis ping
docker compose -f redis-compose.yml exec redis redis-cli ping

# Expected output: PONG
```

### Step 4: Service Response
```bash
# Set and get a test value
docker compose -f redis-compose.yml exec redis redis-cli SET test_key "GosDocker"
docker compose -f redis-compose.yml exec redis redis-cli GET test_key

# Expected: "GosDocker"
```

### Cleanup
- [ ] Leave container running for demo

---

## 4. Angie (Russian Software)

### Prerequisites
- [ ] YANDEX_REGISTRY_ID configured
- [ ] Docker logged into cr.yandex

### Step 1: Download YAML
- [ ] Open GosDocker catalog at http://localhost
- [ ] Navigate to "Российское ПО" (Russian Software) category
- [ ] Select Angie
- [ ] Click "Скачать" (Download) button
- [ ] Save file as `angie-compose.yml`

### Step 2: Start Container
```bash
# Create config and html directories
mkdir -p conf.d html ssl
echo 'server { listen 80; root /usr/share/angie/html; }' > conf.d/default.conf
echo '<h1>Angie from GosDocker</h1>' > html/index.html

# Start container
docker compose -f angie-compose.yml up -d

# Verify status
docker compose ps
# Expected: "running" or "healthy"
```

### Step 3: Healthcheck
```bash
# Check Angie configuration
docker compose -f angie-compose.yml exec angie angie -t

# Expected: "test is successful"
```

### Step 4: Service Response
```bash
# Test HTTP response
curl -I http://localhost:80

# Expected: HTTP/1.1 200 OK
```

### Cleanup
- [ ] Leave container running for demo

---

## 5. Tarantool (Russian Software)

### Prerequisites
- [ ] YANDEX_REGISTRY_ID configured
- [ ] Docker logged into cr.yandex

### Step 1: Download YAML
- [ ] Open GosDocker catalog at http://localhost
- [ ] Navigate to "Российское ПО" (Russian Software) category
- [ ] Select Tarantool
- [ ] Click "Скачать" (Download) button
- [ ] Save file as `tarantool-compose.yml`

### Step 2: Start Container
```bash
# Create data and app directories
mkdir -p tarantool-data tarantool-app

# Start container
docker compose -f tarantool-compose.yml up -d

# Verify status
docker compose ps
# Expected: "running" or "healthy"
```

### Step 3: Healthcheck
```bash
# Check Tarantool status
docker compose -f tarantool-compose.yml exec tarantool tarantoolctl status

# Or via console
docker compose -f tarantool-compose.yml exec -it tarantool tarantool
# Expected: Tarantool console ready (type 'quit' to exit)
```

### Step 4: Service Response
```bash
# Connect to Tarantool console and run test
docker compose -f tarantool-compose.yml exec tarantool tarantool -e "print('Tarantool running OK')"

# Expected: Tarantool running OK
```

### Cleanup
- [ ] Leave container running for demo

---

## 6. Postgres Pro (Russian Software)

### Prerequisites
- [ ] YANDEX_REGISTRY_ID configured
- [ ] Docker logged into cr.yandex

### Step 1: Download YAML
- [ ] Open GosDocker catalog at http://localhost
- [ ] Navigate to "Российское ПО" (Russian Software) category
- [ ] Select Postgres Pro
- [ ] Click "Скачать" (Download) button
- [ ] Save file as `postgres-pro-compose.yml`

### Step 2: Start Container
```bash
# Create data directory
mkdir -p pgpro-data

# Start container
docker compose -f postgres-pro-compose.yml up -d

# Verify status
docker compose ps
# Expected: "running" or "healthy"
```

### Step 3: Healthcheck
```bash
# Check Postgres Pro readiness
docker compose -f postgres-pro-compose.yml exec postgres-pro pg_isready -U postgres

# Expected output: "accepting connections"
```

### Step 4: Service Response
```bash
# Connect and run test query
docker compose -f postgres-pro-compose.yml exec postgres-pro psql -U postgres -c "SELECT version();"

# Expected: Postgres Pro version string
```

### Cleanup
- [ ] Leave container running for demo

---

## 7. Bitrix24 (Russian Software)

### Prerequisites
- [ ] YANDEX_REGISTRY_ID configured
- [ ] Docker logged into cr.yandex

### Step 1: Download YAML
- [ ] Open GosDocker catalog at http://localhost
- [ ] Navigate to "Бизнес-приложения" (Business Apps) category
- [ ] Select Bitrix24
- [ ] Click "Скачать" (Download) button
- [ ] Save file as `bitrix24-compose.yml`

### Step 2: Start Container
```bash
# Bitrix24 includes MySQL database in compose
docker compose -f bitrix24-compose.yml up -d

# Verify status (wait ~60s for startup)
docker compose ps
# Expected: Both "bitrix24" and "bitrix24-db" containers running
```

### Step 3: Healthcheck
```bash
# Check Bitrix24 application
docker compose -f bitrix24-compose.yml exec bitrix24 curl -f http://localhost/

# Expected: HTTP 200 response

# Check MySQL database
docker compose -f bitrix24-compose.yml exec db mysqladmin ping -h localhost

# Expected: "mysqld is alive"
```

### Step 4: Service Response
```bash
# Test HTTP response
curl -I http://localhost:80

# Expected: HTTP/1.1 200 OK or redirect to setup page
```

### Cleanup
- [ ] Leave container running for demo

---

## Verification Summary

After completing all sections:

| Solution | Download | Start | Healthcheck | Response | Status |
|----------|----------|-------|-------------|----------|--------|
| PostgreSQL | [ ] | [ ] | [ ] | [ ] | [ ] |
| Nginx | [ ] | [ ] | [ ] | [ ] | [ ] |
| Redis | [ ] | [ ] | [ ] | [ ] | [ ] |
| Angie | [ ] | [ ] | [ ] | [ ] | [ ] |
| Tarantool | [ ] | [ ] | [ ] | [ ] | [ ] |
| Postgres Pro | [ ] | [ ] | [ ] | [ ] | [ ] |
| Bitrix24 | [ ] | [ ] | [ ] | [ ] | [ ] |

---

## Notes

### Russian Software Configuration
- Russian software (Angie, Tarantool, Postgres Pro, Bitrix24) uses Yandex Container Registry
- Set `YANDEX_REGISTRY_ID` environment variable before deployment
- Login to registry: `docker login cr.yandex`
- Yandex Container Registry is certified by FSTEC and GOST for Russian government use

### Cleanup Commands (Optional)
To stop and remove containers after verification:

```bash
# Stop specific service
docker compose -f <service>-compose.yml down

# Stop all containers
docker compose down

# Remove volumes (WARNING: deletes data)
docker compose -f <service>-compose.yml down -v
```

### Troubleshooting

**Container fails to start:**
- Check Docker logs: `docker compose -f <file> logs`
- Verify image pull succeeded: `docker images`
- For Russian software, verify YANDEX_REGISTRY_ID is correct

**Healthcheck fails:**
- Wait for startup period (some containers need 30-60s)
- Check container logs for errors
- Verify network connectivity

**Service not responding:**
- Check port conflicts: `docker ps` or `netstat -tlnp`
- Verify firewall allows port access
- Check if container is actually running

---

## Issue Log

Document any issues encountered during verification:

| Date | Solution | Issue | Resolution | Notes |
|------|----------|-------|------------|-------|
| | | | | |

---

*Checklist version: 1.0*
*Last updated: 2026-03-15*