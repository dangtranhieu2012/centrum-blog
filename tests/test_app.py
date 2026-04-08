import datetime as dt
import hashlib
import hmac
from unittest.mock import patch

from centrum_blog import app, generate_pagination, sanitize_name
from centrum_blog.constants import static_content_path


class TestSanitizeName:
    def test_replaces_unsupported_characters_with_hyphen(self):
        result = sanitize_name("Hello, World!/2026")

        assert result == "Hello--World--2026"

    def test_keeps_supported_characters(self):
        result = sanitize_name("safe_name-123")

        assert result == "safe_name-123"


class TestGeneratePagination:
    def test_returns_window_with_ellipses_for_middle_page(self):
        result = generate_pagination(current_page=5, total_pages=10)

        assert result == ["ellipsis", 3, 4, 5, 6, 7, "ellipsis"]

    def test_returns_start_window_without_leading_ellipsis(self):
        result = generate_pagination(current_page=1, total_pages=5)

        assert result == [1, 2, 3, "ellipsis"]

    def test_returns_all_pages_when_total_is_small(self):
        result = generate_pagination(current_page=2, total_pages=3)

        assert result == [1, 2, 3]


class TestIndexRoute:
    @patch("centrum_blog.generate_pagination", return_value=[1])
    @patch("centrum_blog.article.get_articles_list")
    @patch("centrum_blog.article.get_total_pages", return_value=3)
    def test_index_uses_default_per_page_for_invalid_cookie(
        self,
        mock_get_total_pages,
        mock_get_articles_list,
        mock_generate_pagination,
    ):
        mock_get_articles_list.return_value = [
            {
                "article_id": "a-1",
                "title": "A title",
                "summary": "A summary",
                "published": dt.date(2026, 1, 1),
            }
        ]

        client = app.test_client()
        response = client.get("/", headers={"Cookie": "per_page=999"})

        assert response.status_code == 200
        assert b"A title" in response.data
        mock_get_articles_list.assert_called_once_with(page=1, per_page=10)
        assert mock_get_total_pages.call_count == 1
        mock_generate_pagination.assert_called_once_with(1, 3)

    @patch("centrum_blog.generate_pagination", return_value=[3, 4])
    @patch("centrum_blog.article.get_articles_list")
    @patch("centrum_blog.article.get_total_pages", return_value=4)
    def test_index_treats_page_zero_as_last_page(
        self,
        mock_get_total_pages,
        mock_get_articles_list,
        mock_generate_pagination,
    ):
        mock_get_articles_list.return_value = []

        client = app.test_client()
        response = client.get("/0", headers={"Cookie": "per_page=10"})

        assert response.status_code == 200
        mock_get_articles_list.assert_called_once_with(page=4, per_page=10)
        mock_generate_pagination.assert_called_once_with(4, 4)
        assert mock_get_total_pages.call_count == 1

    @patch("centrum_blog.article.get_articles_list")
    @patch("centrum_blog.article.get_total_pages", return_value=2)
    def test_index_returns_404_when_page_exceeds_total_pages(
        self,
        mock_get_total_pages,
        mock_get_articles_list,
    ):
        client = app.test_client()
        response = client.get("/3")

        assert response.status_code == 404
        mock_get_total_pages.assert_called_once_with(10)
        mock_get_articles_list.assert_not_called()


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
