from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DB_URL: str

    model_config = SettingsConfigDict(env_file=".env")

def get_settings() -> Settings:
    return Settings()
