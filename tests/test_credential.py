from unittest.mock import patch

from centrum_blog.libs.credential import construct_authenticated_url, get_authenticated_git_url, get_secret


class TestGetAuthenticatedGitUrl:
    """Test cases for get_authenticated_git_url function"""

    @patch("centrum_blog.libs.credential.construct_authenticated_url")
    @patch("centrum_blog.libs.credential.get_secret")
    def test_http_scheme_fetches_credentials(self, mock_get_secret, mock_construct):
        """Test HTTP(S) URLs fetch credentials and pass to construct function"""
        mock_get_secret.side_effect = ["username", "password"]
        mock_construct.return_value = "https://username:password@github.com/user/repo.git"

        url = "https://github.com/user/repo.git"
        result = get_authenticated_git_url(url)

        assert result == "https://username:password@github.com/user/repo.git"
        assert mock_get_secret.call_count == 2
        mock_construct.assert_called_once_with(url, "username", "password")

    @patch("centrum_blog.libs.credential.get_secret")
    def test_non_http_scheme_returns_unchanged(self, mock_get_secret):
        """Test non-HTTP(S) URLs return unchanged without fetching credentials"""
        ssh_url = "git@github.com:user/repo.git"
        result = get_authenticated_git_url(ssh_url)
        assert result == ssh_url
        mock_get_secret.assert_not_called()

        git_url = "git://github.com/user/repo.git"
        result = get_authenticated_git_url(git_url)
        assert result == git_url


class TestConstructAuthenticatedUrl:
    """Test cases for construct_authenticated_url function"""

    def test_https_git_url_with_credentials(self):
        """Test HTTPS Git URL with username and password"""
        url = "https://github.com/user/repo.git"
        result = construct_authenticated_url(url, "myuser", "mypass")

        expected = "https://myuser:mypass@github.com/user/repo.git"
        assert result == expected

    def test_http_url_with_credentials(self):
        """Test HTTP URL with credentials"""
        url = "http://example.com/path"
        result = construct_authenticated_url(url, "admin", "secret123")

        expected = "http://admin:secret123@example.com/path"
        assert result == expected

    def test_username_only(self):
        """Test URL with username but no password"""
        url = "https://gitlab.com/project.git"
        result = construct_authenticated_url(url, "developer", None)

        expected = "https://developer@gitlab.com/project.git"
        assert result == expected

    def test_password_only(self):
        """Test URL with password but no username"""
        url = "https://gitlab.com/project.git"
        result = construct_authenticated_url(url, None, "token123")

        expected = "https://token123@gitlab.com/project.git"
        assert result == expected

    def test_no_credentials(self):
        """Test URL without credentials returns original URL"""
        url = "https://github.com/user/repo.git"
        result = construct_authenticated_url(url, None, None)

        assert result == url

    def test_empty_string_credentials(self):
        """Test URL with empty string credentials"""
        url = "https://github.com/user/repo.git"
        result = construct_authenticated_url(url, "", "")

        assert result == url

    def test_special_characters_in_username(self):
        """Test URL encoding of special characters in username"""
        url = "https://example.com/repo.git"
        result = construct_authenticated_url(url, "user@domain.com", "pass")

        expected = "https://user%40domain.com:pass@example.com/repo.git"
        assert result == expected

    def test_special_characters_in_password(self):
        """Test URL encoding of special characters in password"""
        url = "https://example.com/repo.git"
        result = construct_authenticated_url(url, "user", "pass:word@123")

        expected = "https://user:pass%3Aword%40123@example.com/repo.git"
        assert result == expected

    def test_special_characters_in_both(self):
        """Test URL encoding of special characters in both username and password"""
        url = "https://example.com/repo.git"
        result = construct_authenticated_url(url, "user@domain.com", "pass:word@123")

        expected = "https://user%40domain.com:pass%3Aword%40123@example.com/repo.git"
        assert result == expected

    def test_url_with_port(self):
        """Test URL with custom port"""
        url = "https://example.com:8443/repo.git"
        result = construct_authenticated_url(url, "admin", "pass")

        expected = "https://admin:pass@example.com:8443/repo.git"
        assert result == expected

    def test_url_with_path(self):
        """Test URL with complex path"""
        url = "https://example.com/path/to/repo.git"
        result = construct_authenticated_url(url, "user", "pass")

        expected = "https://user:pass@example.com/path/to/repo.git"
        assert result == expected

    def test_url_with_query_params(self):
        """Test URL with query parameters"""
        url = "https://example.com/repo.git?ref=main&version=1"
        result = construct_authenticated_url(url, "user", "pass")

        expected = "https://user:pass@example.com/repo.git?ref=main&version=1"
        assert result == expected

    def test_url_with_fragment(self):
        """Test URL with fragment"""
        url = "https://example.com/repo.git#section"
        result = construct_authenticated_url(url, "user", "pass")

        expected = "https://user:pass@example.com/repo.git#section"
        assert result == expected

    def test_sqlalchemy_oracle_url(self):
        """Test SQLAlchemy Oracle database URL"""
        url = "oracle+oracledb://host:1521/service"
        result = construct_authenticated_url(url, "dba_user", "dba_pass")

        expected = "oracle+oracledb://dba_user:dba_pass@host:1521/service"
        assert result == expected

    def test_sqlalchemy_postgresql_url(self):
        """Test SQLAlchemy PostgreSQL database URL"""
        url = "postgresql://localhost:5432/mydb"
        result = construct_authenticated_url(url, "postgres", "pgpass123")

        expected = "postgresql://postgres:pgpass123@localhost:5432/mydb"
        assert result == expected

    def test_sqlalchemy_mysql_url(self):
        """Test SQLAlchemy MySQL database URL"""
        url = "mysql+pymysql://localhost/mydb"
        result = construct_authenticated_url(url, "root", "mysql_pass")

        expected = "mysql+pymysql://root:mysql_pass@localhost/mydb"
        assert result == expected

    def test_sqlalchemy_sqlite_url(self):
        """Test SQLAlchemy SQLite URL is preserved as-is."""
        url = "sqlite:///path/to/database.db"
        result = construct_authenticated_url(url, "user", "pass")

        expected = "sqlite:///path/to/database.db"
        assert result == expected

    def test_url_with_existing_credentials_are_replaced(self):
        """Test that existing credentials in URL are properly replaced"""
        url = "https://olduser:oldpass@example.com/repo.git"
        result = construct_authenticated_url(url, "newuser", "newpass")

        # Old credentials should be replaced with new ones
        expected = "https://newuser:newpass@example.com/repo.git"
        assert result == expected

    def test_url_with_port_and_credentials(self):
        """Test URL with both port and credentials"""
        url = "oracle+oracledb://db.example.com:1521/ORCL"
        result = construct_authenticated_url(url, "admin", "admin123")

        expected = "oracle+oracledb://admin:admin123@db.example.com:1521/ORCL"
        assert result == expected

    def test_complex_password_with_special_chars(self):
        """Test password with multiple special characters"""
        url = "https://example.com/repo"
        result = construct_authenticated_url(url, "user", "p@ss:w=rd/123?test#anchor")

        expected = "https://user:p%40ss%3Aw%3Drd%2F123%3Ftest%23anchor@example.com/repo"
        assert result == expected


class TestGetSecret:
    """Test cases for get_secret function"""

    def test_get_secret_with_plain_text(self):
        """Test get_secret with plain text secret"""
        result = get_secret("plain_text_secret")
        assert result == "plain_text_secret"

    @patch("centrum_blog.libs.credential.vault.get_secret")
    def test_get_secret_with_ocid(self, mock_vault_get_secret):
        """Test get_secret with OCID"""
        mock_vault_get_secret.return_value = "vault_secret"
        result = get_secret(None, "test_ocid")
        mock_vault_get_secret.assert_called_once_with("test_ocid")
        assert result == "vault_secret"

    def test_get_secret_with_none(self):
        """Test get_secret with no arguments"""
        result = get_secret()
        assert result == ""

    @patch("centrum_blog.libs.credential.vault.get_secret")
    def test_get_secret_with_both(self, mock_vault_get_secret):
        """Test get_secret with both secret and OCID - secret should take precedence"""
        result = get_secret("plain_secret", "test_ocid")
        # vault.get_secret should not be called since secret is provided
        mock_vault_get_secret.assert_not_called()
        assert result == "plain_secret"

    @patch("centrum_blog.libs.credential.vault.get_secret")
    def test_get_secret_with_ocid_none_secret(self, mock_vault_get_secret):
        """Test get_secret with None secret and OCID"""
        mock_vault_get_secret.return_value = "vault_secret"
        result = get_secret(None, "test_ocid")
        mock_vault_get_secret.assert_called_once_with("test_ocid")
        assert result == "vault_secret"
