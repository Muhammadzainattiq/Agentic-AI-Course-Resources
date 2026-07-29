"""Central configuration, loaded from the environment (see .env.example)."""

from functools import lru_cache

from agents import set_default_openai_key
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- App ---
    app_name: str = "DineFlow"
    environment: str = "development"
    log_level: str = "INFO"
    port: int = 8000

    # --- LLM / Agent ---
    openai_api_key: str
    openai_model: str = "gpt-5"
    openai_extractor_model: str = "gpt-5-mini"
    agent_max_turns: int = 12
    agent_reasoning_effort: str = "low"

    # --- Postgres (Neon): short-term memory + ordering ---
    database_url: str
    db_pool_min_size: int = 1
    db_pool_max_size: int = 5

    # --- MongoDB: long-term memory ---
    mongodb_uri: str
    mongodb_db: str = "dineflow"
    mongodb_memories_collection: str = "long_term_memories"

    # --- Memory behaviour ---
    short_term_window: int = 20
    long_term_max_injected: int = 12
    memory_extraction_enabled: bool = True

    # --- Restaurant identity (used in the system prompt) ---
    restaurant_name: str = "DineFlow Kitchen"
    restaurant_currency: str = "USD"
    # The prompt quotes this same number, so what the agent says it charges and
    # what place_order actually charges can never drift apart.
    restaurant_tax_rate: float = 0.05

    # --- Authentication ---
    # 32 bytes minimum: a short HMAC key is brute-forceable, and anyone who
    # recovers it can mint a token claiming role="chef".
    jwt_secret: str = Field(min_length=32)
    jwt_expire_minutes: int = 60 * 24 * 7  # one week

    # The single kitchen account, provisioned on startup (no chef signup route).
    chef_email: str = "chef@gmail.com"
    chef_password: str = "chef@1234"

    # --- Security / CORS ---
    cors_allow_origins: str = "http://localhost:3000"
    api_auth_token: str = ""

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()  # type: ignore[call-arg]
    # The Agents SDK builds its default client from OPENAI_API_KEY in the process
    # environment, which `.env` never touches — hand it the key explicitly.
    set_default_openai_key(settings.openai_api_key)
    return settings
