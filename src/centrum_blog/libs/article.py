import datetime as dt
import json

import math
from pathlib import Path

from sqlalchemy import func, desc, asc

from centrum_blog.constants import static_content_path
from centrum_blog.libs.db import get_db_session
from centrum_blog.libs.models import BlogIndex


def is_article_exist_on_fs(article_id: str) -> bool:
    article_path = Path(static_content_path) / "posts" / article_id
    article_folder_exist = article_path.exists() and article_path.is_dir()
    metadata_file_exist = (article_path / "metadata.json").exists()
    content_file_exist = (article_path / "content.md").exists()
    return article_folder_exist and metadata_file_exist and content_file_exist


def get_total_pages(per_page: int) -> int:
    with get_db_session() as session:
        total_articles = session.query(func.count(BlogIndex.id)).scalar()

    return math.ceil(total_articles / per_page) if total_articles > 0 else 1


def get_articles_list(page: int, per_page: int) -> list[dict]:
    articles = []

    with get_db_session() as session:
        rows = (
            session.query(BlogIndex.path)
            .order_by(desc(BlogIndex.updated))
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        for row in rows:
            articles.append(get_article_metadata(row[0]))

    return articles


def get_article_metadata(article_id: str) -> dict[str, str | dt.date | Path]:
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

    with get_db_session() as session:
        current = session.query(BlogIndex.updated).filter(BlogIndex.path == article_id).first()

        if current:
            timestamp = current[0]

            prev_row = (
                session.query(BlogIndex.path)
                .filter(BlogIndex.updated < timestamp)
                .order_by(desc(BlogIndex.updated))
                .first()
            )
            prev_article = get_article_metadata(prev_row[0]) if prev_row is not None else None

            next_row = (
                session.query(BlogIndex.path)
                .filter(BlogIndex.updated > timestamp)
                .order_by(asc(BlogIndex.updated))
                .first()
            )
            next_article = get_article_metadata(next_row[0]) if next_row is not None else None

    return (prev_article, next_article)
