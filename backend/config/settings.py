"""
Configuration management for InsightDocs.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import List

class Settings(BaseSettings):
    # Application
    app_name: str = Field("InsightDocs")
    app_env: str = Field("development")
    app_port: int = Field(8000)
    api_prefix: str = Field("/api/v1")
    debug: bool = Field(True)
    log_level: str = Field("INFO")
    
    # Security
    secret_key: str
    algorithm: str = Field("HS256")
    access_token_expire_minutes: int = Field(30)
    refresh_token_expire_days: int = Field(7)
    allowed_origins: str = Field("http://localhost:3000,http://127.0.0.1:3000")
    
    # Database
    database_url: str
    
    # Redis
    redis_url: str
    
    # Celery
    celery_broker_url: str
    celery_result_backend: str
    
    # LLM
    gemini_api_key: str
    gemini_model: str = Field("gemini-1.5-pro")
    gemini_temperature: float = Field(0.7)
    
    # Milvus
    milvus_uri: str
    milvus_token: str
    milvus_collection: str = Field("insightopscollection")
    milvus_dim: int = Field(768)
    
    # Embeddings
    vector_dimension: int = Field(384)
    
    # Storage
    s3_endpoint: str
    aws_access_key_id: str
    aws_secret_access_key: str
    s3_bucket_name: str
    
    @property
    def allowed_origins_list(self) -> List[str]:
        """Convert comma-separated origins to list."""
        return [origin.strip() for origin in self.allowed_origins.split(",")]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

settings = Settings()
