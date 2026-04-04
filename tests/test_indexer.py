from pathlib import Path
from unittest.mock import MagicMock, patch

from git.exc import NoSuchPathError

from centrum_blog.libs import indexer


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
