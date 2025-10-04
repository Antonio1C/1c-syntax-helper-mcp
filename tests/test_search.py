"""Тест 4: Система поиска."""

import asyncio
import sys
import time
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.elasticsearch import es_client
from src.search.search_service import SearchService


@pytest.mark.asyncio
async def test_search():
    """Тест системы поиска."""
    print("=== Тест 4: Система поиска ===")
    
    try:
        # Подключаемся к Elasticsearch
        connected = await es_client.connect()
        if not connected:
            print(" Elasticsearch недоступен")
            return False
    
        # Создаем search_service с передачей es_client
        search_service = SearchService(es_client)
        
        test_queries = ["СтрДлина", "ТаблицаЗначений", "Добавить"]
    
        for query in test_queries:
            print(f"\n Поиск: '{query}'")
            
            start_time = time.time()
            results = await search_service.find_help_by_query(query, limit=3)
            search_time = time.time() - start_time
            
            if results.get("error"):
                print(f" Ошибка: {results['error']}")
                continue
            
            found = len(results.get("results", []))
            total = results.get("total", 0)
            reported_time = results.get("search_time_ms", 0)
            
            print(f" Найдено: {found} из {total}")
            print(f" Время: {reported_time}ms (реальное: {search_time*1000:.0f}ms)")
            
            if reported_time < 500:
                print(" Критерий < 500ms выполнен")
            else:
                print(" Поиск занял > 500ms")
            
            # Показываем результаты
            for i, result in enumerate(results.get("results", []), 1):
                name = result.get("name", "")
                obj = result.get("object", "")
                score = result.get("_score", 0)
                print(f"   {i}. {name}" + (f" ({obj})" if obj else "") + f" [score: {score}]")
        
        return True
        
    except Exception as e:
        print(f" Ошибка тестирования поиска: {e}")
        return False
    finally:
        await es_client.disconnect()


if __name__ == "__main__":
    asyncio.run(test_search())
