import hmac
import hashlib

from unittest.mock import patch

from centrum_blog import app
from centrum_blog.constants import static_content_path


class DummyThread:
    def __init__(self, target, args=()):
        self.target = target
        self.args = args
        self.started = False

    def start(self):
        self.started = True
        self.target(*self.args)


class TestReindexEndpoint:
    """Test cases for the /reindex webhook endpoint."""

    @patch("centrum_blog.threading.Thread", new=DummyThread)
    @patch("centrum_blog.indexer.reindex")
    @patch("centrum_blog.credential.get_secret", return_value="test-secret")
    def test_triggers_reindex_with_valid_signature(self, mock_get_secret, mock_reindex):
        payload = b'{"ref": "refs/heads/main"}'
        signature = hmac.new(mock_get_secret.return_value.encode(), msg=payload, digestmod=hashlib.sha256).hexdigest()
        headers = {"X-Hub-Signature-256": f"sha256={signature}"}

        client = app.test_client()
        response = client.post("/reindex", data=payload, headers=headers)

        assert response.status_code == 200
        assert response.get_json() == {"status": "OK"}
        mock_reindex.assert_called_once_with(static_content_path)

    @patch("centrum_blog.indexer.reindex")
    def test_returns_401_without_signature(self, mock_reindex):
        client = app.test_client()
        response = client.post("/reindex", data=b"{}")

        assert response.status_code == 401
        mock_reindex.assert_not_called()

    @patch("centrum_blog.indexer.reindex")
    def test_returns_503_for_non_sha256_algorithm(self, mock_reindex):
        headers = {"X-Hub-Signature-256": "sha1=deadbeef"}

        client = app.test_client()
        response = client.post("/reindex", data=b"{}", headers=headers)

        assert response.status_code == 503
        mock_reindex.assert_not_called()

    @patch("centrum_blog.indexer.reindex")
    @patch("centrum_blog.credential.get_secret", return_value="test-secret")
    def test_returns_401_for_invalid_signature(self, mock_get_secret, mock_reindex):
        payload = b'{"ref": "refs/heads/main"}'
        headers = {"X-Hub-Signature-256": "sha256=invalidsignature"}

        client = app.test_client()
        response = client.post("/reindex", data=payload, headers=headers)

        assert response.status_code == 401
        mock_reindex.assert_not_called()
