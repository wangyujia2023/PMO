from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    mysql_host: str = "10.26.20.3"
    mysql_port: int = 23336
    mysql_user: str = "root"
    mysql_password: str = "123456"
    mysql_database: str = "pmo"
    gemini_api_key: str = "AIzaSyCkhCf407B7zCL_fzg6eTpKH3UMDlSz4QM"
    gemini_model: str = "gemini-2.5-flash"
    cors_origins: str = "http://localhost:28822,http://127.0.0.1:28822"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
