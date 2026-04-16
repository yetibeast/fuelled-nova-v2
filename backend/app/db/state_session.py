from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import STATE_DATABASE_URL

_engine = None
_session_factory = None


def _ensure_session_factory():
    global _engine, _session_factory
    if _session_factory is not None:
        return _session_factory
    if not STATE_DATABASE_URL:
        raise RuntimeError(
            "STATE_DATABASE_URL environment variable is required for acquisition workflow."
        )
    _engine = create_async_engine(STATE_DATABASE_URL, pool_size=5)
    _session_factory = sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
    return _session_factory


@asynccontextmanager
async def get_state_session():
    session_factory = _ensure_session_factory()
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
