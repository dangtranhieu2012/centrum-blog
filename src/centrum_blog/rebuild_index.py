import shutil

from pathlib import Path

from centrum_blog import static_content_path
from centrum_blog.libs import indexer

p = Path(static_content_path)
if p.exists():
    shutil.rmtree(static_content_path)

indexer.reindex(static_content_path)
