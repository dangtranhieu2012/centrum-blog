import datetime as dt
import json
import os
from unittest.mock import MagicMock, patch

from centrum_blog.libs.article import (
    get_adjacent_articles,
    get_article_metadata,
    get_articles_list,
    get_total_pages,
    is_article_exist_on_fs,
)


class TestIsArticleExistOnFs:
    """Test cases for is_article_exist_on_fs function"""

    def test_article_exists_all_files_present(self, tmp_path):
        """Test when article exists with all required files"""
        # Create a temporary structure with all required files
        posts_dir = tmp_path / "posts"
        article_dir = posts_dir / "test-article"
        article_dir.mkdir(parents=True)

        # Create required files
        (article_dir / "metadata.json").write_text(json.dumps({"title": "Test"}))
        (article_dir / "content.md").write_text("# Test Article")

        with patch('centrum_blog.libs.article.static_content_path', str(tmp_path)):
            result = is_article_exist_on_fs("test-article")

        assert result is True

    def test_article_folder_does_not_exist(self, tmp_path):
        """Test when article folder does not exist"""
        posts_dir = tmp_path / "posts"
        posts_dir.mkdir(parents=True)

        with patch('centrum_blog.libs.article.static_content_path', str(tmp_path)):
            result = is_article_exist_on_fs("nonexistent-article")

        assert result is False

    def test_article_path_not_a_directory(self, tmp_path):
        """Test when article path exists but is not a directory (is a file)"""
        posts_dir = tmp_path / "posts"
        posts_dir.mkdir(parents=True)

        # Create a file instead of a directory
        (posts_dir / "file-not-folder").write_text("content")

        with patch('centrum_blog.libs.article.static_content_path', str(tmp_path)):
            result = is_article_exist_on_fs("file-not-folder")

        assert result is False

    def test_metadata_file_missing(self, tmp_path):
        """Test when metadata.json file is missing"""
        posts_dir = tmp_path / "posts"
        article_dir = posts_dir / "incomplete-article"
        article_dir.mkdir(parents=True)

        # Create only content.md, missing metadata.json
        (article_dir / "content.md").write_text("# Article")

        with patch('centrum_blog.libs.article.static_content_path', str(tmp_path)):
            result = is_article_exist_on_fs("incomplete-article")

        assert result is False

    def test_content_file_missing(self, tmp_path):
        """Test when content.md file is missing"""
        posts_dir = tmp_path / "posts"
        article_dir = posts_dir / "no-content-article"
        article_dir.mkdir(parents=True)

        # Create only metadata.json, missing content.md
        (article_dir / "metadata.json").write_text(json.dumps({"title": "Test"}))

        with patch('centrum_blog.libs.article.static_content_path', str(tmp_path)):
            result = is_article_exist_on_fs("no-content-article")

        assert result is False

    def test_both_metadata_and_content_missing(self, tmp_path):
        """Test when both metadata and content files are missing"""
        posts_dir = tmp_path / "posts"
        article_dir = posts_dir / "empty-article"
        article_dir.mkdir(parents=True)

        # Create only the directory, no files

        with patch('centrum_blog.libs.article.static_content_path', str(tmp_path)):
            result = is_article_exist_on_fs("empty-article")

        assert result is False


class TestGetTotalPages:
    """Test cases for get_total_pages function"""

    @patch('centrum_blog.libs.article.get_db_session')
    def test_get_total_pages_with_articles(self, mock_get_db_session):
        """Test total pages calculation with multiple articles"""
        # Setup
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.scalar.return_value = 25
        mock_session.query.return_value = mock_query
        mock_get_db_session.return_value.__enter__.return_value = mock_session

        # Execute
        result = get_total_pages(per_page=10)

        # Assert: 25 articles / 10 per_page = 2.5, ceil = 3
        assert result == 3

    @patch('centrum_blog.libs.article.get_db_session')
    def test_get_total_pages_exact_division(self, mock_get_db_session):
        """Test total pages when articles divide evenly into pages"""
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.scalar.return_value = 20
        mock_session.query.return_value = mock_query
        mock_get_db_session.return_value.__enter__.return_value = mock_session

        result = get_total_pages(per_page=10)

        # Assert: 20 articles / 10 per_page = 2
        assert result == 2

    @patch('centrum_blog.libs.article.get_db_session')
    def test_get_total_pages_zero_articles(self, mock_get_db_session):
        """Test total pages when no articles exist"""
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.scalar.return_value = 0
        mock_session.query.return_value = mock_query
        mock_get_db_session.return_value.__enter__.return_value = mock_session

        result = get_total_pages(per_page=10)

        # Assert: Should return 1 when no articles
        assert result == 1

    @patch('centrum_blog.libs.article.get_db_session')
    def test_get_total_pages_single_article(self, mock_get_db_session):
        """Test total pages with single article"""
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.scalar.return_value = 1
        mock_session.query.return_value = mock_query
        mock_get_db_session.return_value.__enter__.return_value = mock_session

        result = get_total_pages(per_page=10)

        # Assert: 1 article / 10 per_page = 0.1, ceil = 1
        assert result == 1

    @patch('centrum_blog.libs.article.get_db_session')
    def test_get_total_pages_single_item_per_page(self, mock_get_db_session):
        """Test total pages with single item per page"""
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.scalar.return_value = 5
        mock_session.query.return_value = mock_query
        mock_get_db_session.return_value.__enter__.return_value = mock_session

        result = get_total_pages(per_page=1)

        # Assert: 5 articles / 1 per_page = 5
        assert result == 5

    @patch('centrum_blog.libs.article.get_db_session')
    def test_get_total_pages_uses_context_manager(self, mock_get_db_session):
        """Test that get_total_pages correctly uses database session context manager"""
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.scalar.return_value = 15
        mock_session.query.return_value = mock_query

        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_session
        mock_context.__exit__.return_value = None
        mock_get_db_session.return_value = mock_context

        result = get_total_pages(per_page=5)

        # Assert context manager was used
        mock_get_db_session.assert_called_once()
        mock_context.__enter__.assert_called_once()
        mock_context.__exit__.assert_called_once()
        # Assert: 15 articles / 5 per_page = 3
        assert result == 3


class TestGetArticlesList:
    """Test cases for get_articles_list function."""

    @patch('centrum_blog.libs.article.get_article_metadata')
    @patch('centrum_blog.libs.article.get_db_session')
    def test_get_articles_list_returns_metadata_for_each_row(
        self,
        mock_get_db_session,
        mock_get_article_metadata,
    ):
        mock_session = MagicMock()
        mock_query = MagicMock()
        rows = [('article-1',), ('article-2',)]
        mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = rows
        mock_session.query.return_value = mock_query
        mock_get_db_session.return_value.__enter__.return_value = mock_session
        mock_get_article_metadata.side_effect = lambda article_id: {'article_id': article_id}

        result = get_articles_list(page=1, per_page=2)

        assert result == [
            {'article_id': 'article-1'},
            {'article_id': 'article-2'},
        ]
        mock_get_article_metadata.assert_any_call('article-1')
        mock_get_article_metadata.assert_any_call('article-2')


class TestGetArticleMetadata:
    """Test cases for get_article_metadata function."""

    def test_get_article_metadata_reads_json_and_sets_published_and_path(self, tmp_path):
        posts_dir = tmp_path / 'posts'
        article_dir = posts_dir / 'test-article'
        article_dir.mkdir(parents=True)

        metadata = {'title': 'Test Article', 'author': 'tester'}
        metadata_file = article_dir / 'metadata.json'
        metadata_file.write_text(json.dumps(metadata))

        os.utime(article_dir, (1000, 1000))

        with patch('centrum_blog.libs.article.static_content_path', str(tmp_path)):
            result = get_article_metadata('test-article')

        assert result['title'] == 'Test Article'
        assert result['author'] == 'tester'
        assert result['article_id'] == 'test-article'
        assert result['article_path'] == article_dir
        assert result['published'] == dt.date.fromtimestamp(1000)


class TestGetAdjacentArticles:
    """Test cases for get_adjacent_articles function."""

    @patch('centrum_blog.libs.article.get_article_metadata')
    @patch('centrum_blog.libs.article.get_db_session')
    def test_get_adjacent_articles_returns_previous_and_next(
        self,
        mock_get_db_session,
        mock_get_article_metadata,
    ):
        mock_session = MagicMock()

        current_query = MagicMock()
        current_query.filter.return_value = current_query
        current_query.first.return_value = (1000,)

        prev_query = MagicMock()
        prev_query.filter.return_value = prev_query
        prev_query.order_by.return_value = prev_query
        prev_query.first.return_value = ('prev-article',)

        next_query = MagicMock()
        next_query.filter.return_value = next_query
        next_query.order_by.return_value = next_query
        next_query.first.return_value = ('next-article',)

        mock_session.query.side_effect = [current_query, prev_query, next_query]
        mock_get_db_session.return_value.__enter__.return_value = mock_session
        mock_get_article_metadata.side_effect = lambda article_id: {'article_id': article_id}

        previous_article, next_article = get_adjacent_articles('current-article')

        assert previous_article == {'article_id': 'prev-article'}
        assert next_article == {'article_id': 'next-article'}
        assert mock_session.query.call_count == 3

    @patch('centrum_blog.libs.article.get_article_metadata')
    @patch('centrum_blog.libs.article.get_db_session')
    def test_get_adjacent_articles_returns_only_previous_when_no_next(
        self,
        mock_get_db_session,
        mock_get_article_metadata,
    ):
        mock_session = MagicMock()
        current_query = MagicMock()
        current_query.filter.return_value = current_query
        current_query.first.return_value = (1000,)

        prev_query = MagicMock()
        prev_query.filter.return_value = prev_query
        prev_query.order_by.return_value = prev_query
        prev_query.first.return_value = ('prev-article',)

        next_query = MagicMock()
        next_query.filter.return_value = next_query
        next_query.order_by.return_value = next_query
        next_query.first.return_value = None

        mock_session.query.side_effect = [current_query, prev_query, next_query]
        mock_get_db_session.return_value.__enter__.return_value = mock_session
        mock_get_article_metadata.side_effect = lambda article_id: {'article_id': article_id}

        previous_article, next_article = get_adjacent_articles('current-article')

        assert previous_article == {'article_id': 'prev-article'}
        assert next_article is None
        assert mock_session.query.call_count == 3

    @patch('centrum_blog.libs.article.get_article_metadata')
    @patch('centrum_blog.libs.article.get_db_session')
    def test_get_adjacent_articles_returns_only_next_when_no_previous(
        self,
        mock_get_db_session,
        mock_get_article_metadata,
    ):
        mock_session = MagicMock()
        current_query = MagicMock()
        current_query.filter.return_value = current_query
        current_query.first.return_value = (1000,)

        prev_query = MagicMock()
        prev_query.filter.return_value = prev_query
        prev_query.order_by.return_value = prev_query
        prev_query.first.return_value = None

        next_query = MagicMock()
        next_query.filter.return_value = next_query
        next_query.order_by.return_value = next_query
        next_query.first.return_value = ('next-article',)

        mock_session.query.side_effect = [current_query, prev_query, next_query]
        mock_get_db_session.return_value.__enter__.return_value = mock_session
        mock_get_article_metadata.side_effect = lambda article_id: {'article_id': article_id}

        previous_article, next_article = get_adjacent_articles('current-article')

        assert previous_article is None
        assert next_article == {'article_id': 'next-article'}
        assert mock_session.query.call_count == 3

    @patch('centrum_blog.libs.article.get_article_metadata')
    @patch('centrum_blog.libs.article.get_db_session')
    def test_get_adjacent_articles_returns_none_when_article_missing(
        self,
        mock_get_db_session,
        mock_get_article_metadata,
    ):
        mock_session = MagicMock()
        current_query = MagicMock()
        current_query.filter.return_value = current_query
        current_query.first.return_value = None

        mock_session.query.return_value = current_query
        mock_get_db_session.return_value.__enter__.return_value = mock_session

        previous_article, next_article = get_adjacent_articles('missing-article')

        assert previous_article is None
        assert next_article is None
        mock_get_article_metadata.assert_not_called()
