from typing import Optional
from urllib.parse import quote, urlparse

from centrum_blog.libs.settings import settings
from centrum_blog.libs.oci_helper import vault


def get_secret(secret: Optional[str] = None, secret_ocid: Optional[str] = None) -> str:
    if secret is not None:
        return secret
    elif secret_ocid is not None:
        return vault.get_secret(secret_ocid) or ""
    else:
        return ""


def construct_authenticated_url(url: str, username: Optional[str] = None, password: Optional[str] = None) -> str:
    """
    Construct a URL with optional credentials.

    Handles HTTP/HTTPS URLs (e.g., Git URLs) as well as SQLAlchemy database URLs
    (e.g., oracle+oracledb://, postgresql://, mysql+pymysql://, etc.).

    Args:
        url: The URL to construct (e.g., 'https://github.com/user/repo.git' or
             'oracle+oracledb://host:port/service')
        username: Optional username credential.
        password: Optional password credential.

    Returns:
        The URL with embedded credentials if provided, otherwise the original URL.

    Examples:
        >>> construct_authenticated_url('https://github.com/user/repo.git', 'user', 'pass')
        'https://user:pass@github.com/user/repo.git'

        >>> construct_authenticated_url('oracle+oracledb://host:1521/db', 'admin', 'secret')
        'oracle+oracledb://admin:secret@host:1521/db'
    """
    parsed = urlparse(url)

    # SQLite URLs rely on exact slash formatting (e.g., sqlite:///db.sqlite3).
    # Do not inject credentials or rebuild these URLs.
    if parsed.scheme == "sqlite":
        return url

    # URL-encode credentials to handle special characters
    # Use safe='' to encode all special characters including /:?#
    safe_user = quote(username, safe="") if username else ""
    safe_pass = quote(password, safe="") if password else ""

    if safe_user or safe_pass:
        credential = ":".join(filter(None, [safe_user, safe_pass])) + "@"
    else:
        credential = ""

    # Reconstruct URL with credentials
    # First remove existing credentials from netloc if present
    netloc = parsed.netloc
    if "@" in netloc:
        netloc = netloc.split("@", 1)[1]

    # Works for http, https, and SQLAlchemy database URLs
    auth_url = parsed._replace(netloc=f"{credential}{netloc}").geturl()

    return auth_url


def get_authenticated_git_url(url: str) -> str:
    """
    Construct a Git URL with credentials from settings.

    This function retrieves credentials from the application settings (either plain text or from OCI vault) and injects them into the URL.

    Note: This function only applies credentials to HTTP/HTTPS schemes. For other schemes or more flexible credential handling, use construct_authenticated_url() directly.

    Args:
        url: The Git repository URL.

    Returns:
        The URL with embedded credentials if HTTP/HTTPS, otherwise unchanged.
    """
    parsed = urlparse(url)

    # Check if the protocol is HTTP or HTTPS
    if parsed.scheme in ["http", "https"]:
        username = get_secret(settings.git_username, settings.git_username_secret_ocid)
        password = get_secret(settings.git_password, settings.git_password_secret_ocid)
        return construct_authenticated_url(url, username, password)

    # If it's SSH (e.g., git@github.com:...) or anything else, return as-is
    return url
