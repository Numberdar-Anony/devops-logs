from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    app_name: str = Field(default="DevOps Logs Project")
    database_url: str = Field(
        default="postgresql+psycopg_async://neondb_owner:npg_6WLnBqhAEs1J@ep-cool-shape-ae8ws2cv-pooler.c-2.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require",
        description="SQLAlchemy async database URL. Supports Neon PostgreSQL (psycopg_async) or sqlite fallback",
    )
    redis_url: str = Field(default="redis://localhost:6379/0")
    ollama_base_url: str = Field(default="http://127.0.0.1:11434")
    ollama_model: str = Field(default="qwen2.5-coder:7b")
    log_buffer_size: int = Field(default=5000)
    log_retention_minutes: int = Field(default=180)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
