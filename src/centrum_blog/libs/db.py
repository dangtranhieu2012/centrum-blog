from contextlib import contextmanager

import oracledb

from centrum_blog.libs import util
from centrum_blog.libs.settings import settings


@contextmanager
def get_db_connection():
    db_secret = util.get_secret(settings.db_secret, settings.db_secret_ocid)
    with oracledb.connect(
        user=settings.db_user, password=db_secret, dsn=settings.db_connection_string
    ) as connection:
        yield connection
