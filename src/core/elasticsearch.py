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
from src.core.retry import retry_on_connection_error, retry_on_transient_error

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
    
    @retry_on_connection_error
    async def connect(self) -> bool:
        """Подключается к Elasticsearch с retry механизмом."""
        logger.info("Attempting to connect to Elasticsearch...")
        
        self._client = AsyncElasticsearch(
            hosts=[self._config.url],
            request_timeout=self._request_timeout,
            max_retries=0,  # Отключаем встроенный retry, используем декоратор
            retry_on_timeout=False
        )
        
        # Проверяем подключение
        await self._client.info()
        logger.info("Successfully connected to Elasticsearch")
        return True
    
    async def disconnect(self) -> None:
        """Отключается от Elasticsearch."""
        if self._client:
            try:
                await self._client.close()
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
    
    @retry_on_connection_error
    async def index_exists(self) -> bool:
        """Проверяет существование индекса с retry."""
        if not self._client:
            raise ConnectionFailedError("No connection to Elasticsearch")
        
        return await self._client.indices.exists(index=self._config.index_name)
    
    @retry_on_connection_error
    async def create_index(self) -> bool:
        """Создает индекс с оптимизированной схемой с retry."""
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
                    "availability": {"type": "text"},
                    "version_from": {"type": "keyword"},
                    "examples": {"type": "text", "analyzer": "russian"},
                    "source_file": {"type": "keyword"},
                    "full_path": {"type": "keyword"}
                }
            }
        }
        
        await self._client.indices.create(index=self._config.index_name, body=index_config)
        logger.info(f"Index '{self._config.index_name}' created successfully")
        return True
    
    @retry_on_transient_error
    async def get_documents_count(self) -> int:
        """Получает количество документов в индексе с retry."""
        if not self._client:
            raise ConnectionFailedError("No connection to Elasticsearch")
        
        response = await self._client.count(index=self._config.index_name)
        return response["count"]
    
    async def refresh_index(self) -> bool:
        """Принудительно обновляет индекс для немедленного отражения изменений."""
        if not self._client:
            return False
        
        try:
            await self._client.indices.refresh(index=self._config.index_name)
            return True
        except Exception as e:
            logger.error(f"Ошибка обновления индекса: {e}")
            return False
    
    @retry_on_transient_error
    async def search(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Выполняет поиск в индексе с retry."""
        if not self._client:
            raise ConnectionFailedError("No connection to Elasticsearch")
        
        response = await self._client.search(
            index=self._config.index_name,
            body=query
        )
        return response


# Factory function для создания клиента (для обратной совместимости)
def create_elasticsearch_client() -> ElasticsearchClient:
    """Создаёт новый экземпляр ElasticsearchClient."""
    return ElasticsearchClient()


# Глобальный экземпляр для обратной совместимости (будет удалён в следующих спринтах)
# TODO: Удалить после миграции всех компонентов на DI
es_client = ElasticsearchClient()
