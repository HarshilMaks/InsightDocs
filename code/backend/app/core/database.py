"""
Database Management
Enhanced database layer with connection pooling, monitoring, and resilience features
for the AI-powered document processing platform
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional, Dict, Any, Callable, Awaitable, Union, TypeVar
from functools import wraps
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
    async_scoped_session
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError, TimeoutError
from sqlalchemy import event, text

from app.core.config import get_settings

# Initialize settings and logger
settings = get_settings()
logger = logging.getLogger(__name__)

# Base class for all ORM models
Base = declarative_base()

@dataclass
class DatabaseMetrics:
    """Database connection and performance metrics"""
    active_connections: int = 0
    total_connections: int = 0
    queries_executed: int = 0
    slow_queries: int = 0
    connection_errors: int = 0
    avg_query_time: float = 0.0
    pool_size: int = 0
    pool_checked_out: int = 0
    pool_overflow: int = 0
    pool_invalidated: int = 0

class DatabaseManager:
    """Enhanced database manager with connection pooling and monitoring"""
    
    def __init__(self):
        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[async_sessionmaker[AsyncSession]] = None
        self.scoped_session: Optional[async_scoped_session[AsyncSession]] = None
        self.metrics = DatabaseMetrics()
        self._is_initialized = False
        self._health_check_task: Optional[asyncio.Task] = None
        
    async def initialize(self) -> None:
        """Initialize database engine and session factory with enhanced configuration"""
        if self._is_initialized:
            logger.warning("Database manager already initialized")
            return
            
        try:
            # Configure engine parameters
            engine_kwargs = await self._get_engine_config()
            
            # Create async engine
            self.engine = create_async_engine(
                settings.database.get_async_url(),
                **engine_kwargs
            )
            
            # Configure session factory
            self.session_factory = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
                autocommit=False,
            )
            
            # Create scoped session for thread safety
            self.scoped_session = async_scoped_session(
                self.session_factory,
                scopefunc=asyncio.current_task,
            )
            
            # Set up event listeners for monitoring
            self._setup_event_listeners()
            
            # Test initial connection
            await self._test_connection()
            
            # Start background health monitoring
            if settings.app.metrics_enabled:
                self._health_check_task = asyncio.create_task(self._health_monitor())
            
            self._is_initialized = True
            logger.info("Database manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database manager: {e}")
            await self.cleanup()
            raise
    
    async def _get_engine_config(self) -> Dict[str, Any]:
        """Get optimized engine configuration based on environment"""
        db_settings = settings.database
        app_settings = settings.app
        
        config = {
            "echo": app_settings.debug and not app_settings.is_production,
            "echo_pool": app_settings.debug,
            "future": True,
            "pool_timeout": db_settings.database_pool_timeout,
            "pool_recycle": db_settings.database_pool_recycle,
            "pool_pre_ping": True,  # Verify connections before use
            "connect_args": {
                "command_timeout": db_settings.query_timeout,
                "server_settings": {
                    "application_name": f"{app_settings.app_name}-{app_settings.version}",
                }
            }
        }
        
        # Configure connection pooling based on environment
        if app_settings.is_production:
            config.update({
                "poolclass": QueuePool,
                "pool_size": db_settings.database_pool_size,
                "max_overflow": db_settings.database_max_overflow,
            })
        else:
            # Use smaller pool for development
            config.update({
                "poolclass": QueuePool,
                "pool_size": max(2, db_settings.database_pool_size // 2),
                "max_overflow": max(5, db_settings.database_max_overflow // 2),
            })
            
        return config
    
    def _setup_event_listeners(self) -> None:
        """Set up SQLAlchemy event listeners for monitoring and logging"""
        if not self.engine:
            return
            
        @event.listens_for(self.engine.sync_engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            context._query_start_time = time.perf_counter()
            
        @event.listens_for(self.engine.sync_engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            execution_time = time.perf_counter() - context._query_start_time
            self.metrics.queries_executed += 1
            
            # Track slow queries
            if execution_time > settings.database.slow_query_threshold:
                self.metrics.slow_queries += 1
                logger.warning(
                    f"Slow query detected: {execution_time:.3f}s\n"
                    f"Statement: {statement[:200]}..."
                )
            
            # Update average query time
            self.metrics.avg_query_time = (
                (self.metrics.avg_query_time * (self.metrics.queries_executed - 1) + execution_time)
                / self.metrics.queries_executed
            )
            
        @event.listens_for(self.engine.sync_engine, "connect")
        def on_connect(dbapi_conn, connection_record):
            self.metrics.total_connections += 1
            logger.debug("New database connection established")
            
        @event.listens_for(self.engine.sync_engine, "checkout")
        def on_checkout(dbapi_conn, connection_record, connection_proxy):
            self.metrics.active_connections += 1
            
        @event.listens_for(self.engine.sync_engine, "checkin")
        def on_checkin(dbapi_conn, connection_record):
            self.metrics.active_connections = max(0, self.metrics.active_connections - 1)
            
        @event.listens_for(self.engine.sync_engine, "invalidate")
        def on_invalidate(dbapi_conn, connection_record, exception):
            self.metrics.connection_errors += 1
            self.metrics.pool_invalidated += 1
            logger.error(f"Database connection invalidated: {exception}")
    
    async def _test_connection(self) -> None:
        """Test database connection and basic functionality"""
        if not self.engine:
            raise RuntimeError("Database engine not initialized")
            
        try:
            async with self.engine.begin() as conn:
                result = await conn.execute(text("SELECT 1 as test"))
                test_value = result.scalar()
                if test_value != 1:
                    raise RuntimeError("Database connection test failed")
                    
            logger.info("Database connection test passed")
            
        except Exception as e:
            self.metrics.connection_errors += 1
            logger.error(f"Database connection test failed: {e}")
            raise
    
    async def _health_monitor(self) -> None:
        """Background task for monitoring database health"""
        while True:
            try:
                await asyncio.sleep(settings.app.health_check_interval)
                
                if self.engine:
                    # Update pool metrics
                    pool = self.engine.pool
                    self.metrics.pool_size = pool.size()
                    self.metrics.pool_checked_out = pool.checkedout()
                    self.metrics.pool_overflow = pool.overflow()
                    
                    # Log metrics if debug mode
                    if settings.app.debug:
                        logger.debug(f"DB Metrics: {self.metrics}")
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
    
    async def get_session(self) -> AsyncSession:
        """Get a database session from the scoped session factory"""
        if not self._is_initialized or not self.scoped_session:
            raise RuntimeError("Database manager not initialized")
        return self.scoped_session()
    
    @asynccontextmanager
    async def session_scope(self) -> AsyncGenerator[AsyncSession, None]:
        """Context manager for database sessions with automatic cleanup"""
        session = await self.get_session()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()
    
    async def execute_with_retry(
        self, 
        query_func, 
        max_retries: int = 3, 
        retry_delay: float = 1.0
    ):
        """Execute database operation with retry logic for transient failures"""
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                async with self.session_scope() as session:
                    return await query_func(session)
                    
            except (DisconnectionError, TimeoutError, ConnectionError) as e:
                last_error = e
                self.metrics.connection_errors += 1
                
                if attempt < max_retries:
                    wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(
                        f"Database operation failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Database operation failed after {max_retries + 1} attempts")
                    
            except SQLAlchemyError as e:
                # Don't retry for non-transient errors
                logger.error(f"Database operation failed with non-retryable error: {e}")
                raise
                
        raise last_error
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive database health check"""
        health_info = {
            "status": "unknown",
            "timestamp": time.time(),
            "metrics": self.metrics,
            "connection_test": False,
            "pool_status": {},
        }
        
        try:
            # Test basic connectivity
            start_time = time.perf_counter()
            await self._test_connection()
            response_time = time.perf_counter() - start_time
            
            health_info.update({
                "status": "healthy",
                "connection_test": True,
                "response_time_ms": round(response_time * 1000, 2),
            })
            
            # Add pool information
            if self.engine:
                pool = self.engine.pool
                health_info["pool_status"] = {
                    "size": pool.size(),
                    "checked_out": pool.checkedout(),
                    "overflow": pool.overflow(),
                    "checked_in": pool.checkedin(),
                }
                
        except Exception as e:
            health_info.update({
                "status": "unhealthy",
                "error": str(e),
            })
            
        return health_info
    
    async def init_db(self) -> None:
        """Initialize database schema (create tables)"""
        if not self.engine:
            raise RuntimeError("Database engine not initialized")
            
        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database schema initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database schema: {e}")
            raise
    
    async def cleanup(self) -> None:
        """Clean up database resources"""
        try:
            # Cancel health monitoring
            if self._health_check_task:
                self._health_check_task.cancel()
                try:
                    await self._health_check_task
                except asyncio.CancelledError:
                    pass
            
            # Close scoped session
            if self.scoped_session:
                await self.scoped_session.remove()
            
            # Close engine
            if self.engine:
                await self.engine.dispose()
                
            self._is_initialized = False
            logger.info("Database manager cleaned up successfully")
            
        except Exception as e:
            logger.error(f"Error during database cleanup: {e}")

# Global database manager instance
db_manager = DatabaseManager()

# Dependency for FastAPI routes
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for getting database sessions"""
    async with db_manager.session_scope() as session:
        yield session

# Convenience functions for backward compatibility
async def get_session() -> AsyncSession:
    """Get a database session"""
    return await db_manager.get_session()

async def init_db() -> None:
    """Initialize database schema"""
    await db_manager.init_db()

# Startup and shutdown handlers
async def startup_database() -> None:
    """Initialize database on application startup"""
    await db_manager.initialize()
    if settings.database.auto_migrate:
        await db_manager.init_db()

async def shutdown_database() -> None:
    """Clean up database resources on application shutdown"""
    await db_manager.cleanup()

# Decorators for database operations
def with_db_session(func):
    """Decorator for functions that need a database session"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        async with db_manager.session_scope() as session:
            return await func(session, *args, **kwargs)
    return wrapper

def with_db_retry(max_retries: int = 3, retry_delay: float = 1.0):
    """Decorator for database operations with retry logic"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await db_manager.execute_with_retry(
                lambda session: func(session, *args, **kwargs),
                max_retries=max_retries,
                retry_delay=retry_delay
            )
        return wrapper
    return decorator

# Export commonly used items
__all__ = [
    "Base",
    "db_manager", 
    "get_db",
    "get_session",
    "init_db",
    "startup_database",
    "shutdown_database",
    "with_db_session",
    "with_db_retry",
    "DatabaseManager",
    "DatabaseMetrics"
]
