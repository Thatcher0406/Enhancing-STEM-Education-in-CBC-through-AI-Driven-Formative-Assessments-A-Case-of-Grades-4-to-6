# backend/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# -------------------------------------------------------------
# DATABASE CONFIGURATION
# -------------------------------------------------------------
# You can update this to use PostgreSQL/MySQL in production:
# Example:
# SQLALCHEMY_DATABASE_URL = "postgresql://user:password@localhost/dbname"
# For now, we’ll keep SQLite for local development.
SQLALCHEMY_DATABASE_URL = "sqlite:///./app.db"

# -------------------------------------------------------------
# ENGINE & SESSION
# -------------------------------------------------------------
# `check_same_thread=False` is required only for SQLite
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# -------------------------------------------------------------
# DATABASE DEPENDENCY
# -------------------------------------------------------------
def get_db():
    """
    Provides a SQLAlchemy database session to FastAPI routes.
    Automatically closes the session after the request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
