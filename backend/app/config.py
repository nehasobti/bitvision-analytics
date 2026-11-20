from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    cors_origins: list[str] = ["http://localhost:5173"]
    export_max_rows: int = 50_000
    app_language: str = "it"
    # The app's own data (saved analyses, budgets): Postgres when set, else the SQLite file below.
    # STORE_POSTGRES_URL: Vercel's Postgres integration connected with the custom prefix "STORE"
    # (the prefix keeps it from overwriting DATABASE_URL, which is BitVision's MySQL).
    store_url: str | None = Field(None, validation_alias=AliasChoices("STORE_URL", "STORE_POSTGRES_URL", "POSTGRES_URL"))
    saved_views_path: str = "data/saved_views.db"


settings = Settings()
