"""Database configuration and session management."""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from backend.config import settings

# Connection pool sizing is environment-driven (DB_POOL_SIZE, DB_MAX_OVERFLOW,
# DB_POOL_TIMEOUT, DB_POOL_RECYCLE) rather than hardcoded, since the right
# values depend on the deployment's Postgres plan and number of API/worker
# replicas. Defaults are conservative for small/local deployments.
engine = create_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout,
    pool_pre_ping=True,    # Test connections before using them
    pool_recycle=settings.db_pool_recycle,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
