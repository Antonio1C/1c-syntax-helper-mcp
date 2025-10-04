"""Rate limiting middleware."""

import time
from fastapi import Request
from fastapi.responses import JSONResponse

from src.core.rate_limiter import get_rate_limiter, RateLimitExceeded
from src.core.metrics import get_metrics_collector
from src.core.logging import get_logger

logger = get_logger(__name__)


async def rate_limit_middleware(request: Request, call_next):
    """Middleware для ограничения скорости запросов."""
    rate_limiter = get_rate_limiter()
    metrics = get_metrics_collector()
    
    # Получаем IP клиента
    client_ip = request.client.host if request.client else "unknown"
    
    try:
        # Проверяем rate limit
        await rate_limiter.check_rate_limit(client_ip)
        
        # Измеряем время выполнения запроса
        start_time = time.time()
        response = await call_next(request)
        response_time = time.time() - start_time
        
        # Записываем метрики
        await metrics.record_timer("request.duration", response_time, 
                                 {"method": request.method, "path": request.url.path})
        await metrics.update_performance_stats(
            success=200 <= response.status_code < 400,
            response_time=response_time
        )
        
        return response
        
    except RateLimitExceeded as e:
        await metrics.increment("requests.rate_limited", labels={"client_ip": client_ip})
        
        return JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded",
                "message": str(e),
                "retry_after": e.retry_after
            },
            headers={"Retry-After": str(e.retry_after)}
        )
    except Exception as e:
        await metrics.increment("requests.middleware_error")
        logger.error(f"Error in rate limit middleware: {e}")
        
        response = await call_next(request)
        return response
