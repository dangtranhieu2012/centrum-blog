from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=('.env'))

    log_level: str = "INFO"

    template: str = "typo"

    db_user: str = "ADMIN"
    db_connection_string: str = ""
    db_secret: Optional[str] = None
    db_secret_ocid: Optional[str] = None

    git_repo_url: str = ""
    git_username: Optional[str] = None
    git_password: Optional[str] = None
    git_username_secret_ocid: Optional[str] = None
    git_password_secret_ocid: Optional[str] = None

    webhook_secret: Optional[str] = None
    webhook_secret_ocid: Optional[str] = None


settings = Settings()
