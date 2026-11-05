from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Версию вшивает Dockerfile (ARG APP_VERSION) — по ней видно, какой релиз сейчас запущен.
    app_version: str = "dev"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    greeting: str = "Добро пожаловать в гостевую книгу!"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "guestbook"
    postgres_user: str = "guestbook"
    postgres_password: str  # обязателен из окружения/.env, без default

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
