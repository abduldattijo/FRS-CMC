"""
Dependency injection for API routes
"""

from typing import Generator
from sqlalchemy.orm import Session
from ..models.enhanced_database import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """
    Get database session for dependency injection

    Yields:
        Database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
