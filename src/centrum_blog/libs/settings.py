from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=('.env'))

    log_level: str = "INFO"

    db_user: str = "ADMIN"                                                                                              
    db_connection_string: str = ""                                                                                      
    db_secret_ocid: str = ""

    git_repo_url: str
    git_username: str
    git_password: str

    webhook_secret_ocid: str = ""


settings = Settings()
