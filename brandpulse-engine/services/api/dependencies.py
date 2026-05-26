"""
FastAPI Dependencies
====================
Shared dependency injections for all routes.
"""

from services.shared.database import SessionLocal


def get_db():
    """Yield a SQLAlchemy session, always closing after request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
