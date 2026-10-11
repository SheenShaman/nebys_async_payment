from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DB_URL: str = "postgresql+asyncpg://payments:payments@postgres:5432/payments"
    RABBITMQ_URL: str = "amqp://guest:guest@rabbitmq:5672/"
    API_KEY: str = "secret_key"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


def get_settings() -> Settings:
    return Settings()
