"""Клиент Elasticsearch."""

from typing import Optional, Dict, Any, List
import asyncio
from elasticsearch import AsyncElasticsearch
from elasticsearch.exceptions import ConnectionError, NotFoundError, RequestError

from src.core.config import settings
from src.core.logging import get_logger
from src.core.constants import (
    ELASTICSEARCH_CONNECTION_TIMEOUT,
    ELASTICSEARCH_REQUEST_TIMEOUT,
    BATCH_SIZE
)

logger = get_logger(__name__)


class ElasticsearchError(Exception):
    """Базовое исключение для ошибок Elasticsearch."""
    pass


class ConnectionFailedError(ElasticsearchError):
    """Ошибка подключения к Elasticsearch."""
    pass


class IndexNotFoundError(ElasticsearchError):
    """Индекс не найден."""
    pass


class ElasticsearchClient:
    """Клиент для работы с Elasticsearch."""
    
    def __init__(self):
        self._client: Optional[AsyncElasticsearch] = None
        self._config = settings.elasticsearch
        self._connection_timeout = ELASTICSEARCH_CONNECTION_TIMEOUT
        self._request_timeout = ELASTICSEARCH_REQUEST_TIMEOUT
    
    async def connect(self) -> bool:
        """Подключается к Elasticsearch."""
        try:
            self._client = AsyncElasticsearch(
                hosts=[self._config.url],
                request_timeout=self._request_timeout,
                max_retries=self._config.max_retries,
                retry_on_timeout=True,
                timeout=self._connection_timeout
            )
            
            # Проверяем подключение
            await self._client.info()
            logger.info("Успешно подключились к Elasticsearch")
            return True
            
        except ConnectionError as e:
            logger.error(f"Ошибка подключения к Elasticsearch: {e}")
            raise ConnectionFailedError(f"Failed to connect to Elasticsearch: {e}")
        except Exception as e:
            logger.error(f"Неожиданная ошибка при подключении к Elasticsearch: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Отключается от Elasticsearch."""
        if self._client:
            try:
                await self._client.close()
                logger.info("Отключились от Elasticsearch")
            except Exception as e:
                logger.warning(f"Ошибка при отключении от Elasticsearch: {e}")
            finally:
                self._client = None
    
    async def is_connected(self) -> bool:
        """Проверяет подключение к Elasticsearch."""
        if not self._client:
            return False
        
        try:
            await self._client.ping()
            return True
        except Exception:
            return False
    
    async def index_exists(self) -> bool:
        """Проверяет существование индекса."""
        if not self._client:
            raise ConnectionFailedError("No connection to Elasticsearch")
        
        try:
            return await self._client.indices.exists(index=self._config.index_name)
        except ConnectionError as e:
            raise ConnectionFailedError(f"Connection lost: {e}")
        except Exception as e:
            logger.error(f"Ошибка проверки индекса: {e}")
            raise ElasticsearchError(f"Failed to check index existence: {e}")
    
    async def create_index(self) -> bool:
        """Создает индекс с оптимизированной схемой."""
        if not self._client:
            raise ConnectionFailedError("No connection to Elasticsearch")
        
        # Упрощенная схема индекса
        index_config = {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "analysis": {
                    "analyzer": {
                        "russian": {
                            "tokenizer": "standard",
                            "filter": ["lowercase", "russian_stop", "russian_stemmer"]
                        }
                    },
                    "filter": {
                        "russian_stop": {"type": "stop", "stopwords": "_russian_"},
                        "russian_stemmer": {"type": "stemmer", "language": "russian"}
                    }
                }
            },
            "mappings": {
                "properties": {
                    "id": {"type": "keyword"},
                    "type": {"type": "keyword"}, 
                    "name": {"type": "text", "analyzer": "russian", "fields": {"keyword": {"type": "keyword"}}},
                    "object": {"type": "keyword"},
                    "syntax_ru": {"type": "text"},
                    "syntax_en": {"type": "text"},
                    "description": {"type": "text", "analyzer": "russian"},
                    "parameters": {
                        "type": "nested",
                        "properties": {
                            "name": {"type": "text"},
                            "type": {"type": "keyword"},
                            "description": {"type": "text", "analyzer": "russian"},
                            "required": {"type": "boolean"}
                        }
                    },
                    "return_type": {"type": "keyword"},
                    "version_from": {"type": "keyword"},
                    "examples": {"type": "text", "analyzer": "russian"},
                    "source_file": {"type": "keyword"},
                    "full_path": {"type": "keyword"}
                }
            }
        }
        
        try:
            await self._client.indices.create(index=self._config.index_name, body=index_config)
            logger.info(f"Создан индекс {self._config.index_name}")
            return True
        except Exception as e:
            logger.error(f"Ошибка создания индекса: {e}")
            return False
    
    async def get_documents_count(self) -> Optional[int]:
        """Получает количество документов в индексе."""
        if not self._client:
            return None
        
        try:
            response = await self._client.count(index=self._config.index_name)
            return response["count"]
        except Exception as e:
            logger.error(f"Ошибка получения количества документов: {e}")
            return None
    
    async def search(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Выполняет поиск в индексе."""
        if not self._client:
            logger.error("Нет подключения к Elasticsearch")
            return None
        
        try:
            response = await self._client.search(
                index=self._config.index_name,
                body=query
            )
            return response
        except Exception as e:
            logger.error(f"Ошибка поиска: {e}")
            return None


# Глобальный экземпляр клиента
es_client = ElasticsearchClient()
