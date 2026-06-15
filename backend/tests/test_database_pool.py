"""
AC-INF-1: database engine must have pool_pre_ping=True.

Why: After `docker compose up -d backend` (which can recreate the
backend container while the db container persists across restarts
with new connections on the other end), asyncpg connections from
the old pool become stale. The first few requests after restart
fail with:

  asyncpg.exceptions._base.InterfaceError:
      cannot perform operation: another operation is in progress

pool_pre_ping=True makes SQLAlchemy emit a cheap "SELECT 1" before
each checkout, so stale connections are detected and replaced.
This is the SQLAlchemy-recommended fix for connection-recycle races.

We assert on the engine configuration, not on the network behavior
(it'd be flaky in CI). This guarantees the fix is in place.
"""
from sqlalchemy.ext.asyncio import AsyncEngine


def test_engine_has_pool_pre_ping():
    """AC-INF-1: engine must validate connections on checkout."""
    from app.database import engine

    assert isinstance(engine, AsyncEngine)
    sync_engine = engine.sync_engine
    pool = sync_engine.pool
    # pool_pre_ping lives on the underlying engine's "engine" attribute
    assert pool._pre_ping is True, (
        "engine.pool_pre_ping is not set to True. Without it, asyncpg "
        "connections go stale on backend container restart and throw "
        "'another operation is in progress' on the first requests."
    )
