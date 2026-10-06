"""
SQLite database setup using SQLAlchemy.

`get_db` is a FastAPI dependency that opens a session per request and always
closes it afterwards.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

import config

engine = create_engine(
    f"sqlite:///{config.DATABASE_PATH}",
    # SQLite objects may be used from different threads by FastAPI.
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables if they do not exist yet."""
    import models  # noqa: F401  (importing registers the tables on Base)

    Base.metadata.create_all(bind=engine)
