import datetime as dt
import hmac
import json
import logging
import mistune
import re
import shutil

from centrum_blog.libs import indexer

from pathlib import Path
from centrum_blog.libs.oci_helper.vault import get_secret
from centrum_blog.libs.settings import settings
from centrum_blog.markdown_renderer import MarkdownRenderer

from flask import Flask, abort, render_template, request


app = Flask(__name__)
static_content_path = "src/centrum_blog/static/content"

log_level = getattr(logging, settings.log_level.upper())
logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)


def sanitize_name(name: str):
    return re.sub(r"[^a-zA-Z0-9\-_]", "-", name)


@app.route("/read/<article_id>")
def read(article_id: str):
    article_id = sanitize_name(article_id)

    try:
        static_path = Path(static_content_path)

        article_path = static_path / "posts" / article_id

        metadata_file = article_path / "metadata.json"
        metadata = {}
        with metadata_file.open() as f:
            metadata = json.load(f)

        published = dt.date.fromtimestamp(metadata_file.stat().st_birthtime)

        author = metadata["author"]
        author_metadata_file = static_path / f"authors/{metadata['author']}/metadata.json"
        author_metadata = {}
        with author_metadata_file.open() as f:
            author_metadata = json.load(f)

        body = ""
        markdown = mistune.create_markdown(renderer=MarkdownRenderer(article_id))
        content_file = article_path / "content.md"
        with content_file.open() as f:
            body = markdown(f.read())

        return render_template(
            "typo/post.html",
            now=dt.date.today(),
            published=published,
            author=author_metadata["name"],
            author_avatar=author_metadata["avatar"],
            title=metadata["title"],
            tags=metadata["tags"],
            body=body,
        )
    except Exception as e:
        logger.error(e)
        abort(404)


@app.post("/reindex")
def reindex():
    webhook_secret = get_secret(settings.webhook_secret_ocid)

    header_signature = request.headers.get('X-Hub-Signature-256')

    if not header_signature:
        return abort(401)

    sha_name, signature = header_signature.split('=')
    if sha_name != 'sha256':
        return abort(503)

    local_signature = hmac.new(webhook_secret.encode(), msg=request.get_data(), digestmod='sha256')
    if hmac.compare_digest(local_signature.hexdigest(), signature):
        indexer.reindex(static_content_path)
        return "OK"
    else:
        return abort(401)
