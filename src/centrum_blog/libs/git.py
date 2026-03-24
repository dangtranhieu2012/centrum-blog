import logging
import os

from urllib.parse import urlparse, quote

from centrum_blog.libs.settings import settings


logger = logging.getLogger(__name__)


def get_authenticated_url(url):
    parsed = urlparse(url)
    
    # Check if the protocol is HTTP or HTTPS
    if parsed.scheme in ['http', 'https']:
        username = settings.git_username
        password = settings.git_password
        
        if not username or not password:
            logger.warning("HTTP(S) detected but credentials not found in settings.")
            return url
            
        # URL-encode credentials to handle special characters
        safe_user = quote(username)
        safe_pass = quote(password)
        
        # Reconstruct URL with credentials: https://user:pass@host/path
        auth_url = parsed._replace(
            netloc=f"{safe_user}:{safe_pass}@{parsed.netloc}"
        ).geturl()

        return auth_url
    
    # If it's SSH (e.g., git@github.com:...) or anything else, return as-is
    return url
