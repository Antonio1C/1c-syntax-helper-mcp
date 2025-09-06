#!/usr/bin/env python3
"""Тестирование простого поиска."""

import asyncio
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from src.core.elasticsearch import es_client


async def test_simple_search():
    """Тестируем простые поисковые запросы."""
    print("=== Тестирование простых запросов ===")
    
    await es_client.connect()
    
    try:
        # 1. Простой multi_match запрос
        simple_query = {
            "query": {
                "multi_match": {
                    "query": "документ",
                    "fields": ["name", "description", "syntax_ru", "syntax_en"],
                    "type": "best_fields"
                }
            },
            "size": 3
        }
        
        print("\n🔍 Простой multi_match запрос:")
        print(f"Запрос: {json.dumps(simple_query, ensure_ascii=False, indent=2)}")
        
        response = await es_client.search(simple_query)
        if response:
            total = response.get('hits', {}).get('total', {})
            if isinstance(total, dict):
                total_count = total.get('value', 0)
            else:
                total_count = total
            print(f"✅ Найдено: {total_count} документов")
            
            for i, hit in enumerate(response['hits']['hits'][:3], 1):
                source = hit['_source']
                name = source.get('name', 'N/A')
                obj = source.get('object', 'N/A')
                desc = source.get('description', 'N/A')[:50]
                score = hit['_score']
                print(f"  {i}. {name} ({obj}) - {desc}... [score: {score:.2f}]")
        
        # 2. Поиск по конкретным полям
        field_tests = [
            ("catalog", "name"),
            ("catalog", "description"), 
            ("Телефония", "description"),
            ("InAppPurchaseService", "name")
        ]
        
        for term, field in field_tests:
            query = {
                "query": {"match": {field: term}},
                "size": 1
            }
            
            response = await es_client.search(query)
            if response:
                total = response.get('hits', {}).get('total', {})
                if isinstance(total, dict):
                    total_count = total.get('value', 0)
                else:
                    total_count = total
                print(f"🔍 '{term}' в {field}: {total_count} документов")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await es_client.disconnect()


if __name__ == "__main__":
    asyncio.run(test_simple_search())
