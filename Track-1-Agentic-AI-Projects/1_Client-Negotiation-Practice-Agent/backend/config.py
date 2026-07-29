"""Application configuration loaded from environment variables / .env file."""

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str
    openai_model: str = "gpt-4o"

    # PostgreSQL connection string used by the LangGraph checkpointer.
    # e.g. postgresql://user:password@localhost:5432/negotiation
    # Reads the POSTGRESQL_URL env var (falls back to DATABASE_URL).
    database_url: str = Field(
        validation_alias=AliasChoices("POSTGRESQL_URL", "DATABASE_URL")
    )


settings = Settings()  # type: ignore[call-arg]
