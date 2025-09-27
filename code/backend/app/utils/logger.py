"""
Enhanced logging configuration
Supports structured logging, file rotation, and monitoring integration
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional
import json
from datetime import datetime

from ..core.config import settings


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        if settings.app.structured_logging:
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
            }
            
            # Add extra fields if they exist
            if hasattr(record, 'user_id'):
                log_entry['user_id'] = record.user_id
            if hasattr(record, 'request_id'):
                log_entry['request_id'] = record.request_id
            if hasattr(record, 'file_id'):
                log_entry['file_id'] = record.file_id
            if hasattr(record, 'tokens_used'):
                log_entry['tokens_used'] = record.tokens_used
                
            return json.dumps(log_entry)
        else:
            return super().format(record)


def setup_logging() -> logging.Logger:
    """Setup application logging with configuration from settings"""
    
    # Create root logger
    logger = logging.getLogger("insightops")
    logger.setLevel(getattr(logging, settings.app.log_level.value))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.app.log_level.value))
    
    if settings.app.structured_logging:
        console_formatter = StructuredFormatter()
    else:
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler (if log_file is specified)
    if settings.app.log_file:
        log_path = Path(settings.app.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Rotating file handler
        file_handler = logging.handlers.TimedRotatingFileHandler(
            filename=log_path,
            when='D',  # Daily rotation
            interval=1,
            backupCount=30,  # Keep 30 days of logs
            encoding='utf-8'
        )
        
        file_handler.setLevel(getattr(logging, settings.app.log_level.value))
        file_handler.setFormatter(StructuredFormatter() if settings.app.structured_logging 
                                else console_formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a specific module"""
    return logging.getLogger(f"insightops.{name}")


# Token usage logger for LLM monitoring
def log_token_usage(
    user_id: Optional[str] = None,
    model: str = "",
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int = 0,
    cost: float = 0.0,
    request_id: Optional[str] = None
):
    """Log token usage for monitoring and billing"""
    if not settings.app.token_logging:
        return
        
    logger = get_logger("tokens")
    logger.info(
        "Token usage recorded",
        extra={
            'user_id': user_id,
            'model': model,
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'total_tokens': total_tokens,
            'cost': cost,
            'request_id': request_id
        }
    )


# File processing logger
def log_file_processing(
    file_id: str,
    filename: str,
    file_size: int,
    processing_time: float,
    status: str,
    user_id: Optional[str] = None,
    error: Optional[str] = None
):
    """Log file processing events"""
    logger = get_logger("files")
    
    level = logging.ERROR if status == "failed" else logging.INFO
    message = f"File {status}: {filename}"
    
    logger.log(
        level,
        message,
        extra={
            'file_id': file_id,
            'filename': filename,
            'file_size': file_size,
            'processing_time': processing_time,
            'status': status,
            'user_id': user_id,
            'error': error
        }
    )


# Performance monitoring logger
def log_performance(
    operation: str,
    duration: float,
    success: bool = True,
    metadata: Optional[dict] = None
):
    """Log performance metrics"""
    logger = get_logger("performance")
    
    extra = {
        'operation': operation,
        'duration': duration,
        'success': success
    }
    
    if metadata:
        extra.update(metadata)
    
    logger.info(f"Operation {operation} completed", extra=extra)


# Initialize logging on module import
app_logger = setup_logging()