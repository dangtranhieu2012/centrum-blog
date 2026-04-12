import datetime as dt
import hashlib
import hmac
import json
from unittest.mock import patch

from centrum_blog import app, generate_pagination, sanitize_name
from centrum_blog.constants import static_content_path
from centrum_blog.libs import indexer


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


class TestReindexEndpoint:
    """Test cases for the /reindex webhook endpoint."""

    @staticmethod
    def _build_sha256_signature(secret: str, payload: bytes) -> str:
        return hmac.new(secret.encode(), msg=payload, digestmod=hashlib.sha256).hexdigest()

    @patch("centrum_blog.index_executor.submit")
    @patch("centrum_blog.credential.get_secret", return_value="test-secret")
    def test_triggers_reindex_with_valid_signature(self, mock_get_secret, mock_submit):
        payload = b'{"ref": "refs/heads/main"}'
        signature = self._build_sha256_signature(mock_get_secret.return_value, payload)
        headers = {"X-Hub-Signature-256": f"sha256={signature}"}

        client = app.test_client()
        response = client.post("/reindex", data=payload, headers=headers)

        assert response.status_code == 200
        assert response.get_json() == {"status": "OK"}
        mock_submit.assert_called_once_with(indexer.reindex, static_content_path)

    @patch("centrum_blog.index_executor.submit")
    def test_returns_401_without_signature(self, mock_submit):
        client = app.test_client()
        response = client.post("/reindex", data=b"{}")

        assert response.status_code == 401
        mock_submit.assert_not_called()

    @patch("centrum_blog.index_executor.submit")
    def test_returns_503_for_non_sha256_algorithm(self, mock_submit):
        headers = {"X-Hub-Signature-256": "sha1=deadbeef"}

        client = app.test_client()
        response = client.post("/reindex", data=b"{}", headers=headers)

        assert response.status_code == 503
        mock_submit.assert_not_called()

    @patch("centrum_blog.index_executor.submit")
    @patch("centrum_blog.credential.get_secret", return_value="test-secret")
    def test_returns_401_for_invalid_signature(self, mock_get_secret, mock_submit):
        payload = b'{"ref": "refs/heads/main"}'
        headers = {"X-Hub-Signature-256": "sha256=invalidsignature"}

        client = app.test_client()
        response = client.post("/reindex", data=payload, headers=headers)

        assert response.status_code == 401
        mock_submit.assert_not_called()

    @patch("centrum_blog.index_executor.submit")
    @patch("centrum_blog.credential.get_secret", return_value="test-secret")
    def test_returns_429_after_reaching_rate_limit(self, mock_get_secret, mock_submit):
        payload = b'{"ref": "refs/heads/main"}'
        signature = self._build_sha256_signature(mock_get_secret.return_value, payload)
        headers = {"X-Hub-Signature-256": f"sha256={signature}"}

        client = app.test_client()

        for _ in range(5):
            response = client.post(
                "/reindex",
                data=payload,
                headers=headers,
                environ_overrides={"REMOTE_ADDR": "10.0.0.1"},
            )
            assert response.status_code == 200

        blocked = client.post(
            "/reindex",
            data=payload,
            headers=headers,
            environ_overrides={"REMOTE_ADDR": "10.0.0.1"},
        )

        assert blocked.status_code == 429
        assert mock_submit.call_count == 5

    @patch("centrum_blog.index_executor.submit")
    @patch("centrum_blog.credential.get_secret", return_value="test-secret")
    def test_rate_limit_is_scoped_per_ip(self, mock_get_secret, mock_submit):
        payload = b'{"ref": "refs/heads/main"}'
        signature = self._build_sha256_signature(mock_get_secret.return_value, payload)
        headers = {"X-Hub-Signature-256": f"sha256={signature}"}

        client = app.test_client()

        for _ in range(5):
            response = client.post(
                "/reindex",
                data=payload,
                headers=headers,
                environ_overrides={"REMOTE_ADDR": "10.0.0.2"},
            )
            assert response.status_code == 200

        blocked = client.post(
            "/reindex",
            data=payload,
            headers=headers,
            environ_overrides={"REMOTE_ADDR": "10.0.0.2"},
        )
        assert blocked.status_code == 429

        allowed_other_ip = client.post(
            "/reindex",
            data=payload,
            headers=headers,
            environ_overrides={"REMOTE_ADDR": "10.0.0.3"},
        )

        assert allowed_other_ip.status_code == 200
        assert mock_submit.call_count == 6


class TestReadRoute:
    @patch("centrum_blog.mistune.create_markdown")
    @patch("centrum_blog.article.get_adjacent_articles", return_value=(None, None))
    @patch("centrum_blog.article.get_article_metadata")
    def test_read_renders_article_when_files_exist(
        self,
        mock_get_article_metadata,
        mock_get_adjacent_articles,
        mock_create_markdown,
        tmp_path,
    ):
        content_root = tmp_path / "content"
        author_dir = content_root / "authors" / "test-author"
        author_dir.mkdir(parents=True)
        (author_dir / "metadata.json").write_text(json.dumps({"name": "Test Author", "avatar": "avatar.png"}))

        article_dir = tmp_path / "posts" / "clean-name"
        article_dir.mkdir(parents=True)
        (article_dir / "content.md").write_text("# Hello")

        mock_get_article_metadata.return_value = {
            "author": "test-author",
            "published": dt.date(2026, 1, 1),
            "title": "Clean Title",
            "tags": ["python"],
            "article_path": article_dir,
        }
        mock_create_markdown.return_value = lambda _text: "<p>Rendered body</p>"

        with patch("centrum_blog.static_content_path", str(content_root)):
            client = app.test_client()
            response = client.get("/read/clean!name")

        assert response.status_code == 200
        assert b"Clean Title" in response.data
        assert b"Rendered body" in response.data
        assert b"Test Author" in response.data
        mock_get_article_metadata.assert_called_once_with("clean-name")
        mock_get_adjacent_articles.assert_called_once_with("clean-name")

    @patch("centrum_blog.article.get_article_metadata", side_effect=Exception("boom"))
    def test_read_returns_404_on_metadata_error(self, mock_get_article_metadata):
        client = app.test_client()
        response = client.get("/read/does-not-matter")

        assert response.status_code == 404
        mock_get_article_metadata.assert_called_once()


class TestAboutRoute:
    @patch("centrum_blog.mistune.create_markdown")
    def test_about_renders_markdown_when_file_exists(
        self,
        mock_create_markdown,
        tmp_path,
    ):
        content_root = tmp_path / "content"
        content_root.mkdir(parents=True)
        (content_root / "about.md").write_text("# About Me")

        mock_create_markdown.return_value = lambda _text: "<h1>About Me</h1>"

        with patch("centrum_blog.static_content_path", str(content_root)):
            client = app.test_client()
            response = client.get("/about")

        assert response.status_code == 200
        assert b"About Me" in response.data

    def test_about_renders_fallback_when_file_missing(self, tmp_path):
        content_root = tmp_path / "content"
        content_root.mkdir(parents=True)

        with patch("centrum_blog.static_content_path", str(content_root)):
            client = app.test_client()
            response = client.get("/about")

        assert response.status_code == 200
        assert b"About page content not found" in response.data
