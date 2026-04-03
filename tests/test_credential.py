from unittest.mock import patch

from centrum_blog.libs.credential import get_authenticated_git_url, get_secret


class TestGetAuthenticatedGitUrl:
    """Test cases for get_authenticated_git_url function"""

    @patch('centrum_blog.libs.credential.get_secret')
    @patch('centrum_blog.libs.credential.settings')
    def test_http_url_with_credentials(self, mock_settings, mock_get_secret):
        """Test HTTP URL with username and password"""

        mock_get_secret.side_effect = ["username", "password"]

        url = "https://github.com/user/repo.git"
        result = get_authenticated_git_url(url)

        expected = "https://username:password@github.com/user/repo.git"
        assert result == expected
        assert mock_get_secret.call_count == 2

    @patch('centrum_blog.libs.credential.get_secret')
    @patch('centrum_blog.libs.credential.settings')
    def test_https_url_with_credentials(self, mock_settings, mock_get_secret):
        """Test HTTPS URL with username and password"""
        mock_get_secret.side_effect = ["user", "pass123"]

        url = "https://gitlab.com/group/project.git"
        result = get_authenticated_git_url(url)

        expected = "https://user:pass123@gitlab.com/group/project.git"
        assert result == expected

    @patch('centrum_blog.libs.credential.get_secret')
    @patch('centrum_blog.libs.credential.settings')
    def test_http_url_with_username_only(self, mock_settings, mock_get_secret):
        """Test HTTP URL with username but empty password"""
        mock_get_secret.side_effect = ["username", ""]

        url = "https://github.com/user/repo.git"
        result = get_authenticated_git_url(url)

        expected = "https://username@github.com/user/repo.git"
        assert result == expected

    @patch('centrum_blog.libs.credential.get_secret')
    @patch('centrum_blog.libs.credential.settings')
    def test_http_url_with_password_only(self, mock_settings, mock_get_secret):
        """Test HTTP URL with password but no username"""
        mock_get_secret.side_effect = ["", "password"]

        url = "https://github.com/user/repo.git"
        result = get_authenticated_git_url(url)

        expected = "https://password@github.com/user/repo.git"
        assert result == expected

    @patch('centrum_blog.libs.credential.get_secret')
    @patch('centrum_blog.libs.credential.settings')
    def test_http_url_no_credentials(self, mock_settings, mock_get_secret):
        """Test HTTP URL with no credentials available"""
        mock_get_secret.side_effect = ["", ""]

        url = "https://github.com/user/repo.git"
        result = get_authenticated_git_url(url)

        assert result == url  # Should return original URL

    @patch('centrum_blog.libs.credential.get_secret')
    @patch('centrum_blog.libs.credential.settings')
    def test_ssh_url_unchanged(self, mock_settings, mock_get_secret):
        """Test SSH URL remains unchanged"""
        url = "git@github.com:user/repo.git"
        result = get_authenticated_git_url(url)

        assert result == url
        mock_get_secret.assert_not_called()

    @patch('centrum_blog.libs.credential.get_secret')
    @patch('centrum_blog.libs.credential.settings')
    def test_git_url_unchanged(self, mock_settings, mock_get_secret):
        """Test git:// URL remains unchanged"""
        url = "git://github.com/user/repo.git"
        result = get_authenticated_git_url(url)

        assert result == url
        mock_get_secret.assert_not_called()

    @patch('centrum_blog.libs.credential.get_secret')
    @patch('centrum_blog.libs.credential.settings')
    def test_special_characters_in_credentials(self, mock_settings, mock_get_secret):
        """Test URL encoding of special characters in credentials"""
        mock_get_secret.side_effect = ["user@domain.com", "pass:word@123"]

        url = "https://example.com/repo.git"
        result = get_authenticated_git_url(url)

        # Check that special characters are URL-encoded
        expected = "https://user%40domain.com:pass%3Aword%40123@example.com/repo.git"
        assert result == expected

    @patch('centrum_blog.libs.credential.get_secret')
    @patch('centrum_blog.libs.credential.settings')
    def test_empty_credentials(self, mock_settings, mock_get_secret):
        """Test with empty credentials"""
        mock_get_secret.side_effect = [None, None]

        url = "https://github.com/user/repo.git"
        result = get_authenticated_git_url(url)

        assert result == url
        assert mock_get_secret.call_count == 2

    @patch('centrum_blog.libs.credential.get_secret')
    @patch('centrum_blog.libs.credential.settings')
    def test_url_with_port(self, mock_settings, mock_get_secret):
        """Test URL with custom port"""
        mock_get_secret.side_effect = ["user", "pass"]

        url = "https://example.com:8080/repo.git"
        result = get_authenticated_git_url(url)

        expected = "https://user:pass@example.com:8080/repo.git"
        assert result == expected

    @patch('centrum_blog.libs.credential.get_secret')
    @patch('centrum_blog.libs.credential.settings')
    def test_url_with_query_params(self, mock_settings, mock_get_secret):
        """Test URL with query parameters"""
        mock_get_secret.side_effect = ["user", "pass"]

        url = "https://github.com/user/repo.git?ref=main"
        result = get_authenticated_git_url(url)

        expected = "https://user:pass@github.com/user/repo.git?ref=main"
        assert result == expected

    @patch('centrum_blog.libs.credential.get_secret')
    @patch('centrum_blog.libs.credential.settings')
    def test_url_with_fragment(self, mock_settings, mock_get_secret):
        """Test URL with fragment"""
        mock_get_secret.side_effect = ["user", "pass"]

        url = "https://github.com/user/repo.git#readme"
        result = get_authenticated_git_url(url)

        expected = "https://user:pass@github.com/user/repo.git#readme"
        assert result == expected


class TestGetSecret:
    """Test cases for get_secret function"""

    def test_get_secret_with_plain_text(self):
        """Test get_secret with plain text secret"""
        result = get_secret('plain_text_secret')
        assert result == 'plain_text_secret'

    @patch('centrum_blog.libs.credential.vault.get_secret')
    def test_get_secret_with_ocid(self, mock_vault_get_secret):
        """Test get_secret with OCID"""
        mock_vault_get_secret.return_value = 'vault_secret'
        result = get_secret(None, 'test_ocid')
        mock_vault_get_secret.assert_called_once_with('test_ocid')
        assert result == 'vault_secret'

    def test_get_secret_with_none(self):
        """Test get_secret with no arguments"""
        result = get_secret()
        assert result == ''

    @patch('centrum_blog.libs.credential.vault.get_secret')
    def test_get_secret_with_both(self, mock_vault_get_secret):
        """Test get_secret with both secret and OCID - secret should take precedence"""
        result = get_secret('plain_secret', 'test_ocid')
        # vault.get_secret should not be called since secret is provided
        mock_vault_get_secret.assert_not_called()
        assert result == 'plain_secret'

    @patch('centrum_blog.libs.credential.vault.get_secret')
    def test_get_secret_with_ocid_none_secret(self, mock_vault_get_secret):
        """Test get_secret with None secret and OCID"""
        mock_vault_get_secret.return_value = 'vault_secret'
        result = get_secret(None, 'test_ocid')
        mock_vault_get_secret.assert_called_once_with('test_ocid')
        assert result == 'vault_secret'
