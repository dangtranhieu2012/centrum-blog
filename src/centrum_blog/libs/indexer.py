import git
import json
import os
import subprocess

from centrum_blog.libs.db import get_db_connection

from datetime import datetime
from pathlib import Path

import centrum_blog.libs.git as git_helper
from centrum_blog.libs.settings import settings


def reindex(static_content_path: str):
    try:
        repo = git.Repo(static_content_path)
        old_head = repo.head.commit
        repo.remote().pull()
    except git.exc.NoSuchPathError:
        repo = git.Repo.clone_from(
            git_helper.get_authenticated_url(settings.git_repo_url),
            static_content_path,
        )
        old_head = None

    p = Path(__file__).parent.parent / "git-restore-mtime"
    subprocess.run(["python3", p], cwd=static_content_path)

    if old_head is not None:
        if old_head != repo.head.commit:
            diff_index = old_head.diff(repo.head.commit)
            index_changes(Path(static_content_path) / "posts", diff_index)
    else:
        index_all(Path(static_content_path) / "posts")


def get_metadata(entry_path: str) -> tuple[int, str]:
    entry_path = Path(entry_path)
    mtime = entry_path.stat().st_mtime

    metadata_path = entry_path / "metadata.json"
    tags = []
    with metadata_path.open() as f:
        tags = json.load(f)["tags"]
    tags = "," + ",".join(tags) + "," if len(tags) > 0 else ""

    return (mtime, tags)


def index_changes(posts_path: Path, diff_index: list):
    to_delete = set()
    to_add = set()
    to_update = set()

    content_path = posts_path.parent

    for item in diff_index:
        p = content_path / item.a_path
        post_path = p.parent.name

        # Make sure the changed file is actually in the posts path
        if p.parent != (posts_path / post_path):
            continue

        if item.change_type == "D":
            to_delete.add(post_path)
        elif item.change_type == "A":
            to_add.add(post_path)
        elif item.change_type == "M":
            to_update.add(post_path)

    with get_db_connection() as connection:
        cursor = connection.cursor()

        for item in to_delete:
            sql = "DELETE FROM blog_index WHERE path=:path"
            cursor.execute(sql, path=item)

        for item in to_add:
            (mtime, tags) = get_metadata(posts_path / item)
            sql = "INSERT INTO blog_index (path, updated, tags) VALUES (:path, :updated, :tags)"
            cursor.execute(sql, path=item, updated=datetime.fromtimestamp(mtime), tags=tags)

        for item in to_update:
            (mtime, tags) = get_metadata(posts_path / item)
            sql = "UPDATE blog_index SET updated=:updated, tags=:tags WHERE path=:path"
            cursor.execute(sql, path=item, updated=datetime.fromtimestamp(mtime), tags=tags)

        connection.commit()


def index_all(posts_path: Path):
    with get_db_connection() as connection:
        cursor = connection.cursor()

        cursor.execute("TRUNCATE TABLE blog_index")

        with os.scandir(posts_path) as it:
            for entry in it:
                if entry.is_dir():
                    (mtime, tags) = get_metadata(entry)
                    sql = "INSERT INTO blog_index (path, updated, tags) VALUES (:path, :updated, :tags)"
                    cursor.execute(sql, path=entry.name, updated=datetime.fromtimestamp(mtime), tags=tags)

        connection.commit()
