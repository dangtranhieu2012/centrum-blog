from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from centrum_blog.libs import credential
from centrum_blog.libs.settings import settings


# Build SQLAlchemy connection URL
def _get_sqlalchemy_url():
    db_secret = credential.get_secret(settings.db_secret, settings.db_secret_ocid)
    url = f"{settings.db_dialect_driver}://{settings.db_user}:{db_secret}@{settings.db_connection_string}"
    return url


def get_engine():
    """Get or create the SQLAlchemy engine."""
    if not hasattr(get_engine, '_engine'):
        get_engine._engine = create_engine(_get_sqlalchemy_url(), echo=False, pool_pre_ping=True)
    return get_engine._engine


def get_sessionmaker():
    """Get or create the sessionmaker."""
    if not hasattr(get_sessionmaker, '_sessionmaker'):
        engine = get_engine()
        get_sessionmaker._sessionmaker = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return get_sessionmaker._sessionmaker


@contextmanager
def get_db_session():
    """Yield a SQLAlchemy session for database operations."""
    SessionLocal = get_sessionmaker()
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
