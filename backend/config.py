from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="RepoPilot")
    app_env: str = Field(default="dev")
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    openai_model: str = Field(default="gpt-4-turbo")
    embedding_model: str = Field(default="sentence-transformers/multilingual-e5-large")
    vector_store_dir: str = Field(default=".faiss")

    model_config = SettingsConfigDict(env_file=".env", env_prefix="REPOPILOT_")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
