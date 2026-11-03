from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings


def _clean_database_url(url: str) -> str:
    if "postgres" not in url:
        return url
    url = url.replace("?pgbouncer=true", "").replace("&pgbouncer=true", "")
    if "sslmode=" not in url:
        separator = "&" if "?" in url else "?"
        url = url + separator + "sslmode=require"
    return url


database_url = _clean_database_url(settings.database_url)

engine = create_engine(
    database_url,
    connect_args={"check_same_thread": False} if "sqlite" in database_url else {},
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    if "sqlite" in database_url:
        from app.db import models  # noqa: F401

        Base.metadata.create_all(bind=engine)
    else:
        from app.db.ventrix_models import VentrixBase  # noqa: F401

        VentrixBase.metadata.create_all(bind=engine)
