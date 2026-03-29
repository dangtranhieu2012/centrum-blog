from contextlib import contextmanager

import oracledb

from centrum_blog.libs.oci_helper.vault import get_secret
from centrum_blog.libs.settings import settings


@contextmanager
def get_db_connection():
    """Yield an Oracle DB connection, using the vault-secret password."""
    db_secret = get_secret(settings.db_secret_ocid)
    with oracledb.connect(
        user=settings.db_user, password=db_secret, dsn=settings.db_connection_string
    ) as connection:
        yield connection
