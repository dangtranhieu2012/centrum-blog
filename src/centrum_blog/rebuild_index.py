import shutil

from pathlib import Path

from centrum_blog.libs import indexer
from centrum_blog.libs.settings import settings

p = Path(settings.static_content_path)
if p.exists():
    shutil.rmtree(settings.static_content_path)

indexer.reindex(settings.static_content_path)
