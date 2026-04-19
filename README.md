# Centrum Blog

A simple markdown-based git-triggered blog platform with support for multiple database backends (Oracle, PostgreSQL,
MySQL, SQLite,...).

## Installation

### Prerequisites

- Python 3.12 or higher
- [`uv`](https://docs.astral.sh/uv/) package manager
- Git with [LFS (Large File Storage)](https://git-lfs.com/) extension installed

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

| Variable                   | Type   | Default      | Description                                                                                                                                                       |
| -------------------------- | ------ | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `log_level`                | string | `INFO`       | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`)                                                                                                               |
| `template`                 | string | `typo`       | Template directory to use                                                                                                                                         |
| `static_content_path`      | string | `content`    | Path to the directory where the content repository is going to be downloaded relative to the root of the project                                                  |
| `db_user`                  | string | _optional_   | Database username                                                                                                                                                 |
| `db_connection_string`     | string | _(required)_ | Full SQLAlchemy URL including dialect+driver, host, and service name; should NOT include username/password (added via `db_user` and `db_secret`/`db_secret_ocid`) |
| `db_secret`                | string | _optional_   | Plain text database password (not recommended for production)                                                                                                     |
| `db_secret_ocid`           | string | _optional_   | OCI Vault secret OCID for database password                                                                                                                       |
| `git_repo_url`             | string | _(required)_ | Git repository URL for blog content                                                                                                                               |
| `git_username`             | string | _optional_   | Git username                                                                                                                                                      |
| `git_password`             | string | _optional_   | Git password (plain text, not recommended)                                                                                                                        |
| `git_username_secret_ocid` | string | _optional_   | OCI Vault secret OCID for Git username                                                                                                                            |
| `git_password_secret_ocid` | string | _optional_   | OCI Vault secret OCID for Git password                                                                                                                            |
| `webhook_secret`           | string | _optional_   | Plain text webhook secret                                                                                                                                         |
| `webhook_secret_ocid`      | string | _optional_   | OCI Vault secret OCID for webhook secret                                                                                                                          |

### Example `.env` Configuration

```bash
# Logging
log_level=INFO
template=typo

# Database (Oracle Cloud example)
db_user=ADMIN
# db_connection_string must be the full SQLAlchemy URL with dialect+driver prefix, excluding username/password
# Username/password are read from db_user and db_secret/db_secret_ocid
 db_connection_string="oracle+oracledb://adb.region.oraclecloud.com:1521/your_service_name?ssl_server_dn_match=yes"
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

5. **Alternative Database Backends:** Provide a full SQLAlchemy URL via `db_connection_string`; credentials are supplied
   by `db_user` and `db_secret`/`db_secret_ocid`:
   - **PostgreSQL**: `postgresql://localhost:5432/dbname`
   - **MySQL**: `mysql+pymysql://localhost:3306/dbname`
   - **SQLite**: `sqlite:///blog.db`

## Running the Application

### Development Server

Start the Flask development server:

```bash
uv run flask --app src.centrum_blog run --reload
```

The blog will be available at `http://localhost:5000`

### Production Server

Use the Waitress WSGI server for production:

```bash
uv run waitress-serve --port 8080 src.centrum_blog:app
```

## Content Management

### Force Reindex Content Repository

To forcefully reclone the content repository and rebuild all indexes from scratch, run:

```bash
uv run src/centrum_blog/rebuild_index.py
```

This command will:

- Remove the existing cloned content repository
- Clone the content repository fresh from the configured Git URL
- Rebuild the blog index database with all posts

Use this when you need to ensure the blog content is completely synchronized or when troubleshooting indexing issues.

## Testing

The project includes unit tests that can be run with:

```bash
uv run pytest
```

To run tests with development dependencies:

```bash
uv run --dev pytest
```

## Webhook Configuration

The application supports automatic content synchronization through GitHub webhooks. When configured, the blog will
automatically reindex content whenever changes are pushed to the content repository.

### Setting up GitHub Webhooks

1. **Go to your content repository on GitHub**
   - Navigate to your GitHub repository containing the blog content
   - Click on "Settings" tab
   - Click on "Webhooks" in the left sidebar
   - Click "Add webhook"

2. **Configure the webhook:**
   - **Payload URL**: `https://your-blog-domain.com/reindex`
     - Replace `your-blog-domain.com` with your actual domain
     - For local development, you can use tools like ngrok to expose your local server
   - **Content type**: `application/json`
   - **Secret**: Enter the same secret configured in your `.env` file as `webhook_secret` or `webhook_secret_ocid`
   - **Which events would you like to trigger this webhook?**: Select "Just the push event"
   - **Active**: Ensure this is checked

3. **Save the webhook**

### Security Notes

- The webhook endpoint uses HMAC-SHA256 signature verification for security
- Only push events are processed; other event types are ignored
- The webhook secret must match the one configured in your application settings

## Features

- **Markdown-based content:** Write blog posts in Markdown
- **Git-triggered:** Automatically indexes new posts from a Git repository
- **Multi-database support:** Works with Oracle, PostgreSQL, MySQL, SQLite via SQLAlchemy ORM
- **Webhook support:** Automatic reindexing on Git pushes
- **Responsive design:** Mobile-friendly Bulma CSS framework
- **Code highlighting:** Syntax highlighting with Pygments

## Content Repository Structure

The blog content is stored in a separate Git repository and automatically indexed by the application. The content
repository should follow this structure:

```
content/
├── about.md                    # About page content (optional)
├── posts/
│   ├── <post-slug>/
│   │   ├── content.md          # Markdown content of the blog post
│   │   ├── metadata.json       # Post metadata (title, tags, author, summary)
│   │   └── <image-files>       # Images used in the blog post
│   └── <another-post-slug>/
│       ├── content.md
│       ├── metadata.json
│       └── <image-files>
├── authors/
│   └── <author-email>/
│       └── metadata.json       # Author information (name, avatar)
└── images/
    └── <image-files>           # Author avatars and other images
```

### Post Structure

Each blog post resides in its own directory under `posts/`, where the directory name serves as the URL slug for the
post.

- **`content.md`**: Contains the full Markdown content of the article. HTML can be mixed with Markdown syntax, and the
  HTML content will not be escaped, allowing for custom styling and layouts.
- **`metadata.json`**: Contains post metadata in JSON format:

  ```json
  {
    "title": "Post Title",
    "tags": ["tag1", "tag2"],
    "author": "author@example.com",
    "summary": "Brief description of the post"
  }
  ```

- **`<image-files>`**: Any images referenced in the blog post should be stored within the post folder itself.

### Author Structure

Author information is stored under `authors/<author-email>/`:

- **`metadata.json`**: Contains author details:
  ```json
  {
    "name": "Author Name",
    "avatar": "avatar-filename.png"
  }
  ```

Author avatars are stored in the `images/` directory and referenced by filename in the author's metadata.

### About Page

The blog includes an optional about page that can be customized by adding an `about.md` file at the root of the content
repository. This file should contain Markdown content that will be rendered and displayed on the `/about` route.

The `about.md` file should contain the complete HTML structure for the article content, including any images, styling,
and layout elements. You can mix Markdown syntax with HTML tags as needed. HTML content will not be escaped, allowing
for custom styling and layouts.

**Note:** Since the about page is not a blog post, any resources (such as images, videos, or other media files)
referenced in the `about.md` file should be stored appropriately within the content repository. For example, images are
typically stored in the `images/` folder at the root of the content repository, while other resource types may be better
suited to different locations based on your organizational preferences.

Example `about.md` content:

```markdown
<div class="media-left">
  <figure class="image is-128x128">
    <img src="/static/content/images/your-avatar.png" alt="Author Avatar" class="is-rounded" />
  </figure>
</div>
<div class="media-content">
  <h1 class="title is-italic-title">About Me</h1>

Write your about page content here using Markdown. You can include **bold text**, _italic text_,
[links](https://example.com), and any HTML elements you need.

</div>
```

If the `about.md` file is not present, the about page will display a fallback message indicating that the content is not
available.

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
   db_connection_string=sqlite:///blog.db
   ```

## License

Licensed under the MIT License. See LICENSE file for details.

## Contributing

Pull requests are welcome. For major changes, please open an issue first.
