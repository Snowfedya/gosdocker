from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from .config import settings

Base = declarative_base()

# AC-INF-1: pool_pre_ping=True prevents asyncpg "another operation is
# in progress" errors that appear after `docker compose up -d backend`
# recreates the backend container while the db connection pool keeps
# stale handles. SQLAlchemy emits a cheap "SELECT 1" on each checkout
# and replaces dead connections transparently.
# pool_recycle=1800 forces a refresh every 30 min even if pre_ping
# somehow misses a half-dead connection.
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_recycle=1800,
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    # AC-INF-2: pre_ping=True catches dead conns on *checkout*, but a conn
    # already checked out can die mid-request (db Recreate). The
    # request-level retry lives in app.middleware.db_retry (StaleConnRetry)
    # — here we just hand out a session and let exceptions propagate.
    session = async_session()
    try:
        yield session
    finally:
        try:
            await session.close()
        except Exception:
            pass
