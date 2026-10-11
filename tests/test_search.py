"""Тест 4: Система поиска."""

import asyncio
import sys
import time
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.elasticsearch import ElasticsearchClient
from src.handlers.mcp_handlers import handle_get_quick_reference, handle_get_syntax_info
from src.models.mcp_models import GetQuickReferenceRequest, GetSyntaxInfoRequest
from src.search.query_builder import QueryBuilder
from src.search.search_service import SearchService


@pytest.mark.unit
@pytest.mark.search
def test_strict_exact_query_is_case_insensitive_and_requires_name_match():
    query = QueryBuilder().build_strict_exact_query("PutFile")
    bool_query = query["query"]["bool"]
    name_conditions = bool_query["must"][0]["bool"]["should"]

    assert query["size"] == 1
    assert name_conditions == [
        {"term": {"name_ru.keyword": {"value": "putfile", "boost": 10.0}}},
        {"term": {"name_en.keyword": {"value": "putfile", "boost": 10.0}}},
    ]
    assert bool_query["must"][0]["bool"]["minimum_should_match"] == 1
    assert bool_query["should"] == [
        {"terms": {"type": QueryBuilder.GLOBAL_TYPES, "boost": 2.0}}
    ]


@pytest.mark.unit
@pytest.mark.search
def test_strict_exact_query_filters_by_russian_object_name():
    query = QueryBuilder().build_strict_exact_query("Количество", "ТаблицаЗначений")

    assert query["query"]["bool"]["filter"] == [
        {"term": {"object": "ТаблицаЗначений"}}
    ]


@pytest.mark.unit
@pytest.mark.search
def test_exact_fallback_normalizes_keyword_queries_and_uses_filter():
    query = QueryBuilder().build_exact_query("PutFile", "ТаблицаЗначений")
    bool_query = query["query"]["bool"]
    name_conditions = bool_query["must"][0]["bool"]["should"]

    assert name_conditions[0] == {
        "term": {"name_ru.keyword": {"value": "putfile", "boost": 10.0}}
    }
    assert name_conditions[1] == {
        "term": {"name_en.keyword": {"value": "putfile", "boost": 10.0}}
    }
    assert name_conditions[5] == {
        "wildcard": {"name_ru.keyword": {"value": "*putfile*", "boost": 2.0}}
    }
    assert bool_query["must"][0]["bool"]["minimum_should_match"] == 1
    assert bool_query["should"] == [
        {"terms": {"type": QueryBuilder.GLOBAL_TYPES, "boost": 2.0}}
    ]
    assert bool_query["filter"] == [{"term": {"object": "ТаблицаЗначений"}}]


def _search_response(document=None):
    hits = [{"_source": document}] if document else []
    return {"hits": {"total": {"value": len(hits)}, "hits": hits}}


@pytest.mark.unit
@pytest.mark.search
@pytest.mark.asyncio
async def test_detailed_info_returns_global_strict_match_without_fallback():
    client = AsyncMock()
    client.search.return_value = _search_response({
        "name": "ПоместитьФайл (PutFile)",
        "type": "global_function",
        "examples": ["example"]
    })

    result = await SearchService(client).get_detailed_syntax_info(
        "putfile",
        include_examples=False
    )

    assert result == {
        "name": "ПоместитьФайл (PutFile)",
        "type": "global_function"
    }
    client.search.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.search
@pytest.mark.asyncio
async def test_detailed_info_requires_object_for_strict_object_match():
    client = AsyncMock()
    client.search.return_value = _search_response({
        "name": "Количество (Count)",
        "type": "object_function",
        "object": "ТаблицаЗначений"
    })

    result = await SearchService(client).get_detailed_syntax_info("Количество")

    assert result["ambiguous"] is True
    assert "object_name" in result["message"]
    client.search.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.search
@pytest.mark.asyncio
async def test_detailed_info_uses_fuzzy_fallback_after_empty_strict_search():
    client = AsyncMock()
    client.search.side_effect = [
        _search_response(),
        _search_response({"name": "СтрДлина", "type": "global_function"})
    ]

    result = await SearchService(client).get_detailed_syntax_info("СтрДлин")

    assert result["name"] == "СтрДлина"
    assert client.search.await_count == 2


@pytest.mark.unit
@pytest.mark.search
@pytest.mark.asyncio
async def test_detailed_info_requires_object_for_fuzzy_object_match():
    client = AsyncMock()
    client.search.side_effect = [
        _search_response(),
        _search_response({
            "name": "Количество (Count)",
            "type": "object_function",
            "object": "ТаблицаЗначений"
        })
    ]

    result = await SearchService(client).get_detailed_syntax_info("Количеств")

    assert result["ambiguous"] is True
    assert client.search.await_count == 2


@pytest.mark.unit
@pytest.mark.search
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("handler", "tool_request"),
    [
        (handle_get_syntax_info, GetSyntaxInfoRequest(element_name="Количество")),
        (handle_get_quick_reference, GetQuickReferenceRequest(element_name="Количество")),
    ]
)
async def test_mcp_handlers_format_ambiguous_result(handler, tool_request):
    client = AsyncMock()

    with patch(
        "src.handlers.mcp_handlers.SearchService.get_detailed_syntax_info",
        new=AsyncMock(return_value={
            "ambiguous": True,
            "message": "Укажите русское имя объекта в параметре object_name."
        })
    ):
        response = await handler(tool_request, client)

    assert response.error is None
    assert "object_name" in response.content[0]["text"]


@pytest.mark.integration
@pytest.mark.elasticsearch
@pytest.mark.search
@pytest.mark.asyncio
async def test_search():
    """Тест системы поиска."""
    es_client = ElasticsearchClient()
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
