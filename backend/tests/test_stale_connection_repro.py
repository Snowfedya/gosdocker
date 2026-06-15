"""
TDD test для Lesson #32 followup: pool_pre_ping=True + TCPTransport closed.

Production сценарий: несколько FastAPI workers держут connections в pool.
db перезагружается (Recreate). Первый запрос после restart ловит 500.
"""
import asyncio
import os
import uuid

import asyncpg
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession


@pytest.mark.asyncio
async def test_pre_ping_recovers_when_idle_pool_connections_terminated():
    """
    1. Открываем 3 connections в pool (warmup).
    2. Connections лежат в pool idle (НЕ закрываем sessions).
    3. Terminate эти backends через control connection.
    4. Делаем новые SELECTs — pre_ping должен сбросить stale conns.
    """
    db_url = os.environ.get(
        "DATABASE_URL", "postgresql+asyncpg://gosdocker:***@db:5432/gosdocker"
    )
    engine = create_async_engine(
        db_url, echo=False, pool_pre_ping=True, pool_recycle=300, pool_size=5
    )
    sm = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # === Step 1: открываем 3 sessions и ДЕРЖИМ ИХ ОТКРЫТЫМИ (не закрываем) ===
    sessions = []
    for i in range(3):
        s = sm()
        r = await s.execute(text(f"SELECT {i} AS x"))
        assert r.scalar() == i
        sessions.append(s)

    # Теперь 3 connections checked out из pool
    print(f"  pool checkedout: {engine.pool.checkedout()}")

    # === Step 2: terminate asyncpg backends через ОТДЕЛЬНЫЙ control connection ===
    control_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    control_app = f"test-ctrl-{uuid.uuid4().hex[:8]}"
    sep = "?" if "?" not in control_url else "&"
    control = await asyncpg.connect(f"{control_url}{sep}application_name={control_app}")
    rows = await control.fetch(
        "SELECT pid, state FROM pg_stat_activity "
        "WHERE usename='gosdocker' AND client_addr IS NOT NULL "
        "AND state IN ('idle', 'idle in transaction')"
    )
    print(f"  found {len(rows)} gosdocker backends to kill")
    assert len(rows) >= 3, f"expected ≥3 gosdocker backends, got {len(rows)}"
    for r in rows:
        try:
            await control.execute(f"SELECT pg_terminate_backend({r['pid']})")
        except Exception as e:
            print(f"  terminate err: {e}")
    await control.close()

    # === Step 3: пытаемся делать SELECTs через "stale" sessions ===
    errors = []
    for i, s in enumerate(sessions):
        try:
            r = await s.execute(text(f"SELECT {i+10} AS x"))
            print(f"  session {i}: result={r.scalar()}")
        except Exception as e:
            err = f"session {i}: {type(e).__name__}: {str(e)[:100]}"
            print(f"  {err}")
            errors.append(err)

    # Cleanup: закрываем sessions (должны swallow exceptions)
    for s in sessions:
        try:
            await s.close()
        except Exception:
            pass
    await engine.dispose()

    if errors:
        pytest.fail(
            f"pool_pre_ping did NOT recover {len(errors)} stale connections: {errors}"
        )
