"""Startup logic для приложения."""

import asyncio
from pathlib import Path

from src.core.config import settings
from src.core.logging import get_logger
from src.core.elasticsearch import ElasticsearchClient
from src.infrastructure.background.indexing_manager import get_indexing_manager

logger = get_logger(__name__)


async def auto_index_on_startup(es_client: ElasticsearchClient):
    """
    Автоматическая индексация в фоновом режиме при запуске.
    
    Проверяет наличие .hbk файла и запускает фоновую индексацию.
    Поведение зависит от настроек:
    - force_reindex=True или reindex_on_startup=true: всегда индексирует
    - Иначе: индексирует только если индекс пуст или не существует
    
    Args:
        es_client: Подключённый клиент Elasticsearch
    """
    try:
        # Определяем путь к единственному .hbk файлу
        hbk_file = Path(settings.data.hbk_directory) / "shcntx_ru.hbk"
        
        if not hbk_file.exists():
            logger.warning(f"Файл .hbk не найден: {hbk_file}")
            return
        
        # Проверяем, нужна ли принудительная переиндексация
        force_reindex = settings.should_reindex_on_startup
        
        if not force_reindex:
            # Быстрая проверка индекса
            index_exists = await es_client.index_exists()
            if index_exists:
                docs_count = await es_client.get_documents_count()
                if docs_count > 0:
                    logger.info(f"Индекс уже существует с {docs_count} документами. Пропускаем автоиндексацию.")
                    return
        else:
            logger.info("Принудительная переиндексация при запуске (reindex_on_startup=true или --reindex)")
        
        # Запускаем фоновую индексацию с задержкой
        logger.info(f"Запланирована фоновая индексация файла: {hbk_file}")
        asyncio.create_task(_delayed_background_indexing(str(hbk_file), es_client))
        
    except Exception as e:
        logger.error(f"Ошибка при планировании автоиндексации: {e}")


async def _delayed_background_indexing(file_path: str, es_client: ElasticsearchClient):
    """
    Отложенная фоновая индексация.
    
    Даёт приложению время на полный запуск перед началом индексации.
    
    Args:
        file_path: Путь к .hbk файлу
        es_client: Клиент Elasticsearch
    """
    # Даём приложению 5 секунд на полный запуск
    await asyncio.sleep(5)
    
    logger.info("Начинаем фоновую индексацию...")
    
    try:
        manager = get_indexing_manager()
        await manager.start_indexing(file_path=file_path, es_client=es_client)
    except Exception as e:
        logger.error(f"Ошибка при запуске фоновой индексации: {e}")


async def index_hbk_file(file_path: str, es_client: ElasticsearchClient) -> bool:
    """
    Индексирует .hbk файл в Elasticsearch (используется для ручной индексации через API).
    
    Args:
        file_path: Путь к .hbk файлу
        es_client: Подключённый клиент Elasticsearch
        
    Returns:
        bool: True если индексация успешна, False иначе
    """
    try:
        from src.parsers.hbk_parser import HBKParser
        from src.parsers.indexer import ElasticsearchIndexer
        
        logger.info(f"Начинаем синхронную индексацию файла: {file_path}")
        
        # Парсим .hbk файл в отдельном потоке (не блокируем event loop)
        parser = HBKParser()
        logger.info("Запускаем парсинг HBK файла в отдельном потоке...")
        parsed_hbk = await asyncio.to_thread(parser.parse_file, file_path)
        logger.info("Парсинг HBK файла завершен")
        
        if not parsed_hbk:
            logger.error("Ошибка парсинга .hbk файла")
            return False
        
        if not parsed_hbk.documentation:
            logger.warning("В файле не найдена документация для индексации")
            return False
        
        logger.info(f"Найдено {len(parsed_hbk.documentation)} документов для индексации")
        
        # Индексируем в Elasticsearch
        indexer = ElasticsearchIndexer(es_client)
        success = await indexer.reindex_all(parsed_hbk)
        
        if success:
            docs_count = await es_client.get_documents_count()
            logger.info(f"Индексация завершена. Документов в индексе: {docs_count}")
        
        return success
        
    except Exception as e:
        logger.error(f"Ошибка индексации файла {file_path}: {e}")
        return False
