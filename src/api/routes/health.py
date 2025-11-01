"""Health check endpoints."""

from fastapi import APIRouter, Depends

from src.models.mcp_models import HealthResponse
from src.core.elasticsearch import ElasticsearchClient
from src.core.metrics import get_metrics_collector
from src.core.config import settings
from src.api.dependencies import get_elasticsearch_client, get_indexing_manager
from src.infrastructure.background.indexing_manager import BackgroundIndexingManager

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(
    es_client: ElasticsearchClient = Depends(get_elasticsearch_client),
    indexing_manager: BackgroundIndexingManager = Depends(get_indexing_manager),
    metrics=Depends(get_metrics_collector)
):
    """
    Проверка состояния системы.
    
    Возвращает информацию о:
    - Статусе приложения (всегда healthy если приложение запущено)
    - Подключении к Elasticsearch
    - Состоянии индекса
    - Статусе фоновой индексации
    """
    async with metrics.timer("health_check.duration"):
        # Клиент уже подключён через dependency
        es_connected = await es_client.is_connected()
        index_exists = bool(await es_client.index_exists()) if es_connected else False
        docs_count = await es_client.get_documents_count() if index_exists else None
        
        # Получаем статус фоновой индексации
        indexing_progress = await indexing_manager.get_status()
    
    await metrics.increment("health_check.requests")
    
    # Приложение считается healthy даже во время индексации
    return HealthResponse(
        status="healthy" if es_connected else "unhealthy",
        elasticsearch=es_connected,
        index_exists=index_exists,
        documents_count=docs_count,
        indexing_status=indexing_progress.status.value,
        indexing_active=indexing_manager.is_indexing()
    )
