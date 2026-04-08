import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import sessionmaker
from centrum_blog.libs import db

class TestDb:
    """Test cases for db.py functions."""

    def setup_method(self):
        """Reset singleton globals before each test to prevent leakage."""
        db._engine = None
        db._sessionmaker = None

    def teardown_method(self):
        """Reset singleton globals after each test to prevent leakage."""
        db._engine = None
        db._sessionmaker = None

    @patch('centrum_blog.libs.credential.construct_authenticated_url')
    @patch('centrum_blog.libs.credential.get_secret')
    @patch('centrum_blog.libs.settings.settings.db_secret', new='some_secret')
    @patch('centrum_blog.libs.settings.settings.db_secret_ocid', new='some_ocid')
    @patch('centrum_blog.libs.settings.settings.db_connection_string', new='oracle://conn_str')
    @patch('centrum_blog.libs.settings.settings.db_user', new='some_user')
    def test__get_sqlalchemy_url(
        self,
        mock_get_secret,
        mock_construct_url
    ):
        """Test that the SQLAlchemy URL is constructed correctly."""
        # Setup mocks
        mock_get_secret.return_value = "some_secret"
        mock_construct_url.return_value = "oracle://user:password@host:port/service"

        result = db._get_sqlalchemy_url()

        assert result == "oracle://user:password@host:port/service"
        mock_get_secret.assert_called_once_with('some_secret', 'some_ocid')
        mock_construct_url.assert_called_once_with(
            'oracle://conn_str',
            'some_user',
            "some_secret"
        )

    @patch('centrum_blog.libs.settings.settings.db_connection_string', new='sqlite:///./blog.db')
    def test__get_sqlalchemy_url_sqlite(self):
        """Test that SQLite URLs are used directly without credential injection."""
        result = db._get_sqlalchemy_url()
        assert result == 'sqlite:///./blog.db'

    @patch('centrum_blog.libs.db.create_engine')
    @patch('centrum_blog.libs.db._get_sqlalchemy_url')
    def test_get_engine(self, mock_get_url, mock_create_engine):
        """Test get_engine returns the engine and implements singleton pattern."""
        mock_url = "oracle://connection_string"
        mock_get_url.return_value = mock_url
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        # First call
        engine1 = db.get_engine()
        assert engine1 == mock_engine
        mock_create_engine.assert_called_once_with(mock_url, echo=False, pool_pre_ping=True)

        # Second call (should return same instance)
        engine2 = db.get_engine()
        assert engine2 == mock_engine
        assert mock_create_engine.call_count == 1

    @patch('centrum_blog.libs.db.get_engine')
    @patch('centrum_blog.libs.db.sessionmaker')
    def test_get_sessionmaker(self, mock_sessionmaker, mock_get_engine):
        """Test get_sessionmaker returns the sessionmaker and implements singleton pattern."""
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        mock_sm = MagicMock()
        mock_sessionmaker.return_value = mock_sm

        # First call
        sm1 = db.get_sessionmaker()
        assert sm1 == mock_sm
        mock_sessionmaker.assert_called_once_with(autocommit=False, autoflush=False, bind=mock_engine)

        # Second call (should return same instance)
        sm2 = db.get_sessionmaker()
        assert sm2 == mock_sm
        assert mock_sessionmaker.call_count == 1

    @patch('centrum_blog.libs.db.get_sessionmaker')
    def test_get_db_session_success(self, mock_get_sessionmaker):
        """Test get_db_session success path: commit and close."""
        mock_sm = MagicMock()
        mock_session = MagicMock()
        mock_get_sessionmaker.return_value = mock_sm
        mock_sm.return_value = mock_session

        with db.get_db_session() as session:
            assert session == mock_session
            # Verify we are inside the context manager

        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

    @patch('centrum_blog.libs.db.get_sessionmaker')
    def test_get_db_session_error(self, mock_get_sessionmaker):
        """Test get_db_session error path: rollback and close."""
        mock_sm = MagicMock()
        mock_session = MagicMock()
        mock_get_sessionmaker.return_value = mock_sm
        mock_sm.return_value = mock_session

        with pytest.raises(Exception) as excinfo:
            with db.get_db_session() as session:
                raise ValueError("Database error")

        assert str(excinfo.value) == "Database error"
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()
