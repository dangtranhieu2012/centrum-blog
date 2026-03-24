import shutil

from centrum_blog import static_content_path
from centrum_blog.libs import indexer


shutil.rmtree(static_content_path)
indexer.reindex(static_content_path)
