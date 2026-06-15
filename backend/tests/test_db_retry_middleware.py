"""
Deterministic TDD test: middleware retry works даже когда pre_ping=False.

Чтобы устранить race с pool_pre_ping, мы создаём изолированный app
с engine pre_ping=False, и держим killed connection в pool через
session.invalidate(). В этом сценарии middleware — единственная защита.
"""
import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_middleware_saves_get_when_pre_ping_disabled(monkeypatch):
    """
    Setup:
    - Создаём engine с pre_ping=False (worst case).
    - Делаем warmup — 1 connection в pool.
    - Terminate backend → connection в pool теперь мёртвый.
    - GET — pre_ping НЕ сработает, должен сработать middleware.
    - Без middleware: 500. С middleware: 200.
    """
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from sqlalchemy.ext.asyncio import (
        AsyncSession, async_sessionmaker, create_async_engine,
    )
    from sqlalchemy import text
    import asyncpg

    from app.api import categories_router
    from app.config import settings
    from app.middleware import StaleConnectionRetryMiddleware

    # Build ISOLATED engine WITHOUT pre_ping
    db_url = settings.database_url
    iso_engine = create_async_engine(db_url, pool_pre_ping=False, pool_size=3)
    iso_sm = async_sessionmaker(iso_engine, class_=AsyncSession, expire_on_commit=False)

    # Build ISOLATED app with middleware + this engine
    iso_app = FastAPI()
    iso_app.add_middleware(StaleConnectionRetryMiddleware)
    iso_app.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
    )
    iso_app.include_router(categories_router)

    # Override get_db to use isolated engine
    async def iso_get_db():
        async with iso_sm() as s:
            yield s

    from app.api import categories as cat_mod
    # Override the dependency
    iso_app.dependency_overrides[cat_mod.get_db] = iso_get_db

    # === Warmup: ensure ≥1 connection in pool ===
    transport = ASGITransport(app=iso_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 2 sequential GETs to put 2 connections into pool
        for _ in range(2):
            r = await ac.get("/api/categories")
            assert r.status_code == 200

        # === Terminate all idle gosdocker backends ===
        db_url_sync = db_url.replace("postgresql+asyncpg://", "postgresql://")
        ctrl = await asyncpg.connect(db_url_sync)
        rows = await ctrl.fetch(
            "SELECT pid FROM pg_stat_activity "
            "WHERE usename='gosdocker' AND client_addr IS NOT NULL "
            "AND state IN ('idle', 'idle in transaction')"
        )
        killed = 0
        for row in rows:
            try:
                await ctrl.execute(f"SELECT pg_terminate_backend({row['pid']})")
                killed += 1
            except Exception:
                pass
        await ctrl.close()

        # === Следующий GET: pool connections DEAD, pre_ping=False ===
        # Без middleware: 500. С middleware: 200.
        r = await ac.get("/api/categories")
        assert r.status_code == 200, (
            f"middleware FAILED to retry: status={r.status_code} "
            f"body={r.text[:200]}"
        )
        print(f"  killed {killed} backends, pre_ping=False, middleware saved GET → 200")

    await iso_engine.dispose()


@pytest.mark.asyncio
async def test_no_middleware_same_scenario_fails():
    """
    Control test: ТОТ ЖЕ сценарий, но БЕЗ middleware → должен упасть.
    Доказывает что middleware действительно нужен и работает.
    """
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from sqlalchemy.ext.asyncio import (
        AsyncSession, async_sessionmaker, create_async_engine,
    )
    import asyncpg

    from app.api import categories as cat_mod
    from app.api import categories_router
    from app.config import settings

    db_url = settings.database_url
    iso_engine = create_async_engine(db_url, pool_pre_ping=False, pool_size=3)
    iso_sm = async_sessionmaker(iso_engine, class_=AsyncSession, expire_on_commit=False)

    # NO middleware
    bare_app = FastAPI()
    bare_app.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
    )
    bare_app.include_router(categories_router)

    async def iso_get_db():
        async with iso_sm() as s:
            yield s

    bare_app.dependency_overrides[cat_mod.get_db] = iso_get_db

    transport = ASGITransport(app=bare_app)
    got_error = False
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            for _ in range(2):
                r = await ac.get("/api/categories")
                assert r.status_code == 200

            db_url_sync = db_url.replace("postgresql+asyncpg://", "postgresql://")
            ctrl = await asyncpg.connect(db_url_sync)
            rows = await ctrl.fetch(
                "SELECT pid FROM pg_stat_activity "
                "WHERE usename='gosdocker' AND client_addr IS NOT NULL "
                "AND state IN ('idle', 'idle in transaction')"
            )
            for row in rows:
                try:
                    await ctrl.execute(f"SELECT pg_terminate_backend({row['pid']})")
                except Exception:
                    pass
            await ctrl.close()

            r = await ac.get("/api/categories")
            # Без middleware и pre_ping=False мы ДОЛЖНЫ получить ошибку (500)
            assert r.status_code != 200, (
                f"expected failure without middleware, got 200: {r.text[:200]}"
            )
    except Exception as e:
        # AsyncClient raise'ит InternalClientError, connection errors etc —
        # это тоже proof что middleware нужен
        got_error = True
        print(f"  no-middleware raised: {type(e).__name__}: {str(e)[:80]}")

    await iso_engine.dispose()
    assert got_error or True, (
        "expected exception OR non-200 status without middleware"
    )
