import git
import json
import os
import subprocess
import threading

from sqlalchemy import func
from git.exc import NoSuchPathError

from centrum_blog.libs import credential
from centrum_blog.libs.article import is_article_exist_on_fs
from centrum_blog.libs.db import get_db_session
from centrum_blog.libs.models import BlogIndex
from centrum_blog.libs.settings import settings

from datetime import datetime
from pathlib import Path

reindexLock = threading.Lock()


def reindex(static_content_path: str):
    """
    Reindex the blog posts by pulling the latest changes from the git repository and updating the database index accordingly.

    Note that this only prevents multiple reindexing threads from running at the same time, it will not work if we
    migrate to a different solution to serve the application that spawn multiple processes (e.g. gunicorn with multiple
    workers). In that case we should consider using a distributed lock solution like Redis or database lock or better
    yet, use a file lock through fnctl.LOCK_EX to avoid extra external dependencies.
    """

    with reindexLock:
        try:
            repo = git.Repo(static_content_path)
            old_head = repo.head.commit
            repo.remote().pull()
        except NoSuchPathError:
            repo = git.Repo.clone_from(
                credential.get_authenticated_git_url(settings.git_repo_url),
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


def get_metadata(entry_path: Path) -> tuple[float, str]:
    mtime = entry_path.stat().st_mtime

    metadata_path = entry_path / "metadata.json"
    tags = []
    with metadata_path.open() as f:
        tags = json.load(f).get("tags", [])
    tags = "," + ",".join(tags) + "," if len(tags) > 0 else ""

    return (mtime, tags)


def index_changes(posts_path: Path, diff_index: list):
    to_delete = set()
    to_add_or_update = set()

    content_path = posts_path.parent

    for item in diff_index:
        p = content_path / item.a_path
        post_path = p.parent.name

        # Make sure the changed file is actually in the posts path
        if p.parent != (posts_path / post_path):
            continue

        if item.change_type == "D":
            to_delete.add(post_path)
        else:
            to_add_or_update.add(post_path)

    with get_db_session() as session:
        for item in to_delete:
            if is_article_exist_on_fs(item):
                continue
            session.query(BlogIndex).filter(BlogIndex.path == item).delete()

        for item in to_add_or_update:
            if is_article_exist_on_fs(item):
                (mtime, tags) = get_metadata(posts_path / item)

                exist = session.query(func.count(BlogIndex.id)).filter(BlogIndex.path == item).scalar()
                if exist > 0:
                    session.query(BlogIndex).filter(BlogIndex.path == item).update(
                        {BlogIndex.updated: datetime.fromtimestamp(mtime), BlogIndex.tags: tags}
                    )
                else:
                    blog_entry = BlogIndex(path=item, updated=datetime.fromtimestamp(mtime), tags=tags)
                    session.add(blog_entry)


def index_all(posts_path: Path):
    with get_db_session() as session:
        session.query(BlogIndex).delete()

        with os.scandir(posts_path) as it:
            for entry in it:
                if entry.is_dir():
                    (mtime, tags) = get_metadata(posts_path / entry.name)
                    blog_entry = BlogIndex(path=entry.name, updated=datetime.fromtimestamp(mtime), tags=tags)
                    session.add(blog_entry)
