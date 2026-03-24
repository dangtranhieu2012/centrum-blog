import oci
import base64
import logging

from centrum_blog.libs.oci_helper import AuthConfigException, get_client 


logger = logging.getLogger(__name__)


def get_secret(secret_ocid: str) -> str | None:
    """
    Retrieves a secret from OCI Vault
    """

    try:
        secrets_client = get_client(oci.secrets.SecretsClient)
        get_secret_bundle_response = secrets_client.get_secret_bundle(secret_ocid)
        secret_content_base64 = get_secret_bundle_response.data.secret_bundle_content.content
        secret_value = base64.b64decode(secret_content_base64).decode('utf-8')
        
        return secret_value
    except oci.exceptions.ServiceError as e:
        logger.error(f"Error accessing secret: {e}")
        return None
    except AuthConfigException as e:
        logger.error(f"OCI configuration error: {e}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred while retrieving secret: {e}")
        return None
