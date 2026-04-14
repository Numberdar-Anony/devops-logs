from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    app_name: str = Field(default="DevOps Logs Project")
    database_url: str = Field(
        default="postgresql+psycopg_async://neondb_owner:npg_6WLnBqhAEs1J@ep-cool-shape-ae8ws2cv-pooler.c-2.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require",
        description="SQLAlchemy async database URL. Supports Neon PostgreSQL (psycopg_async) or sqlite fallback",
    )
    redis_url: str = Field(default="redis://localhost:6379/0")
    openrouter_api_key: Optional[str] = Field(default=None)
    openrouter_model: str = Field(default="openrouter/free")
    log_buffer_size: int = Field(default=5000)
    log_retention_minutes: int = Field(default=180)

    # MinIO
    minio_endpoint: str = Field(default="localhost:9000")
    minio_access_key: str = Field(default="minioadmin")
    minio_secret_key: str = Field(default="minioadmin")
    minio_bucket: str = Field(default="devops-logs")
    minio_secure: bool = Field(default=False)

    # Jenkins
    jenkins_url: str = Field(default="")
    jenkins_user: str = Field(default="")
    jenkins_token: str = Field(default="")

    # Telegram
    telegram_bot_token: str = Field(default="")
    telegram_chat_id: str = Field(default="")

    # Slack
    slack_webhook_url: str = Field(default="")

    # Terraform
    terraform_log_path: str = Field(default="sample.log")

    # ArgoCD
    argocd_url: str = Field(default="")
    argocd_token: str = Field(default="")
    
    # Kubernetes
    kubeconfig: str = Field(default="")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
