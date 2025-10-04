"""Startup logic для приложения."""

from pathlib import Path

from src.core.config import settings
from src.core.logging import get_logger
from src.core.elasticsearch import ElasticsearchClient
from src.parsers.hbk_parser import HBKParser
from src.parsers.indexer import indexer

logger = get_logger(__name__)


async def auto_index_on_startup(es_client: ElasticsearchClient):
    """
    Автоматическая индексация при запуске, если найден .hbk файл.
    
    Args:
        es_client: Подключённый клиент Elasticsearch
    """
    try:
        # Ищем .hbk файлы в директории данных
        hbk_dir = Path(settings.data.hbk_directory)
        if not hbk_dir.exists():
            logger.warning(f"Директория .hbk файлов не найдена: {hbk_dir}")
            return
        
        hbk_files = list(hbk_dir.glob("*.hbk"))
        if not hbk_files:
            logger.info(f"Файлы .hbk не найдены в {hbk_dir}. Индексация будет выполнена при загрузке файла.")
            return
        
        # Проверяем, нужна ли индексация
        index_exists = await es_client.index_exists()
        docs_count = await es_client.get_documents_count() if index_exists else 0
        
        if index_exists and docs_count and docs_count > 0:
            logger.info(f"Индекс уже существует с {docs_count} документами. Пропускаем автоиндексацию.")
            return
        
        # Запускаем индексацию первого найденного файла
        hbk_file = hbk_files[0]
        logger.info(f"Запускаем автоматическую индексацию файла: {hbk_file}")
        
        success = await index_hbk_file(str(hbk_file), es_client)
        if success:
            logger.info("Автоматическая индексация завершена успешно")
        else:
            logger.error("Ошибка автоматической индексации")
            
    except Exception as e:
        logger.error(f"Ошибка при автоматической индексации: {e}")


async def index_hbk_file(file_path: str, es_client: ElasticsearchClient) -> bool:
    """
    Индексирует .hbk файл в Elasticsearch.
    
    Args:
        file_path: Путь к .hbk файлу
        es_client: Подключённый клиент Elasticsearch
        
    Returns:
        bool: True если индексация успешна, False иначе
    """
    try:
        logger.info(f"Начинаем индексацию файла: {file_path}")
        
        # Парсим .hbk файл
        parser = HBKParser()
        parsed_hbk = parser.parse_file(file_path)
        
        if not parsed_hbk:
            logger.error("Ошибка парсинга .hbk файла")
            return False
        
        if not parsed_hbk.documentation:
            logger.warning("В файле не найдена документация для индексации")
            return False
        
        logger.info(f"Найдено {len(parsed_hbk.documentation)} документов для индексации")
        
        # Индексируем в Elasticsearch
        success = await indexer.reindex_all(parsed_hbk)
        
        if success:
            docs_count = await es_client.get_documents_count()
            logger.info(f"Индексация завершена. Документов в индексе: {docs_count}")
        
        return success
        
    except Exception as e:
        logger.error(f"Ошибка индексации файла {file_path}: {e}")
        return False
