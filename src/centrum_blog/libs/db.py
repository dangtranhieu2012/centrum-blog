from contextlib import contextmanager
from typing import Optional

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from centrum_blog.libs import credential
from centrum_blog.libs.settings import settings

_engine: Optional[Engine] = None
_sessionmaker: Optional[sessionmaker[Session]] = None


# Build SQLAlchemy connection URL
def _get_sqlalchemy_url():
    db_secret = credential.get_secret(settings.db_secret, settings.db_secret_ocid)
    return credential.construct_authenticated_url(settings.db_connection_string, settings.db_user, db_secret)


def get_engine() -> Engine:
    """Get or create the SQLAlchemy engine."""
    global _engine
    if _engine is None:
        _engine = create_engine(_get_sqlalchemy_url(), echo=False, pool_pre_ping=True)
    return _engine


def get_sessionmaker() -> sessionmaker[Session]:
    """Get or create the sessionmaker."""
    global _sessionmaker
    if _sessionmaker is None:
        engine = get_engine()
        _sessionmaker = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _sessionmaker


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
