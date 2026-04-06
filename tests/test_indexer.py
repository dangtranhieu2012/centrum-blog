from pathlib import Path
from unittest.mock import MagicMock, patch

import json
import os
from datetime import datetime

from git.exc import NoSuchPathError

from centrum_blog.libs import indexer
from centrum_blog.libs.models import BlogIndex


class TestIndexerReindex:
    """Test cases for the indexer.reindex function."""

    @patch("centrum_blog.libs.indexer.index_all")
    @patch("centrum_blog.libs.indexer.subprocess.run")
    @patch("centrum_blog.libs.indexer.credential.get_authenticated_git_url", return_value="https://ex.com/repo.git")
    @patch("centrum_blog.libs.indexer.git.Repo", side_effect=NoSuchPathError("path not found"))
    def test_reindex_clones_repo_and_indexes_all_when_path_missing(
        self,
        mock_git_repo,
        mock_get_authenticated_git_url,
        mock_subprocess_run,
        mock_index_all,
        tmp_path,
    ):
        static_content_path = tmp_path / "static_content"
        expected_posts_path = Path(static_content_path) / "posts"

        indexer.reindex(str(static_content_path))

        mock_get_authenticated_git_url.assert_called_once()
        mock_git_repo.clone_from.assert_called_once_with("https://ex.com/repo.git", str(static_content_path))
        mock_subprocess_run.assert_called_once()
        mock_index_all.assert_called_once_with(expected_posts_path)

    @patch("centrum_blog.libs.indexer.index_all")
    @patch("centrum_blog.libs.indexer.index_changes")
    @patch("centrum_blog.libs.indexer.subprocess.run")
    @patch("centrum_blog.libs.indexer.git.Repo")
    def test_reindex_does_not_index_when_head_unchanged(
        self,
        mock_git_repo,
        mock_subprocess_run,
        mock_index_changes,
        mock_index_all,
        tmp_path,
    ):
        static_content_path = tmp_path / "static_content"
        repo_mock = MagicMock()
        commit = MagicMock()
        repo_mock.head.commit = commit
        repo_mock.remote.return_value.pull.return_value = None
        mock_git_repo.return_value = repo_mock

        indexer.reindex(str(static_content_path))

        mock_git_repo.assert_called_once_with(str(static_content_path))
        mock_subprocess_run.assert_called_once()
        mock_index_changes.assert_not_called()
        mock_index_all.assert_not_called()

    @patch("centrum_blog.libs.indexer.index_all")
    @patch("centrum_blog.libs.indexer.index_changes")
    @patch("centrum_blog.libs.indexer.subprocess.run")
    @patch("centrum_blog.libs.indexer.git.Repo")
    def test_reindex_indexes_changes_when_head_differs(
        self,
        mock_git_repo,
        mock_subprocess_run,
        mock_index_changes,
        mock_index_all,
        tmp_path,
    ):
        static_content_path = tmp_path / "static_content"
        old_head = MagicMock()
        new_head = MagicMock()
        diff_index = [MagicMock()]
        old_head.diff.return_value = diff_index

        repo_mock = MagicMock()
        repo_mock.head.commit = old_head

        def pull_side_effect():
            repo_mock.head.commit = new_head

        repo_mock.remote.return_value.pull.side_effect = pull_side_effect
        mock_git_repo.return_value = repo_mock

        indexer.reindex(str(static_content_path))

        mock_index_changes.assert_called_once_with(Path(static_content_path) / "posts", diff_index)
        mock_index_all.assert_not_called()


class TestGetMetadata:
    """Test cases for the indexer.get_metadata function."""

    def test_get_metadata_returns_mtime_and_tags(self, tmp_path):
        """Test that get_metadata reads metadata file and returns mtime and tags."""
        posts_dir = tmp_path / "posts"
        article_dir = posts_dir / "test-article"
        article_dir.mkdir(parents=True)

        # Create metadata.json with tags
        metadata = {"tags": ["python", "testing", "unit"]}
        metadata_file = article_dir / "metadata.json"
        metadata_file.write_text(json.dumps(metadata))

        # Set a specific mtime
        os.utime(article_dir, (1000, 1000))

        result = indexer.get_metadata(str(article_dir))

        # Should return (mtime, tags) tuple
        assert len(result) == 2
        assert result[0] == 1000  # mtime should match
        assert result[1] == ",python,testing,unit,"  # tags formatted correctly

    def test_get_metadata_handles_empty_tags(self, tmp_path):
        """Test get_metadata when tags list is empty."""
        posts_dir = tmp_path / "posts"
        article_dir = posts_dir / "test-article"
        article_dir.mkdir(parents=True)

        # Create metadata.json with empty tags list
        metadata = {"tags": []}
        metadata_file = article_dir / "metadata.json"
        metadata_file.write_text(json.dumps(metadata))

        # Set a specific mtime
        os.utime(article_dir, (1000, 1000))

        result = indexer.get_metadata(str(article_dir))

        # Should return (mtime, tags) tuple with empty tags
        assert len(result) == 2
        assert result[0] == 1000  # mtime should match
        assert result[1] == ""  # tags should be empty string

    def test_get_metadata_handles_no_tags(self, tmp_path):
        """Test get_metadata when tags key is missing."""
        posts_dir = tmp_path / "posts"
        article_dir = posts_dir / "test-article"
        article_dir.mkdir(parents=True)

        # Create metadata.json without tags key
        metadata = {"title": "Test Article"}
        metadata_file = article_dir / "metadata.json"
        metadata_file.write_text(json.dumps(metadata))

        # Set a specific mtime
        os.utime(article_dir, (1000, 1000))

        result = indexer.get_metadata(str(article_dir))

        # Should return (mtime, tags) tuple with empty tags
        assert len(result) == 2
        assert result[0] == 1000  # mtime should match
        assert result[1] == ""  # tags should be empty string


class TestIndexChanges:
    """Test cases for the indexer.index_changes function."""

    @patch("centrum_blog.libs.indexer.is_article_exist_on_fs", return_value=False)
    @patch("centrum_blog.libs.indexer.get_db_session")
    def test_index_changes_deletes_article_when_deleted_in_git(
        self,
        mock_get_db_session,
        mock_is_article_exist_on_fs,
    ):
        """Test that index_changes deletes articles from database when they are deleted in git."""
        posts_path = Path("/tmp/posts")
        diff_index = [MagicMock()]
        diff_index[0].change_type = "D"  # Deleted
        diff_index[0].a_path = "posts/article-1/content.md"
        diff_index[0].b_path = None

        mock_session = MagicMock()
        mock_get_db_session.return_value.__enter__.return_value = mock_session

        indexer.index_changes(posts_path, diff_index)

        # Should delete from database
        mock_session.query.assert_called_once_with(BlogIndex)
        filter_call = mock_session.query().filter.call_args
        assert filter_call is not None
        assert filter_call.args[0].compare(BlogIndex.path == "article-1")
        mock_session.query().filter().delete.assert_called_once()

    @patch("centrum_blog.libs.indexer.is_article_exist_on_fs", return_value=True)
    @patch("centrum_blog.libs.indexer.get_db_session")
    def test_index_changes_skips_deletion_when_article_exists_on_fs(
        self,
        mock_get_db_session,
        mock_is_article_exist_on_fs,
    ):
        """Test that index_changes skips deletion when article still exists on filesystem."""
        posts_path = Path("/tmp/posts")
        diff_index = [MagicMock()]
        diff_index[0].change_type = "D"  # Deleted
        diff_index[0].a_path = "posts/article-1/content.md"
        diff_index[0].b_path = None

        mock_session = MagicMock()
        mock_get_db_session.return_value.__enter__.return_value = mock_session

        indexer.index_changes(posts_path, diff_index)

        # Should not delete from database since article exists on filesystem
        mock_session.query().filter().delete.assert_not_called()

    @patch("centrum_blog.libs.indexer.is_article_exist_on_fs", return_value=True)
    @patch("centrum_blog.libs.indexer.get_db_session")
    def test_index_changes_adds_new_article(
        self,
        mock_get_db_session,
        mock_is_article_exist_on_fs,
    ):
        """Test that index_changes adds new articles to database."""
        posts_path = Path("/tmp/posts")
        diff_index = [MagicMock()]
        diff_index[0].change_type = "A"  # Added
        diff_index[0].a_path = "posts/article-1/content.md"
        diff_index[0].b_path = "posts/article-1/content.md"

        # Mock the get_metadata function to return specific values
        with patch("centrum_blog.libs.indexer.get_metadata", return_value=(1000, ",python,testing,")):
            mock_session = MagicMock()
            mock_get_db_session.return_value.__enter__.return_value = mock_session

            mock_session.query.return_value.filter.return_value.scalar.return_value = 0

            indexer.index_changes(posts_path, diff_index)

            # Should add new blog entry to database with correct fields
            mock_session.add.assert_called_once()
            added_obj = mock_session.add.call_args[0][0]
            assert isinstance(added_obj, BlogIndex)
            assert added_obj.path == "article-1"
            assert added_obj.updated == datetime.fromtimestamp(1000)
            assert added_obj.tags == ",python,testing,"

    @patch("centrum_blog.libs.indexer.is_article_exist_on_fs", return_value=True)
    @patch("centrum_blog.libs.indexer.get_db_session")
    def test_index_changes_updates_existing_article(
        self,
        mock_get_db_session,
        mock_is_article_exist_on_fs,
    ):
        """Test that index_changes updates existing articles in database."""
        posts_path = Path("/tmp/posts")
        diff_index = [MagicMock()]
        diff_index[0].change_type = "M"  # Modified
        diff_index[0].a_path = "posts/article-1/content.md"
        diff_index[0].b_path = "posts/article-1/content.md"

        # Mock the get_metadata function to return specific values
        with patch("centrum_blog.libs.indexer.get_metadata", return_value=(1000, ",python,testing,")):
            mock_session = MagicMock()
            mock_get_db_session.return_value.__enter__.return_value = mock_session

            mock_session.query.return_value.filter.return_value.scalar.return_value = 1

            indexer.index_changes(posts_path, diff_index)

            # Should update existing blog entry in database with correct fields
            mock_session.query().filter().update.assert_called_once()
            update_args = mock_session.query().filter().update.call_args[0][0]
            assert update_args[BlogIndex.updated] == datetime.fromtimestamp(1000)
            assert update_args[BlogIndex.tags] == ",python,testing,"


class TestIndexAll:
    """Test cases for the indexer.index_all function."""

    @patch("centrum_blog.libs.indexer.get_db_session")
    def test_index_all_deletes_all_existing_entries_and_adds_new_ones(
        self,
        mock_get_db_session,
    ):
        """Test that index_all clears database and re-adds all entries."""
        posts_path = Path("/tmp/posts")

        # Mock directory listing to return two articles
        mock_entries = [
            MagicMock(),
            MagicMock()
        ]
        mock_entries[0].is_dir.return_value = True
        mock_entries[0].name = "article-1"
        mock_entries[1].is_dir.return_value = True
        mock_entries[1].name = "article-2"

        # Mock get_metadata to return values
        with patch("centrum_blog.libs.indexer.get_metadata", side_effect=[
            (1000, ",python,testing,"),
            (2000, ",javascript,web,")
        ]):
            mock_session = MagicMock()
            mock_get_db_session.return_value.__enter__.return_value = mock_session

            # Mock os.scandir to return our entries
            with patch("centrum_blog.libs.indexer.os.scandir") as mock_scandir:
                mock_scandir.return_value.__enter__.return_value = mock_entries

                indexer.index_all(posts_path)

                # Should delete all existing entries
                mock_session.query.assert_called_once_with(BlogIndex)
                mock_session.query().delete.assert_called_once()

                # Should add two new entries with correct fields
                assert mock_session.add.call_count == 2
                added_objs = [call[0][0] for call in mock_session.add.call_args_list]
                assert added_objs[0].path == "article-1"
                assert added_objs[0].updated == datetime.fromtimestamp(1000)
                assert added_objs[0].tags == ",python,testing,"
                assert added_objs[1].path == "article-2"
                assert added_objs[1].updated == datetime.fromtimestamp(2000)
                assert added_objs[1].tags == ",javascript,web,"

    @patch("centrum_blog.libs.indexer.get_db_session")
    def test_index_all_handles_directory_with_no_articles(
        self,
        mock_get_db_session,
    ):
        """Test that index_all works correctly when there are no articles."""
        posts_path = Path("/tmp/posts")

        # Mock directory listing to return no entries
        mock_entries = []

        # Mock os.scandir to return our entries
        with patch("centrum_blog.libs.indexer.os.scandir") as mock_scandir:
            mock_scandir.return_value.__enter__.return_value = mock_entries

            mock_session = MagicMock()
            mock_get_db_session.return_value.__enter__.return_value = mock_session

            indexer.index_all(posts_path)

            # Should delete all existing entries but add none
            mock_session.query.assert_called_once_with(BlogIndex)
            mock_session.query().delete.assert_called_once()
            mock_session.add.assert_not_called()
