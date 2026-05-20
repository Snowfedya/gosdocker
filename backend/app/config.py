from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://gosdocker:secret@localhost:5432/gosdocker"
    debug: bool = False
    templates_dir: str = "app/templates"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
