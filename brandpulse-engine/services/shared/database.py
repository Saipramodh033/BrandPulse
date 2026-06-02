"""
Database Configuration
=====================
SQLAlchemy engine and session management
"""

import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Get database URL from environment
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://brandpulse_user:your_secure_password_here@postgres:5432/brandpulse'
)

# Create engine
engine = create_engine(
    DATABASE_URL,
    pool_size=5,          # D1 Fix: Use connection pool instead of NullPool
    max_overflow=10,      # Allow up to 15 total connections under load
    pool_timeout=30,      # Wait up to 30s for a connection from pool
    pool_recycle=1800,    # Recycle connections every 30min to avoid stale connections
    echo=False,  # Set to True for SQL query logging
    future=True
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class for models
Base = declarative_base()


def get_db():
    """
    Dependency for getting database session.
    Used in FastAPI/Streamlit endpoints.
    
    Usage:
        session = next(get_db())
        try:
            # Use session
        finally:
            session.close()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session():
    """
    Context manager for getting a database session.
    Used in Celery worker tasks.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_health(engine) -> bool:
    """
    Check if database connection is healthy.
    
    Args:
        engine: SQLAlchemy engine instance
        
    Returns:
        True if database is accessible, False otherwise
    """
    try:
        # Try to execute a simple query
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            result.fetchone()
        
        logger.info("✅ Database health check passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database health check failed: {e}")
        return False


def init_database():
    """
    Initialize database tables.
    Creates all tables defined in models.py if they don't exist.
    
    Note: For production, use Alembic migrations instead.
    """
    from services.shared.models import Base
    
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables initialized")
        
        # Self-healing migration for missing region column in company_profiles
        try:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE company_profiles ADD COLUMN IF NOT EXISTS region VARCHAR(100) DEFAULT 'India';"))
                conn.commit()
            logger.info("✅ Database schema migrations applied (added region column to company_profiles if missing)")
        except Exception as migration_error:
            logger.warning(f"⚠️ Self-healing schema migration warning: {migration_error}")
            
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        raise