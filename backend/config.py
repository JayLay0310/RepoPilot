from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # 应用配置
    app_name: str = Field(default="RepoPilot")
    app_env: str = Field(default="dev")
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    
    # LLM 配置
    openai_api_key: str = Field(default="")
    openai_model: str = Field(default="gpt-4-turbo")
    llm_temperature: float = Field(default=0.7)
    llm_max_tokens: int = Field(default=2000)
    
    # 向量模型配置
    embedding_model: str = Field(default="sentence-transformers/multilingual-e5-large")
    vector_store_dir: str = Field(default=".faiss")
    embedding_cache_path: str = Field(default=".cache/embeddings.json")
    
    # 检索配置
    retrieval_top_k: int = Field(default=10)
    retrieval_alpha: float = Field(default=0.5)  # BM25 权重
    similarity_threshold: float = Field(default=0.5)
    
    # CORS 配置
    cors_origins: str = Field(default="http://localhost,http://127.0.0.1")

    model_config = SettingsConfigDict(env_file=".env", env_prefix="REPOPILOT_")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def get_cors_origins(settings: Settings) -> list[str]:
    return [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
