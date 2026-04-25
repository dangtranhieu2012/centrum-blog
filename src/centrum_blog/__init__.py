import datetime as dt
import hmac
import importlib
import json
import logging
import os
import sys
import mistune
import re

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from centrum_blog.libs import article, credential, indexer
from centrum_blog.libs.db import initialize_database
from centrum_blog.libs.settings import settings

from flask import Flask, abort, render_template, request, send_from_directory
from flask.json import jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


log_level = getattr(logging, settings.log_level.upper())
logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)

app = Flask(__name__)

limiter = Limiter(get_remote_address, app=app, storage_uri="memory://")

if "pytest" not in sys.modules and os.getenv("PYTEST_CURRENT_TEST") is None:
    initialize_database()
    indexer.reindex(settings.static_content_path)

renderer = importlib.import_module(f"centrum_blog.templates.{settings.template}.markdown_renderer").MarkdownRenderer

index_executor = ThreadPoolExecutor(max_workers=10)


def sanitize_name(name: str):
    return re.sub(r"[^a-zA-Z0-9\-_]", "-", name)


def get_per_page() -> int:
    per_page = request.cookies.get("per_page", "10")
    if per_page not in ["10", "20"]:
        per_page = "10"
    return int(per_page)


def generate_pagination(current_page: int, total_pages: int) -> list[int | str]:
    pagination = []

    max_page = min(current_page + 2, total_pages)
    min_page = max(current_page - 2, 1)

    if min_page > 1:
        pagination.append("ellipsis")

    for i in range(min_page, max_page + 1):
        pagination.append(i)

    if max_page < total_pages:
        pagination.append("ellipsis")

    return pagination


@app.route("/")
@app.route("/<int:page>")
def index(page: int = 1):
    per_page = get_per_page()

    total_pages = article.get_total_pages(int(per_page))
    if page == 0:
        page = total_pages
    elif page > total_pages:
        abort(404)

    articles = article.get_articles_list(page=page, per_page=int(per_page))

    return render_template(
        f"{settings.template}/feed.html",
        now=dt.date.today(),
        per_page=per_page,
        articles=articles,
        current_page=page,
        pages=generate_pagination(page, total_pages),
    )


@app.route("/read/<article_id>")
def read(article_id: str):
    article_id = sanitize_name(article_id)

    try:
        metadata = article.get_article_metadata(article_id)

        author_metadata_file = Path(settings.static_content_path) / f"authors/{metadata['author']}/metadata.json"
        author_metadata = {}
        with author_metadata_file.open() as f:
            author_metadata = json.load(f)

        body = ""
        markdown = mistune.create_markdown(renderer=renderer(article_id))
        content_file = Path(str(metadata["article_path"])) / "content.md"
        with content_file.open() as f:
            body = markdown(f.read())

        adjacent_articles = article.get_adjacent_articles(article_id)

        return render_template(
            f"{settings.template}/post.html",
            now=dt.date.today(),
            published=metadata["published"],
            author=author_metadata["name"],
            author_avatar=author_metadata["avatar"],
            title=metadata["title"],
            tags=metadata["tags"],
            body=body,
            previous_article=adjacent_articles[0],
            next_article=adjacent_articles[1],
        )
    except Exception as e:
        logger.error(e)
        abort(404)


@app.route("/about")
def about():
    about_content = ""
    about_file = Path(settings.static_content_path) / "about.md"

    if about_file.exists():
        markdown = mistune.create_markdown(renderer=renderer(escape=False))
        with about_file.open() as f:
            about_content = markdown(f.read())
    else:
        # Fallback content if file doesn't exist
        about_content = "<p>About page content not found. Please add an about.md file to your content repository.</p>"

    return render_template(
        f"{settings.template}/about.html",
        now=dt.date.today(),
        about_content=about_content,
    )


@app.route("/tag/<tag>")
@app.route("/tag/<tag>/<int:page>")
def tag(tag: str, page: int = 1):
    per_page = get_per_page()
    total_pages = article.get_total_pages(per_page, tag=tag)

    if page == 0:
        page = total_pages
    elif page > total_pages:
        abort(404)

    articles = article.get_articles_list(page=page, per_page=per_page, tag=tag)

    return render_template(
        f"{settings.template}/feed.html",
        now=dt.date.today(),
        tag=tag,
        per_page=per_page,
        articles=articles,
        current_page=page,
        pages=generate_pagination(page, total_pages),
    )


@app.route("/content/<path:filename>")
def static_content(filename: Path):
    return send_from_directory("../../" / Path(settings.static_content_path), filename)


@app.post("/reindex")
@limiter.limit("5 per minute")
def reindex():
    header_signature = request.headers.get("X-Hub-Signature-256")
    if not header_signature:
        return abort(401)

    sha_name, signature = header_signature.split("=")
    if sha_name != "sha256":
        return abort(503)

    webhook_secret = credential.get_secret(settings.webhook_secret, settings.webhook_secret_ocid)

    local_signature = hmac.new(webhook_secret.encode(), msg=request.get_data(), digestmod="sha256")
    if hmac.compare_digest(local_signature.hexdigest(), signature):
        index_executor.submit(indexer.reindex, settings.static_content_path)
        return jsonify({"status": "OK"})
    else:
        return abort(401)
