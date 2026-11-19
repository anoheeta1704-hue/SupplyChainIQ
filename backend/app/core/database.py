# ============================================
# SupplyChainIQ — Database Engine & Sessions
# ============================================
import os
import structlog
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy import create_engine, text
from app.core.config import settings

logger = structlog.get_logger()

# Determine database URL: check if postgres is reachable or fallback to sqlite
_db_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "supplychainiq.db"))
_sqlite_async_url = f"sqlite+aiosqlite:///{_db_file}"
_sqlite_sync_url = f"sqlite:///{_db_file}"

active_db_url = settings.DATABASE_URL
active_sync_url = settings.DATABASE_URL_SYNC

# If we are in local development and not running inside docker, default to reliable sqlite
# unless explicit postgres connection succeeds
if "localhost" in settings.DATABASE_URL or "postgres" in settings.DATABASE_URL:
    try:
        import socket
        s = socket.create_connection(("localhost", 5432), timeout=0.5)
        s.close()
    except Exception:
        # PostgreSQL is not running on localhost:5432, use SQLite fallback
        active_db_url = _sqlite_async_url
        active_sync_url = _sqlite_sync_url
        logger.info("postgres_offline_using_sqlite_fallback", db_path=_db_file)

# Async engine for FastAPI
engine_kwargs = {"echo": False}
if "sqlite" in active_db_url:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs.update({
        "pool_size": 20,
        "max_overflow": 10,
        "pool_pre_ping": True,
    })

async_engine = create_async_engine(active_db_url, **engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Sync engine for scripts
sync_kwargs = {"echo": False}
if "sqlite" in active_sync_url:
    sync_kwargs["connect_args"] = {"check_same_thread": False}
else:
    sync_kwargs.update({
        "pool_size": 5,
        "pool_pre_ping": True,
    })

sync_engine = create_engine(active_sync_url, **sync_kwargs)
SyncSessionLocal = sessionmaker(bind=sync_engine)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


async def get_db() -> AsyncSession:
    """FastAPI dependency that yields an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Create all tables."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("database_tables_verified", db_url=active_db_url)

