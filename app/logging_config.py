# app/logging_config.py
"""Structured logging configuration with loguru for production observability."""

import sys
import time
from loguru import logger
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


def setup_logging(log_level: str = "INFO") -> None:
    """Configure structured JSON logging for production."""
    # Remove default logger
    logger.remove()
    
    # Add structured JSON logger for production
    logger.add(
        sys.stdout,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} | {message}",
        level=log_level,
        serialize=True,  # JSON output
        backtrace=True,  # Include stack traces
        diagnose=True,   # Include variable values in tracebacks
    )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all HTTP requests with timing and error handling."""

    async def dispatch(self, request: Request, call_next) -> Response:
        """Log request details and response times."""
        start_time = time.time()
        
        # Extract request info
        method = request.method
        path = request.url.path
        query = str(request.query_params) if request.query_params else ""
        client_ip = request.client.host if request.client else "unknown"
        
        try:
            response = await call_next(request)
            process_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Log successful requests
            log_data = {
                "method": method,
                "path": path,
                "query": query,
                "status_code": response.status_code,
                "process_time_ms": round(process_time, 2),
                "client_ip": client_ip
            }
            
            if response.status_code >= 400:
                logger.warning(f"HTTP {response.status_code}", extra=log_data)
            else:
                logger.info(f"HTTP {response.status_code}", extra=log_data)
                
            return response
            
        except Exception as exc:
            process_time = (time.time() - start_time) * 1000
            
            # Log errors with stack traces
            log_data = {
                "method": method,
                "path": path,
                "query": query,
                "process_time_ms": round(process_time, 2),
                "client_ip": client_ip,
                "error": str(exc),
                "error_type": type(exc).__name__
            }
            
            logger.error(f"Request failed: {exc}", extra=log_data)
            raise  # Re-raise the exception
