"""
Configuration management for InsightDocs.
(Merged from InsightDocs and Insight projects)
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import List, Optional

class AppSettings(BaseSettings):
    app_name: str = Field("InsightDocs", env="APP_NAME")
    app_env: str = Field("development", env="APP_ENV")
    app_port: int = Field(8000, env="APP_PORT")
    api_prefix: str = Field("/api/v1", env="API_PREFIX")
    debug: bool = Field(True, env="DEBUG")
    log_level: str = Field("INFO", env="LOG_LEVEL")

class SecuritySettings(BaseSettings):
    secret_key: str = Field(..., env="SECRET_KEY")
    algorithm: str = Field("HS256")
    access_token_expire_minutes: int = Field(30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(7)
    allowed_origins: List[str] = Field(["http://localhost:3000", "http://127.0.0.1:3000"], env="ALLOWED_ORIGINS")

class DatabaseSettings(BaseSettings):
    database_url: str = Field(..., env="DATABASE_URL")

class RedisSettings(BaseSettings):
    redis_url: str = Field(..., env="REDIS_URL")

class CelerySettings(BaseSettings):
    celery_broker_url: str = Field(..., env="CELERY_BROKER_URL")
    celery_result_backend: str = Field(..., env="CELERY_RESULT_BACKEND")

class LLMSettings(BaseSettings):
    google_api_key: str = Field(..., env="GOOGLE_API_KEY")
    gemini_model: str = Field("gemini-1.5-pro", env="GEMINI_MODEL")
    gemini_temperature: float = Field(0.7, env="GEMINI_TEMPERATURE")

class MilvusSettings(BaseSettings):
    milvus_uri: str = Field(..., env="MILVUS_URI")
    milvus_token: str = Field(..., env="MILVUS_TOKEN")
    milvus_collection: str = Field("InsightDocscollection", env="MILVUS_COLLECTION")
    milvus_dim: int = Field(768, env="MILVUS_DIM")

class StorageSettings(BaseSettings):
    s3_endpoint: str = Field(..., env="S3_ENDPOINT")
    aws_access_key_id: str = Field(..., env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str = Field(..., env="AWS_SECRET_ACCESS_KEY")
    s3_bucket_name: str = Field(..., env="S3_BUCKET_NAME")

class Settings(BaseSettings):
    app: AppSettings = AppSettings()
    security: SecuritySettings = SecuritySettings()
    database: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()
    celery: CelerySettings = CelerySettings()
    llm: LLMSettings = LLMSettings()
    milvus: MilvusSettings = MilvusSettings()
    storage: StorageSettings = StorageSettings()

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # This allows nested models to be populated
        env_nested_delimiter = '__' 

settings = Settings()