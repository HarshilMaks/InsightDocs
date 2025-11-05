"""Configuration management for InsightDocs."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""
    
    # Application
    app_env: str = "development"
    log_level: str = "INFO"
    secret_key: str
    
    # Database
    database_url: str
    
    # Redis
    redis_url: str
    
    # Celery
    celery_broker_url: str
    celery_result_backend: str
    
    # OpenAI
    openai_api_key: str
    
    # Storage
    s3_endpoint: str
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    s3_bucket_name: str
    
    # Vector Database
    vector_dimension: int = 384
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
