import logging
from typing import Optional
from urllib.parse import quote, urlparse

from centrum_blog.libs import settings
from centrum_blog.libs.oci_helper import vault


logger = logging.getLogger(__name__)


def get_secret(secret: Optional[str] = None, secret_ocid: Optional[str] = None) -> str:
    s = secret

    if secret_ocid is not None:
        s = vault.get_secret(secret_ocid)
    
    return s if s is not None else ""


def get_authenticated_git_url(url):
    parsed = urlparse(url)

    # Check if the protocol is HTTP or HTTPS
    if parsed.scheme in ['http', 'https']:
        username = get_secret(settings.git_username, settings.git_username_secret_ocid)
        password = get_secret(settings.git_password, settings.git_password_secret_ocid)

        if not password:
            logger.warning("HTTP(S) detected but credentials not found in settings.")
            return url

        # URL-encode credentials to handle special characters
        safe_user = ""
        if username:
            safe_user = quote(username) + ":"
        safe_pass = quote(password)

        # Reconstruct URL with credentials: https://user:pass@host/path
        auth_url = parsed._replace(
            netloc=f"{safe_user}{safe_pass}@{parsed.netloc}"
        ).geturl()

        return auth_url

    # If it's SSH (e.g., git@github.com:...) or anything else, return as-is
    return url
