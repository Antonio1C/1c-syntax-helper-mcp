"""Index management endpoints."""

from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends

from src.core.config import settings
from src.core.elasticsearch import ElasticsearchClient
from src.core.logging import get_logger
from src.core.startup import index_hbk_file
from src.api.dependencies import get_elasticsearch_client, get_indexing_manager
from src.infrastructure.background.indexing_manager import BackgroundIndexingManager

router = APIRouter(prefix="/index", tags=["index"])
logger = get_logger(__name__)


@router.get("/status")
async def index_status(
    es_client: ElasticsearchClient = Depends(get_elasticsearch_client),
    indexing_manager: BackgroundIndexingManager = Depends(get_indexing_manager)
):
    """
    Получить статус индекса и фоновой индексации.
    
    Возвращает:
    - Статус подключения к Elasticsearch
    - Информацию о существовании индекса
    - Количество документов в индексе
    - Статус фоновой индексации (если активна)
    """
    # Информация об Elasticsearch индексе
    es_connected = await es_client.is_connected()
    index_exists = await es_client.index_exists() if es_connected else False
    docs_count = await es_client.get_documents_count() if index_exists else 0
    
    # Информация о фоновой индексации
    progress = await indexing_manager.get_status()
    
    return {
        "elasticsearch_connected": es_connected,
        "index_exists": index_exists,
        "documents_count": docs_count,
        "index_name": settings.elasticsearch.index_name,
        "indexing": {
            "is_active": indexing_manager.is_indexing(),
            **progress.to_dict()
        }
    }


@router.post("/rebuild")
async def rebuild_index(
    es_client: ElasticsearchClient = Depends(get_elasticsearch_client)
):
    """Переиндексация документации из .hbk файла."""
    try:
        # Проверяем подключение к Elasticsearch
        if not await es_client.is_connected():
            raise HTTPException(
                status_code=503,
                detail="Elasticsearch недоступен"
            )
        
        # Ищем .hbk файлы
        hbk_dir = Path(settings.data.hbk_directory)
        if not hbk_dir.exists():
            raise HTTPException(
                status_code=400,
                detail=f"Директория .hbk файлов не найдена: {hbk_dir}"
            )
        
        hbk_files = list(hbk_dir.glob("*.hbk"))
        if not hbk_files:
            raise HTTPException(
                status_code=400,
                detail=f"Файлы .hbk не найдены в {hbk_dir}"
            )
        
        # Индексируем первый найденный файл
        hbk_file = hbk_files[0]
        logger.info(f"Начинаем переиндексацию файла: {hbk_file}")
        
        success = await index_hbk_file(str(hbk_file), es_client)
        
        if success:
            docs_count = await es_client.get_documents_count()
            return {
                "status": "success",
                "message": "Переиндексация завершена успешно",
                "file": str(hbk_file),
                "documents_count": docs_count
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Ошибка переиндексации"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка переиндексации: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Внутренняя ошибка: {str(e)}"
        )
