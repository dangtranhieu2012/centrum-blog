import logging
from typing import Optional
from urllib.parse import quote, urlparse

from centrum_blog.libs import settings
from centrum_blog.libs.oci_helper import vault


logger = logging.getLogger(__name__)


def get_secret(secret: Optional[str] = None, secret_ocid: Optional[str] = None) -> str:
    if secret is not None:
        return secret
    elif secret_ocid is not None:
        return vault.get_secret(secret_ocid)
    else:
        return ""


def get_authenticated_git_url(url: str) -> str:
    parsed = urlparse(url)

    # Check if the protocol is HTTP or HTTPS
    if parsed.scheme in ['http', 'https']:
        username = get_secret(settings.git_username, settings.git_username_secret_ocid)
        password = get_secret(settings.git_password, settings.git_password_secret_ocid)

        # URL-encode credentials to handle special characters
        safe_user = quote(username) if username else ""
        safe_pass = quote(password) if password else ""
        if safe_user or safe_pass:
            credential = ":".join(filter(None, [safe_user, safe_pass])) + "@"
        else:
            credential = ""

        # Reconstruct URL with credentials: https://user:pass@host/path
        auth_url = parsed._replace(
            netloc=f"{credential}{parsed.netloc}"
        ).geturl()

        return auth_url

    # If it's SSH (e.g., git@github.com:...) or anything else, return as-is
    return url
