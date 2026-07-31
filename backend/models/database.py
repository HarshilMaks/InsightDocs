"""Database configuration and session management."""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from backend.config import settings

# Production database connection pooling configuration
engine = create_engine(
    settings.database_url,
    pool_size=20,          # Maintain up to 20 persistent connections
    max_overflow=10,       # Allow up to 10 additional burst connections
    pool_timeout=30,       # Wait up to 30 seconds for a connection
    pool_pre_ping=True,    # Test connections before using them
    pool_recycle=300,      # Recycle connections after 5 minutes
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
