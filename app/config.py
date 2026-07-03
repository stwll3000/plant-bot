from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    bot_token: str
    database_url: str
    webapp_url: str = ""
    port: int = 8000

    @property
    def async_database_url(self) -> str:
        # Railway выдаёт postgres:// или postgresql://,
        # а асинхронному SQLAlchemy нужен явный драйвер asyncpg
        url = self.database_url
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url


settings = Settings()
