import logging
import oci
import os

from typing import Callable


config = {}
signer = None

logger = logging.getLogger(__name__)


class AuthConfigException(Exception):
    pass


def get_config() -> dict:
    global config

    if bool(config):
        return config

    ret = {}

    profile_name = os.environ.get("OCI_USER_PROFILE")
    if profile_name:
        try:
            ret = oci.config.from_file(profile_name=profile_name)
        except FileNotFoundError:
            logger.error("OCI config file or API key file not found.")
            return {}
        except oci.config.config.ConfigErrors as e:
            logger.error(f"Error loading OCI config profile '{OCI_USER_PROFILE}': {e}")
            return {}
        except Exception as e:
            logger.error(f"An unexpected error occurred while getting OCI config: {e}")
            return {}

    config = ret

    return config


def get_signer() -> oci.auth.signers.InstancePrincipalsSecurityTokenSigner | None:
    global signer

    if signer is not None:
        return signer

    ret = None
    try:
        ret = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
    except Exception as e:
        logger.error(f"An unexpected error occurred while getting signer: {e}")
        return None

    signer = ret

    return signer


def get_config_or_signer() -> oci.auth.signers.InstancePrincipalsSecurityTokenSigner | dict | None:
    ret = get_config()

    if not bool(ret):
        ret = get_signer()

    return ret


def get_client(client_initializer: Callable, **kwargs):
    config_or_signer = get_config_or_signer()

    if config_or_signer is None:
        raise ConfigException("Cannot find a valid configuration to authenticate with OCI")

    try:
        client = None
        if type(config_or_signer) is not dict:
            client = client_initializer(config={}, signer=config_or_signer, **kwargs)
        else:
            client = client_initializer(config=config_or_signer, **kwargs)
        return client
    except Exception as e:
        logger.error(f"An unexpected error occurred while initializing client: {e}")
        return None
