"""FastAPI Dependencies для Dependency Injection."""

from typing import AsyncGenerator
from fastapi import Depends

from src.core.elasticsearch import ElasticsearchClient
from src.core.metrics import get_metrics_collector, get_system_monitor
from src.core.rate_limiter import get_rate_limiter
from src.core.logging import get_logger

logger = get_logger(__name__)


# ============================================================================
# Elasticsearch Client Dependency
# ============================================================================

async def get_elasticsearch_client() -> AsyncGenerator[ElasticsearchClient, None]:
    """
    Dependency для получения Elasticsearch клиента.
    
    Создаёт новый клиент для каждого запроса, подключается к ES,
    и корректно закрывает соединение после завершения запроса.
    
    Yields:
        ElasticsearchClient: Подключённый клиент Elasticsearch
    """
    client = ElasticsearchClient()
    
    try:
        # Подключаемся к Elasticsearch
        connected = await client.connect()
        if not connected:
            logger.warning("Failed to connect to Elasticsearch in dependency")
        
        yield client
        
    finally:
        # Закрываем соединение после завершения запроса
        await client.disconnect()


# ============================================================================
# Legacy dependencies (для постепенной миграции)
# ============================================================================

def get_es_client():
    """
    Legacy dependency для получения глобального ES клиента.
    TODO: Удалить после полной миграции на get_elasticsearch_client()
    """
    from src.core.elasticsearch import es_client
    return es_client


def get_metrics():
    """Dependency для получения MetricsCollector."""
    return get_metrics_collector()


def get_limiter():
    """Dependency для получения RateLimiter."""
    return get_rate_limiter()
