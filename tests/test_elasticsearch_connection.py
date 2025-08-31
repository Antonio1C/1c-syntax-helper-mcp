"""Тест 1: Проверка подключения к Elasticsearch."""

import asyncio
import sys
import pytest
from pathlib import Path

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent))

from src.core.config import settings
from src.core.elasticsearch import es_client
from src.core.logging import get_logger

logger = get_logger(__name__)


@pytest.mark.asyncio
async def test_elasticsearch_connection():
    """Тест 1: Проверка подключения к Elasticsearch."""
    print("=== Тест 1: Подключение к Elasticsearch ===")
    
    try:
        connected = await es_client.connect()
        if connected:
            print("✅ Подключение к Elasticsearch успешно")
            
            # Проверяем статус
            index_exists = await es_client.index_exists()
            docs_count = await es_client.get_documents_count() if index_exists else 0
            
            print(f"Индекс существует: {index_exists}")
            print(f"Документов в индексе: {docs_count}")
            return True
        else:
            print("❌ Не удалось подключиться к Elasticsearch")
            print("Убедитесь что Elasticsearch запущен на localhost:9200")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return False
    finally:
        await es_client.disconnect()


if __name__ == "__main__":
    asyncio.run(test_elasticsearch_connection())
