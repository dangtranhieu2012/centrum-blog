from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env"))

    log_level: str = "INFO"

    template: str = "typo"
    static_content_path: str = "content"

    db_user: str | None = None
    db_connection_string: str = ""
    db_secret: str | None = None
    db_secret_ocid: str | None = None

    git_repo_url: str = ""
    git_username: str | None = None
    git_password: str | None = None
    git_username_secret_ocid: str | None = None
    git_password_secret_ocid: str | None = None

    webhook_secret: str | None = None
    webhook_secret_ocid: str | None = None


settings = Settings()
