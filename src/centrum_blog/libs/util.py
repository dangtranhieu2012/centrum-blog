from typing import Optional

from centrum_blog.libs.oci_helper import vault


def get_secret(secret: Optional[str] = None, secret_ocid: Optional[str] = None) -> str:
    s = secret

    if secret_ocid is not None:
        s = vault.get_secret(secret_ocid)
    
    return s if s is not None else ""
