"""
Configuration Management
Enhanced configuration system with validation, monitoring, and security features
for the AI-powered document processing platform
"""

import logging
import secrets
from typing import Optional, List, Dict, Any
from functools import lru_cache
from enum import Enum
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from pydantic import field_validator
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# Factory helpers for nested settings to satisfy static type checker
def _make_application_settings() -> "ApplicationSettings":
    return ApplicationSettings()  # type: ignore[call-arg]

def _make_database_settings() -> "DatabaseSettings":
    return DatabaseSettings()  # type: ignore[call-arg]

def _make_aws_settings() -> "AWSSettings":
    return AWSSettings()  # type: ignore[call-arg]

def _make_milvus_settings() -> "MilvusSettings":
    return MilvusSettings()  # type: ignore[call-arg]

def _make_llm_settings() -> "LLMSettings":
    return LLMSettings()  # type: ignore[call-arg]

def _make_security_settings() -> "SecuritySettings":
    return SecuritySettings()  # type: ignore[call-arg]

# Enums for better type safety
class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ApplicationSettings(BaseSettings):
    """Enhanced application settings with monitoring and performance tuning"""
    
    # App metadata
    app_name: str = Field("InsightOps", description="Application name")
    app_env: Environment = Field(Environment.DEVELOPMENT, description="Application environment")
    app_port: int = Field(8000, ge=1024, le=65535, description="Application port")
    debug: bool = Field(False, description="Debug mode")
    version: str = Field("1.0.0", description="Application version")
    
    # API settings
    api_prefix: str = Field("/api/v1", description="API prefix")
    docs_url: str = Field("/docs", description="API docs URL")
    redoc_url: str = Field("/redoc", description="ReDoc URL")
    openapi_url: str = Field("/openapi.json", description="OpenAPI JSON URL")
    
    # Server settings
    host: str = Field("0.0.0.0", description="Server host")
    workers: int = Field(1, ge=1, le=8, description="Number of worker processes")
    reload: bool = Field(False, description="Auto-reload on code changes")
    
    # Logging configuration
    log_level: LogLevel = Field(LogLevel.INFO, description="Logging level")
    token_logging: bool = Field(True, description="Enable token usage logging")
    log_file: Optional[str] = Field(None, description="Log file path")
    log_rotation: str = Field("1 day", description="Log rotation interval")
    log_retention: str = Field("30 days", description="Log retention period")
    structured_logging: bool = Field(True, description="Enable structured JSON logging")
    
    # Performance settings
    max_concurrent_uploads: int = Field(5, ge=1, le=50, description="Max concurrent uploads")
    processing_timeout: int = Field(600, ge=30, le=3600, description="Processing timeout in seconds")
    max_request_size: int = Field(100 * 1024 * 1024, description="Max request size in bytes")
    request_timeout: int = Field(300, ge=30, le=1800, description="Request timeout in seconds")
    
    # Background task settings
    task_queue_size: int = Field(1000, ge=10, le=10000, description="Task queue size")
    max_task_retries: int = Field(3, ge=0, le=10, description="Max task retries")
    task_retry_delay: int = Field(60, ge=1, le=3600, description="Task retry delay in seconds")
    
    # Health check settings
    health_check_interval: int = Field(30, ge=10, le=300, description="Health check interval")
    enable_health_endpoint: bool = Field(True, description="Enable health check endpoint")
    health_check_timeout: int = Field(10, ge=1, le=60, description="Health check timeout")
    
    # Caching settings
    cache_enabled: bool = Field(True, description="Enable response caching")
    cache_ttl: int = Field(3600, ge=60, le=86400, description="Cache TTL in seconds")
    cache_max_size: int = Field(1000, ge=10, le=10000, description="Max cache entries")
    
    # Monitoring and metrics
    metrics_enabled: bool = Field(True, description="Enable metrics collection")
    prometheus_endpoint: str = Field("/metrics", description="Prometheus metrics endpoint")
    tracing_enabled: bool = Field(False, description="Enable distributed tracing")
    
    @field_validator('app_env', mode='before')
    @classmethod
    def validate_environment(cls, v: object) -> Environment:
        if isinstance(v, str):
            return Environment(v.lower())
        if isinstance(v, Environment):
            return v
        raise TypeError('app_env must be a string or Environment')
    
    @property
    def is_development(self) -> bool:
        return self.app_env == Environment.DEVELOPMENT
    
    @property
    def is_production(self) -> bool:
        return self.app_env == Environment.PRODUCTION
    
    @property
    def is_staging(self) -> bool:
        return self.app_env == Environment.STAGING
    
    def get_uvicorn_config(self) -> Dict[str, Any]:
        """Get Uvicorn server configuration"""
        return {
            "host": self.host,
            "port": self.app_port,
            "workers": self.workers if self.is_production else 1,
            "reload": self.reload or self.is_development,
            "log_level": self.log_level.value.lower(),
            "access_log": not self.is_production,
        }
    
    model_config = SettingsConfigDict(case_sensitive=False)


class DatabaseSettings(BaseSettings):
    """Enhanced database configuration with connection pooling and monitoring"""
    
    # Neon Postgres settings
    database_url: str = Field("", description="PostgreSQL connection URL")
    
    # Connection pool settings
    database_pool_size: int = Field(10, ge=1, le=50, description="Connection pool size")
    database_max_overflow: int = Field(20, ge=0, le=100, description="Max overflow connections")
    database_pool_timeout: int = Field(30, ge=1, le=300, description="Pool timeout in seconds")
    database_pool_recycle: int = Field(3600, ge=300, description="Connection recycle time")
    
    # Query settings
    query_timeout: int = Field(30, ge=1, le=300, description="Query timeout in seconds")
    slow_query_threshold: float = Field(1.0, ge=0.1, description="Slow query threshold in seconds")
    
    # Migration settings
    auto_migrate: bool = Field(False, description="Auto-run migrations on startup")
    migration_timeout: int = Field(300, description="Migration timeout in seconds")
    
    @field_validator('database_url')
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v:
            raise ValueError("DATABASE_URL is required")
        if not v.startswith(('postgresql://', 'postgresql+asyncpg://', 'sqlite://')):
            raise ValueError("DATABASE_URL must be a valid PostgreSQL or SQLite connection string")
        return v
    
    def get_async_url(self) -> str:
        """Convert sync URL to async for SQLAlchemy"""
        if self.database_url.startswith('postgresql://'):
            return self.database_url.replace('postgresql://', 'postgresql+asyncpg://')
        return self.database_url
    
    model_config = SettingsConfigDict(env_prefix="DATABASE_", case_sensitive=False)


class AWSSettings(BaseSettings):
    """Enhanced AWS configuration with retry policies and monitoring"""
    
    # AWS credentials
    aws_access_key_id: str = Field("", description="AWS Access Key ID")
    aws_secret_access_key: str = Field("", description="AWS Secret Access Key", repr=False)
    aws_default_region: str = Field("ap-south-1", description="Default AWS region")
    aws_session_token: Optional[str] = Field(None, description="AWS session token for temporary credentials")
    
    # S3 settings
    s3_bucket_name: str = Field("", description="S3 bucket name for file storage")
    s3_upload_prefix: str = Field("uploads/", description="S3 key prefix for uploads")
    s3_presigned_url_expiration: int = Field(3600, ge=300, le=86400, description="Presigned URL expiration in seconds")
    s3_multipart_threshold: int = Field(64 * 1024 * 1024, description="Multipart upload threshold")
    s3_max_concurrency: int = Field(10, ge=1, le=50, description="Max concurrent S3 operations")
    
    # Lambda settings
    lambda_function_name: str = Field("", description="Lambda function name for processing")
    lambda_timeout: int = Field(300, ge=30, le=900, description="Lambda timeout in seconds")
    lambda_memory_size: int = Field(512, ge=128, le=10240, description="Lambda memory in MB")
    lambda_retry_attempts: int = Field(3, ge=1, le=10, description="Lambda retry attempts")
    
    # File processing settings
    max_file_size: int = Field(100 * 1024 * 1024, description="Maximum file size in bytes")
    allowed_extensions: List[str] = Field(['.pdf', '.docx', '.doc', '.txt', '.csv', '.xlsx', '.xls'])
    virus_scan_enabled: bool = Field(True, description="Enable virus scanning for uploads")
    
    @field_validator('aws_access_key_id', 'aws_secret_access_key', 's3_bucket_name')
    @classmethod
    def validate_required_aws_fields(cls, v: str) -> str:
        if not v:
            raise ValueError("Value is required for AWS operations")
        return v
    
    @field_validator('s3_bucket_name')
    @classmethod
    def validate_s3_bucket_name(cls, v: str) -> str:
        if v and (len(v) < 3 or len(v) > 63):
            raise ValueError("S3 bucket name must be between 3 and 63 characters")
        return v
    
    def get_boto3_config(self) -> Dict[str, Any]:
        """Get boto3 configuration dictionary"""
        config = {
            'region_name': self.aws_default_region,
            'aws_access_key_id': self.aws_access_key_id,
            'aws_secret_access_key': self.aws_secret_access_key,
        }
        if self.aws_session_token:
            config['aws_session_token'] = self.aws_session_token
        return config
    
    model_config = SettingsConfigDict(case_sensitive=False)


class MilvusSettings(BaseSettings):
    """Enhanced Milvus vector database configuration with performance tuning"""
    
    # Zilliz Cloud settings
    milvus_uri: str = Field("", description="Milvus connection URI")
    milvus_token: str = Field("", description="Milvus authentication token", repr=False)
    milvus_collection: str = Field("insightopscollection", description="Collection name")
    
    # Vector configuration
    milvus_dim: int = Field(768, description="Vector dimension")
    milvus_metric: str = Field("COSINE", description="Distance metric")
    milvus_index_type: str = Field("IVF_FLAT", description="Index type")
    milvus_nlist: int = Field(1024, ge=1, le=65536, description="Index parameter nlist")
    
    # Search settings
    milvus_search_params: Dict[str, int] = Field({"nprobe": 10}, description="Search parameters")
    milvus_top_k: int = Field(10, ge=1, le=100, description="Top K results")
    consistency_level: str = Field("Eventually", description="Consistency level")
    
    # Performance settings
    batch_size: int = Field(1000, ge=1, le=10000, description="Batch size for operations")
    connection_pool_size: int = Field(10, ge=1, le=100, description="Connection pool size")
    timeout: int = Field(30, ge=1, le=300, description="Operation timeout in seconds")
    
    # Index settings
    auto_create_index: bool = Field(True, description="Auto-create index on collection")
    index_build_params: Dict[str, Any] = Field(
        {"nlist": 1024, "m": 8}, 
        description="Index build parameters"
    )
    
    @field_validator('milvus_uri')
    @classmethod
    def validate_milvus_uri(cls, v: str) -> str:
        if not v:
            raise ValueError("MILVUS_URI is required")
        if not (v.startswith('https://') or v.startswith('grpc://') or v.startswith('localhost')):
            raise ValueError("MILVUS_URI must be a valid HTTPS, gRPC URL, or localhost")
        return v
    
    @field_validator('milvus_dim')
    @classmethod
    def validate_dimension(cls, v: int) -> int:
        valid_dims = [128, 256, 384, 512, 768, 1024, 1536, 2048, 4096]
        if v not in valid_dims:
            raise ValueError(f"MILVUS_DIM must be one of {valid_dims}")
        return v
    
    @field_validator('milvus_metric')
    @classmethod
    def validate_metric(cls, v: str) -> str:
        valid_metrics = ['L2', 'IP', 'COSINE', 'HAMMING', 'JACCARD']
        if v.upper() not in valid_metrics:
            raise ValueError(f"MILVUS_METRIC must be one of {valid_metrics}")
        return v.upper()
    
    def get_collection_schema(self) -> Dict[str, Any]:
        """Get collection schema configuration"""
        return {
            "dimension": self.milvus_dim,
            "metric_type": self.milvus_metric,
            "index_type": self.milvus_index_type,
            "index_params": self.index_build_params
        }
    
    model_config = SettingsConfigDict(case_sensitive=False)


class LLMSettings(BaseSettings):
    """Enhanced LLM configuration with advanced parameters and monitoring"""
    
    # Gemini API settings
    google_api_key: str = Field("", description="Google Gemini API key", repr=False)
    gemini_model: str = Field("gemini-1.5-pro", description="Gemini model name")
    gemini_temperature: float = Field(0.7, ge=0.0, le=2.0, description="Generation temperature")
    gemini_max_output_tokens: int = Field(2048, ge=1, le=8192, description="Max output tokens")
    gemini_top_p: float = Field(0.8, ge=0.0, le=1.0, description="Top-p sampling parameter")
    gemini_top_k: int = Field(40, ge=1, le=100, description="Top-k sampling parameter")
    
    # Alternative model settings
    fallback_model: str = Field("gemini-1.5-flash", description="Fallback model if primary fails")
    use_fallback: bool = Field(True, description="Enable fallback model on failures")
    
    # Embedding settings
    embedding_model: str = Field("models/text-embedding-004", description="Embedding model")
    embedding_dimension: int = Field(768, description="Embedding dimension")
    max_tokens_per_chunk: int = Field(8000, ge=100, le=32000, description="Max tokens per chunk")
    chunk_overlap: int = Field(200, ge=0, le=1000, description="Chunk overlap in tokens")
    
    # Processing settings
    batch_size: int = Field(10, ge=1, le=100, description="Batch size for processing")
    max_retries: int = Field(3, ge=0, le=10, description="Max retry attempts")
    retry_delay: float = Field(1.0, ge=0.1, le=60.0, description="Retry delay in seconds")
    timeout: int = Field(60, ge=10, le=300, description="Request timeout in seconds")
    
    # Rate limiting
    requests_per_minute: int = Field(60, ge=1, le=1000, description="Requests per minute limit")
    requests_per_day: int = Field(1500, ge=1, le=50000, description="Requests per day limit")
    tokens_per_minute: int = Field(32000, ge=1000, description="Tokens per minute limit")
    
    # Context window management
    max_context_length: int = Field(128000, description="Maximum context window length")
    context_overflow_strategy: str = Field("truncate", description="Strategy when context overflows")
    preserve_system_prompt: bool = Field(True, description="Always preserve system prompt")
    
    # Safety and content filtering
    safety_threshold: str = Field("BLOCK_MEDIUM_AND_ABOVE", description="Content safety threshold")
    enable_content_filter: bool = Field(True, description="Enable content filtering")
    
    @field_validator('google_api_key')
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        if not v:
            raise ValueError("GOOGLE_API_KEY is required")
        if not v.startswith('AIza'):
            raise ValueError("GOOGLE_API_KEY must be a valid Google API key")
        return v
    
    @field_validator('context_overflow_strategy')
    @classmethod
    def validate_overflow_strategy(cls, v: str) -> str:
        valid_strategies = ['truncate', 'summarize', 'split', 'error']
        if v not in valid_strategies:
            raise ValueError(f"context_overflow_strategy must be one of {valid_strategies}")
        return v
    
    def get_generation_config(self) -> Dict[str, Any]:
        """Get generation configuration for Gemini"""
        return {
            "temperature": self.gemini_temperature,
            "top_p": self.gemini_top_p,
            "top_k": self.gemini_top_k,
            "max_output_tokens": self.gemini_max_output_tokens,
        }
    
    def get_safety_settings(self) -> List[Dict[str, str]]:
        """Get safety settings for content filtering"""
        categories = [
            "HARM_CATEGORY_HARASSMENT",
            "HARM_CATEGORY_HATE_SPEECH",
            "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            "HARM_CATEGORY_DANGEROUS_CONTENT"
        ]
        return [{"category": cat, "threshold": self.safety_threshold} for cat in categories]
    
    model_config = SettingsConfigDict(case_sensitive=False)


class SecuritySettings(BaseSettings):
    """Enhanced security configuration with comprehensive protection"""
    
    # JWT settings
    secret_key: str = Field("", description="JWT secret key", repr=False)
    algorithm: str = Field("HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(30, ge=1, le=1440, description="Access token expiry")
    refresh_token_expire_days: int = Field(7, ge=1, le=90, description="Refresh token expiry")
    
    # Advanced JWT settings
    jwt_issuer: str = Field("InsightOps", description="JWT issuer")
    jwt_audience: str = Field("InsightOps-Users", description="JWT audience")
    require_https: bool = Field(True, description="Require HTTPS in production")
    
    # CORS settings
    allowed_origins: List[str] = Field(
        ["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Allowed CORS origins"
    )
    allowed_methods: List[str] = Field(
        ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        description="Allowed HTTP methods"
    )
    allowed_headers: List[str] = Field(["*"], description="Allowed headers")
    allow_credentials: bool = Field(True, description="Allow credentials in CORS")
    
    # Rate limiting
    rate_limit_enabled: bool = Field(True, description="Enable rate limiting")
    requests_per_minute: int = Field(60, ge=1, le=1000, description="Requests per minute per IP")
    burst_limit: int = Field(100, ge=1, le=1000, description="Burst request limit")
    rate_limit_storage: str = Field("memory", description="Rate limit storage backend")
    
    # File upload security
    max_file_size: int = Field(100 * 1024 * 1024, description="Maximum file size in bytes")
    allowed_file_types: List[str] = Field([".pdf", ".docx", ".doc", ".txt", ".csv", ".xlsx", ".xls"])
    allowed_mime_types: List[str] = Field([
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
        "text/plain",
        "text/csv",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel"
    ])
    scan_uploaded_files: bool = Field(True, description="Scan uploaded files for malware")
    quarantine_suspicious_files: bool = Field(True, description="Quarantine suspicious files")
    
    # Password security
    min_password_length: int = Field(8, ge=4, le=128, description="Minimum password length")
    require_uppercase: bool = Field(True, description="Require uppercase letters")
    require_lowercase: bool = Field(True, description="Require lowercase letters")
    require_numbers: bool = Field(True, description="Require numbers")
    require_special_chars: bool = Field(False, description="Require special characters")
    password_history_count: int = Field(5, ge=0, le=50, description="Password history to check")
    
    # Session security
    session_timeout_minutes: int = Field(60, ge=5, le=1440, description="Session timeout")
    max_concurrent_sessions: int = Field(5, ge=1, le=100, description="Max concurrent sessions per user")
    force_logout_on_password_change: bool = Field(True, description="Force logout on password change")
    
    # API security
    api_key_enabled: bool = Field(False, description="Enable API key authentication")
    api_key_header: str = Field("X-API-Key", description="API key header name")
    require_user_agent: bool = Field(True, description="Require User-Agent header")
    
    # Encryption settings
    encryption_key: Optional[str] = Field(None, description="Data encryption key", repr=False)
    encrypt_sensitive_data: bool = Field(True, description="Encrypt sensitive data at rest")
    
    @field_validator('secret_key')
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if not v:
            v = secrets.token_urlsafe(32)  # Generate if not provided
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v
    
    @field_validator('allowed_origins')
    @classmethod
    def validate_origins(cls, v: List[str]) -> List[str]:
        # Add localhost variants if not in production
        common_localhost = [
            "http://localhost:3000", "http://127.0.0.1:3000",
            "http://localhost:8000", "http://127.0.0.1:8000"
        ]
        for origin in common_localhost:
            if origin not in v:
                v.append(origin)
        return v
    
    def generate_jwt_config(self) -> Dict[str, Any]:
        """Generate JWT configuration"""
        return {
            "secret_key": self.secret_key,
            "algorithm": self.algorithm,
            "access_token_expire_minutes": self.access_token_expire_minutes,
            "refresh_token_expire_days": self.refresh_token_expire_days,
            "issuer": self.jwt_issuer,
            "audience": self.jwt_audience
        }
    
    model_config = SettingsConfigDict(case_sensitive=False)


class Settings(BaseSettings):
    """Main application settings aggregator"""
    
    # Initialize all configuration sections
    app: ApplicationSettings = Field(default_factory=_make_application_settings)
    database: DatabaseSettings = Field(default_factory=_make_database_settings)
    aws: AWSSettings = Field(default_factory=_make_aws_settings)
    milvus: MilvusSettings = Field(default_factory=_make_milvus_settings)
    llm: LLMSettings = Field(default_factory=_make_llm_settings)
    security: SecuritySettings = Field(default_factory=_make_security_settings)
    
    model_config = SettingsConfigDict(case_sensitive=False)
    
    def model_post_init(self, __context: Any) -> None:
        self._validate_cross_dependencies()
    
    def _validate_cross_dependencies(self):
        """Validate cross-dependencies between different settings"""
        # Ensure production settings are secure
        if self.app.is_production:
            if not self.security.require_https:
                logging.warning("HTTPS should be required in production")
            if self.app.debug:
                logging.warning("Debug mode should be disabled in production")
        
        # Validate embedding dimensions match
        if self.llm.embedding_dimension != self.milvus.milvus_dim:
            raise ValueError(
                f"LLM embedding dimension ({self.llm.embedding_dimension}) "
                f"must match Milvus dimension ({self.milvus.milvus_dim})"
            )


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings"""
    return Settings()


# Export settings instance
settings = get_settings()