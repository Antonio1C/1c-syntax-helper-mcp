"""FastAPI Dependencies для Dependency Injection."""

from typing import Annotated
from fastapi import Depends

from src.core.elasticsearch import es_client
from src.core.metrics import get_metrics_collector, get_system_monitor
from src.core.rate_limiter import get_rate_limiter
from src.core.logging import get_logger

# Type aliases для удобного использования в endpoints
ESClient = Annotated[type(es_client), Depends(lambda: es_client)]
MetricsCollector = Annotated[type(get_metrics_collector()), Depends(get_metrics_collector)]
SystemMonitor = Annotated[type(get_system_monitor()), Depends(get_system_monitor)]
RateLimiter = Annotated[type(get_rate_limiter()), Depends(get_rate_limiter)]


def get_es_client():
    """Dependency для получения Elasticsearch клиента."""
    return es_client


def get_metrics():
    """Dependency для получения MetricsCollector."""
    return get_metrics_collector()


def get_limiter():
    """Dependency для получения RateLimiter."""
    return get_rate_limiter()
