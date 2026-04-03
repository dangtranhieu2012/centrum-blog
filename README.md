# Centrum Blog

A simple markdown-based git-triggered blog platform with support for multiple database backends (Oracle, PostgreSQL,
MySQL, SQLite,...).

## Installation

### Prerequisites

- Python 3.12 or higher
- [`uv`](https://docs.astral.sh/uv/) package manager

### Setup Steps

1. **Clone the repository:**

   ```bash
   git clone https://github.com/dangtranhieu2012/centrum-blog.git
   cd centrum-blog
   ```

2. **Install dependencies with uv:**

   ```bash
   uv sync
   ```

   This will create a virtual environment and install all dependencies from `pyproject.toml`.

3. **Create a `.env` file** for configuration:

   See the Configuration section below for all available options.

## Configuration

Configuration is managed through environment variables in the `.env` file, which are loaded by Pydantic. Edit
`src/centrum_blog/libs/settings.py` to add or modify configuration options.

### Available Settings

| Variable                   | Type   | Default           | Description                                                   |
| -------------------------- | ------ | ----------------- | ------------------------------------------------------------- |
| `log_level`                | string | `INFO`            | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`)           |
| `template`                 | string | `typo`            | Template directory to use                                     |
| `db_user`                  | string | `ADMIN`           | Database username                                             |
| `db_dialect_driver`        | string | `oracle+oracledb` | SQLAlchemy database dialect+driver                            |
| `db_connection_string`     | string | _(required)_      | Database connection URL or TNS descriptor                     |
| `db_secret`                | string | _optional_        | Plain text database password (not recommended for production) |
| `db_secret_ocid`           | string | _optional_        | OCI Vault secret OCID for database password                   |
| `git_repo_url`             | string | _(required)_      | Git repository URL for blog content                           |
| `git_username`             | string | _optional_        | Git username                                                  |
| `git_password`             | string | _optional_        | Git password (plain text, not recommended)                    |
| `git_username_secret_ocid` | string | _optional_        | OCI Vault secret OCID for Git username                        |
| `git_password_secret_ocid` | string | _optional_        | OCI Vault secret OCID for Git password                        |
| `webhook_secret`           | string | _optional_        | Plain text webhook secret                                     |
| `webhook_secret_ocid`      | string | _optional_        | OCI Vault secret OCID for webhook secret                      |

### Example `.env` Configuration

```bash
# Logging
log_level=INFO
template=typo

# Database (Oracle Cloud example)
db_user=ADMIN
db_dialect_driver=oracle+oracledb
db_connection_string="(description=(retry_count=20)(retry_delay=3)(address=(protocol=tcps)(port=1521)(host=adb.region.oraclecloud.com))(connect_data=(service_name=your_service_name.adb.oraclecloud.com))(security=(ssl_server_dn_match=yes)))"
db_secret_ocid=ocid1.vaultsecret.oc1.region.aaaaa...

# Git Repository
git_repo_url=https://github.com/username/blog-content.git
git_password_secret_ocid=ocid1.vaultsecret.oc1.region.aaaaa...

# Webhook
webhook_secret_ocid=ocid1.vaultsecret.oc1.region.aaaaa...
```

### Database Configuration

#### Oracle Cloud Autonomous Database

1. **Download the Wallet:**
   - Go to Oracle Cloud Console → Autonomous Database instance
   - Click "Database Connections" → "Download Wallet"
   - Extract the wallet ZIP to a safe directory

2. **Set TNS_ADMIN:**

   ```bash
   export TNS_ADMIN=/path/to/wallet/directory
   ```

3. **Configure `.env`:**

   ```bash
   db_connection_string="(full TNS descriptor from tnsnames.ora)"
   db_secret_ocid="your OCI vault secret OCID"
   ```

4. **For Local Development with OCI:** Set the `OCI_USER_PROFILE` environment variable to match your local profile:

   ```bash
   export OCI_USER_PROFILE=DEFAULT
   # or use a specific profile name:
   export OCI_USER_PROFILE=my-profile-name
   ```

   The profile must exist in `~/.oci/config`.

5. **Alternative Database Backends:** Change `db_dialect_driver` to use different databases:
   - **PostgreSQL**: `postgresql://user:pass@localhost:5432/dbname`
   - **MySQL**: `mysql+pymysql://user:pass@localhost:3306/dbname`
   - **SQLite**: `sqlite:///./blog.db`

## Running the Application

### Development Server

Start the Flask development server:

```bash
uv run flask --app src.centrum_blog run
```

The blog will be available at `http://localhost:5000`

### Production Server

Use the Waitress WSGI server for production:

```bash
uv run waitress-serve --port 8080 src.centrum_blog:app
```

## Features

- **Markdown-based content:** Write blog posts in Markdown
- **Git-triggered:** Automatically indexes new posts from a Git repository
- **Multi-database support:** Works with Oracle, PostgreSQL, MySQL, SQLite via SQLAlchemy ORM
- **Webhook support:** Automatic reindexing on Git pushes
- **Responsive design:** Mobile-friendly Bulma CSS framework
- **Code highlighting:** Syntax highlighting with Pygments

## Project Structure

```
centrum-blog/
├── src/centrum_blog/
│   ├── __init__.py              # Flask app & routes
│   ├── constants.py             # Application constants
│   ├── templates/typo/          # HTML templates
│   ├── static/                  # CSS, images, etc.
│   └── libs/
│       ├── settings.py          # Configuration management
│       ├── db.py                # SQLAlchemy database setup
│       ├── models.py            # SQLAlchemy ORM models
│       ├── article.py           # Article/blog logic
│       ├── indexer.py           # Git indexing logic
│       └── oci_helper/          # OCI integration
├── pyproject.toml               # Project dependencies
├── .env                         # Environment configuration
└── README.md                    # This file
```

## Database Schema

The application uses a single `blog_index` table:

| Column    | Type                     | Description                       |
| --------- | ------------------------ | --------------------------------- |
| `id`      | INTEGER (auto-increment) | Primary key                       |
| `path`    | VARCHAR(256)             | Blog post directory name (unique) |
| `updated` | TIMESTAMP(6)             | Last modified timestamp           |
| `tags`    | VARCHAR(4000)            | Comma-separated tags              |

## Troubleshooting

### Oracle Connection Issues

1. **"ORA-12514: TNS:listener could not resolve"**
   - Verify `TNS_ADMIN` is set correctly
   - Check wallet files exist in the directory
   - Verify `db_connection_string` matches your service name

2. **"OCI Profile not found"**
   - Ensure `OCI_USER_PROFILE` environment variable is set
   - Verify the profile exists in `~/.oci/config`
   - Run `oci session authenticate --profile-name <profile>`

3. **"SSL verification failed"**
   - Download the latest Oracle Cloud wallet
   - Ensure `ssl_server_dn_match=yes` in the TNS descriptor (already in default)

### Database Errors

1. Switch to a simpler database for testing (SQLite):
   ```bash
   db_dialect_driver=sqlite
   db_connection_string=sqlite:///./blog.db
   ```

## License

Licensed under the MIT License. See LICENSE file for details.

## Contributing

Pull requests are welcome. For major changes, please open an issue first.
