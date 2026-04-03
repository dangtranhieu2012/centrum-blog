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


engine = create_engine(_get_sqlalchemy_url(), echo=False, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_db_session():
    """Yield a SQLAlchemy session for database operations."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
