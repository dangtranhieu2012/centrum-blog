import base64
from unittest.mock import MagicMock, patch

from centrum_blog.libs import oci_helper
from centrum_blog.libs.oci_helper import AuthConfigException
from centrum_blog.libs.oci_helper import vault


class TestGetConfig:
    def setup_method(self):
        oci_helper.config = {}

    def test_returns_cached_config_when_available(self):
        oci_helper.config = {"region": "ap-tokyo-1"}

        with patch("centrum_blog.libs.oci_helper.os.environ.get") as mock_get_env:
            result = oci_helper.get_config()

        assert result == {"region": "ap-tokyo-1"}
        mock_get_env.assert_not_called()

    @patch("centrum_blog.libs.oci_helper.os.environ.get", return_value=None)
    def test_returns_empty_dict_when_profile_not_set(self, mock_get_env):
        result = oci_helper.get_config()

        assert result == {}
        assert oci_helper.config == {}
        mock_get_env.assert_called_once_with("OCI_USER_PROFILE")

    @patch("centrum_blog.libs.oci_helper.oci.config.from_file", return_value={"tenancy": "ocid1.tenancy"})
    @patch("centrum_blog.libs.oci_helper.os.environ.get", return_value="DEFAULT")
    def test_loads_config_from_profile_and_caches(self, mock_get_env, mock_from_file):
        result = oci_helper.get_config()

        assert result == {"tenancy": "ocid1.tenancy"}
        assert oci_helper.config == {"tenancy": "ocid1.tenancy"}
        mock_get_env.assert_called_once_with("OCI_USER_PROFILE")
        mock_from_file.assert_called_once_with(profile_name="DEFAULT")

    @patch("centrum_blog.libs.oci_helper.oci.config.from_file", side_effect=FileNotFoundError())
    @patch("centrum_blog.libs.oci_helper.os.environ.get", return_value="DEFAULT")
    def test_returns_empty_dict_when_config_file_missing(self, mock_get_env, mock_from_file):
        result = oci_helper.get_config()

        assert result == {}
        assert oci_helper.config == {}
        mock_get_env.assert_called_once_with("OCI_USER_PROFILE")
        mock_from_file.assert_called_once_with(profile_name="DEFAULT")

    @patch("centrum_blog.libs.oci_helper.oci.config.from_file", side_effect=Exception("bad profile"))
    @patch("centrum_blog.libs.oci_helper.os.environ.get", return_value="DEFAULT")
    def test_returns_empty_dict_on_unexpected_load_error(self, mock_get_env, mock_from_file):
        result = oci_helper.get_config()

        assert result == {}
        assert oci_helper.config == {}
        mock_get_env.assert_called_once_with("OCI_USER_PROFILE")
        mock_from_file.assert_called_once_with(profile_name="DEFAULT")


class TestGetSigner:
    def setup_method(self):
        oci_helper.signer = None

    def test_returns_cached_signer_when_available(self):
        cached_signer = object()
        oci_helper.signer = cached_signer

        with patch("centrum_blog.libs.oci_helper.oci.auth.signers.InstancePrincipalsSecurityTokenSigner") as mock_signer_cls:
            result = oci_helper.get_signer()

        assert result is cached_signer
        mock_signer_cls.assert_not_called()

    @patch("centrum_blog.libs.oci_helper.oci.auth.signers.InstancePrincipalsSecurityTokenSigner")
    def test_creates_and_caches_signer(self, mock_signer_cls):
        signer_instance = object()
        mock_signer_cls.return_value = signer_instance

        result = oci_helper.get_signer()

        assert result is signer_instance
        assert oci_helper.signer is signer_instance
        mock_signer_cls.assert_called_once_with()

    @patch(
        "centrum_blog.libs.oci_helper.oci.auth.signers.InstancePrincipalsSecurityTokenSigner",
        side_effect=Exception("failed"),
    )
    def test_returns_none_when_signer_creation_fails(self, mock_signer_cls):
        result = oci_helper.get_signer()

        assert result is None
        assert oci_helper.signer is None
        mock_signer_cls.assert_called_once_with()


class TestGetConfigOrSigner:
    @patch("centrum_blog.libs.oci_helper.get_signer")
    @patch("centrum_blog.libs.oci_helper.get_config", return_value={"region": "eu-frankfurt-1"})
    def test_returns_config_when_non_empty(self, mock_get_config, mock_get_signer):
        result = oci_helper.get_config_or_signer()

        assert result == {"region": "eu-frankfurt-1"}
        mock_get_config.assert_called_once_with()
        mock_get_signer.assert_not_called()

    @patch("centrum_blog.libs.oci_helper.get_signer", return_value="signer")
    @patch("centrum_blog.libs.oci_helper.get_config", return_value={})
    def test_falls_back_to_signer_when_config_empty(self, mock_get_config, mock_get_signer):
        result = oci_helper.get_config_or_signer()

        assert result == "signer"
        mock_get_config.assert_called_once_with()
        mock_get_signer.assert_called_once_with()


class TestGetClient:
    @patch("centrum_blog.libs.oci_helper.get_config_or_signer", return_value=None)
    def test_raises_when_no_auth_material(self, mock_get_config_or_signer):
        with patch("centrum_blog.libs.oci_helper.logger.error") as mock_log:
            try:
                oci_helper.get_client(lambda **kwargs: kwargs)
                assert False, "Expected AuthConfigException"
            except AuthConfigException as exc:
                assert "Cannot find a valid configuration" in str(exc)

        mock_get_config_or_signer.assert_called_once_with()
        mock_log.assert_not_called()

    @patch("centrum_blog.libs.oci_helper.get_config_or_signer", return_value={"region": "ap-seoul-1"})
    def test_initializes_client_with_config_dict(self, mock_get_config_or_signer):
        initializer = MagicMock(return_value="client")

        result = oci_helper.get_client(initializer, service_endpoint="https://example")

        assert result == "client"
        initializer.assert_called_once_with(
            config={"region": "ap-seoul-1"},
            service_endpoint="https://example",
        )
        mock_get_config_or_signer.assert_called_once_with()

    @patch("centrum_blog.libs.oci_helper.get_config_or_signer", return_value="signer-object")
    def test_initializes_client_with_signer(self, mock_get_config_or_signer):
        initializer = MagicMock(return_value="client")

        result = oci_helper.get_client(initializer, timeout=10)

        assert result == "client"
        initializer.assert_called_once_with(
            config={},
            signer="signer-object",
            timeout=10,
        )
        mock_get_config_or_signer.assert_called_once_with()

    @patch("centrum_blog.libs.oci_helper.get_config_or_signer", return_value={"region": "ap-singapore-1"})
    def test_returns_none_when_initializer_raises(self, mock_get_config_or_signer):
        def _initializer(**kwargs):
            raise RuntimeError("boom")

        with patch("centrum_blog.libs.oci_helper.logger.error") as mock_log:
            result = oci_helper.get_client(_initializer)

        assert result is None
        mock_get_config_or_signer.assert_called_once_with()
        mock_log.assert_called_once()


class TestVaultGetSecret:
    @patch("centrum_blog.libs.oci_helper.vault.get_client")
    def test_returns_decoded_secret_value(self, mock_get_client):
        decoded_secret = "my-secret-value"
        encoded_secret = base64.b64encode(decoded_secret.encode("utf-8")).decode("utf-8")

        client = MagicMock()
        client.get_secret_bundle.return_value.data.secret_bundle_content.content = encoded_secret
        mock_get_client.return_value = client

        result = vault.get_secret("ocid1.vaultsecret")

        assert result == decoded_secret
        mock_get_client.assert_called_once_with(vault.oci.secrets.SecretsClient)
        client.get_secret_bundle.assert_called_once_with("ocid1.vaultsecret")

    @patch("centrum_blog.libs.oci_helper.vault.get_client", return_value=None)
    def test_returns_none_when_client_init_fails(self, mock_get_client):
        result = vault.get_secret("ocid1.vaultsecret")

        assert result is None
        mock_get_client.assert_called_once_with(vault.oci.secrets.SecretsClient)

    @patch("centrum_blog.libs.oci_helper.vault.get_client")
    def test_returns_none_on_service_error(self, mock_get_client):
        class DummyServiceError(Exception):
            pass

        client = MagicMock()
        client.get_secret_bundle.side_effect = DummyServiceError("service error")
        mock_get_client.return_value = client

        with patch("centrum_blog.libs.oci_helper.vault.oci.exceptions.ServiceError", DummyServiceError):
            result = vault.get_secret("ocid1.vaultsecret")

        assert result is None

    @patch("centrum_blog.libs.oci_helper.vault.get_client", side_effect=AuthConfigException("no auth"))
    def test_returns_none_on_auth_config_exception(self, mock_get_client):
        result = vault.get_secret("ocid1.vaultsecret")

        assert result is None
        mock_get_client.assert_called_once_with(vault.oci.secrets.SecretsClient)

    @patch("centrum_blog.libs.oci_helper.vault.get_client", side_effect=RuntimeError("boom"))
    def test_returns_none_on_unexpected_exception(self, mock_get_client):
        result = vault.get_secret("ocid1.vaultsecret")

        assert result is None
        mock_get_client.assert_called_once_with(vault.oci.secrets.SecretsClient)
