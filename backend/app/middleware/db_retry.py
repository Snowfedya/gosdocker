"""
AC-INF-2: HTTP middleware that retries the request once if it fails
with a stale-db-connection error (asyncpg InterfaceError /
PostgresConnectionError / ConnectionResetError). The first attempt
catches the kill; the second attempt re-runs the handler with a
fresh pool checkout (pre_ping will pass).
"""
from __future__ import annotations

import logging
from typing import Callable

import asyncpg.exceptions as _aexc
from fastapi import Request, Response
from sqlalchemy.exc import InterfaceError as SAInterfaceError
from starlette.middleware.base import BaseHTTPMiddleware

log = logging.getLogger("gosdocker.db_retry")

# Errors that indicate a stale connection (db Recreate / SIGTERM) and
# are safe to retry transparently.
STALE_CONN_ERRORS: tuple[type[BaseException], ...] = (
    SAInterfaceError,
    _aexc.InterfaceError,
    _aexc.PostgresConnectionError,
    _aexc.CannotConnectNowError,
    ConnectionResetError,
)


class StaleConnectionRetryMiddleware(BaseHTTPMiddleware):
    """Retries GET requests once on stale-db-connection errors.

    Only safe for idempotent verbs (GET/HEAD). POST/PUT/PATCH are NOT
    retried — their handlers may have side effects (DB writes,
    external calls) we can't safely replay.
    """

    SAFE_METHODS = frozenset({"GET", "HEAD"})

    def __init__(self, app, max_retries: int = 1) -> None:
        super().__init__(app)
        self.max_retries = max_retries

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.method not in self.SAFE_METHODS:
            return await call_next(request)

        last_exc: BaseException
        for attempt in range(self.max_retries + 1):
            try:
                return await call_next(request)
            except STALE_CONN_ERRORS as e:
                last_exc = e
                if attempt < self.max_retries:
                    log.warning(
                        "stale db conn on %s %s (attempt %d/%d): %s — retrying",
                        request.method,
                        request.url.path,
                        attempt + 1,
                        self.max_retries + 1,
                        type(e).__name__,
                    )
                    continue
                raise
        # Defensive — loop body always either returns or raises.
        raise RuntimeError("db_retry: unreachable")  # pragma: no cover
