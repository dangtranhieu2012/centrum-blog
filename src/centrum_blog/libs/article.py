import datetime as dt
import json

import math
from pathlib import Path

from centrum_blog.constants import static_content_path
from centrum_blog.libs.db import get_db_connection


def get_total_pages(per_page: int) -> int:
    total_articles = 0

    with get_db_connection() as connection:
        cursor = connection.cursor()
        sql = "SELECT COUNT(*) FROM blog_index"
        cursor.execute(sql)
        row = cursor.fetchone()
        total_articles = row[0]

    return math.ceil(total_articles / per_page) if total_articles > 0 else 1


def get_articles_list(page: int, per_page: int) -> list[dict]:
    articles = []

    with get_db_connection() as connection:
        cursor = connection.cursor()

        sql = "SELECT path, updated FROM blog_index ORDER BY updated DESC OFFSET :offset ROWS FETCH NEXT :per_page ROWS ONLY"
        cursor.execute(sql, offset=(page - 1) * per_page, per_page=per_page)

        rows = cursor.fetchall()
        for row in rows:
            articles.append(get_article_metadata(row[0]))

    return articles


def get_article_metadata(article_id: str) -> dict | None:
    static_path = Path(static_content_path)
    article_path = static_path / "posts" / article_id

    metadata_file = article_path / "metadata.json"
    metadata = {}
    with metadata_file.open() as f:
        metadata = json.load(f)

    metadata["published"] = dt.date.fromtimestamp((article_path).stat().st_mtime)
    metadata["article_path"] = article_path
    metadata["article_id"] = article_id

    return metadata


def get_adjacent_articles(article_id: str) -> tuple[dict | None, dict | None]:
    prev_article = None
    next_article = None

    with get_db_connection() as connection:
        cursor = connection.cursor()

        sql = "SELECT updated FROM blog_index WHERE path = :article_id"
        cursor.execute(sql, article_id=article_id)
        row = cursor.fetchone()
        timestamp = row[0]

        sql = "SELECT path FROM blog_index WHERE updated < :timestamp ORDER BY updated DESC FETCH FIRST 1 ROWS ONLY"
        cursor.execute(sql, timestamp=timestamp)
        prev_row = cursor.fetchone()
        prev_article = get_article_metadata(prev_row[0]) if prev_row is not None else None

        sql = "SELECT path FROM blog_index WHERE updated > :timestamp ORDER BY updated ASC FETCH FIRST 1 ROWS ONLY"
        cursor.execute(sql, timestamp=timestamp)
        next_row = cursor.fetchone()
        next_article = get_article_metadata(next_row[0]) if next_row is not None else None

    return (prev_article, next_article)
