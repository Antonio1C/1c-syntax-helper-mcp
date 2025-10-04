"""Health check endpoints."""

from fastapi import APIRouter, Depends

from src.models.mcp_models import HealthResponse
from src.core.elasticsearch import es_client
from src.core.metrics import get_metrics_collector
from src.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(metrics=Depends(get_metrics_collector)):
    """Проверка состояния системы."""
    async with metrics.timer("health_check.duration"):
        # Подключаемся к Elasticsearch если еще не подключены
        if not await es_client.is_connected():
            await es_client.connect()
        
        es_connected = await es_client.is_connected()
        index_exists = await es_client.index_exists() if es_connected else False
        docs_count = await es_client.get_documents_count() if index_exists else None
    
    await metrics.increment("health_check.requests")
    
    return HealthResponse(
        status="healthy" if es_connected else "unhealthy",
        elasticsearch=es_connected,
        index_exists=index_exists,
        documents_count=docs_count
    )
