"""Основной сервис поиска по документации 1С."""

from typing import List, Dict, Any, Optional
import time

from src.core.elasticsearch import es_client
from src.core.logging import get_logger
from src.search.query_builder import QueryBuilder
from src.search.ranker import SearchRanker
from src.search.formatter import SearchFormatter

logger = get_logger(__name__)


class SearchService:
    """Сервис поиска по документации 1С."""
    
    def __init__(self):
        self.query_builder = QueryBuilder()
        self.ranker = SearchRanker()
        self.formatter = SearchFormatter()
    
    async def search_1c_syntax(
        self,
        query: str,
        limit: int = 10,
        search_type: str = "auto"
    ) -> Dict[str, Any]:
        """
        Поиск по синтаксису 1С.
        
        Args:
            query: Поисковый запрос
            limit: Максимальное количество результатов
            search_type: Тип поиска (auto, exact, fuzzy, semantic)
        
        Returns:
            Словарь с результатами поиска
        """
        start_time = time.time()
        
        try:
            # Проверяем подключение к Elasticsearch
            if not await es_client.is_connected():
                return {
                    "results": [],
                    "total": 0,
                    "query": query,
                    "search_time_ms": 0,
                    "error": "Elasticsearch недоступен"
                }
            
            # Строим запрос
            es_query = self.query_builder.build_search_query(
                query=query,
                limit=limit,
                search_type=search_type
            )
            
            # Выполняем поиск
            response = await es_client.search(es_query)
            
            if not response:
                return {
                    "results": [],
                    "total": 0,
                    "query": query,
                    "search_time_ms": int((time.time() - start_time) * 1000),
                    "error": "Ошибка выполнения поиска"
                }
            
            # Извлекаем результаты
            hits = response.get("hits", {}).get("hits", [])
            total = response.get("hits", {}).get("total", {})
            total_count = total.get("value", 0) if isinstance(total, dict) else total
            
            # Ранжируем результаты
            ranked_results = self.ranker.rank_results(hits, query)
            
            # Форматируем для вывода
            formatted_results = self.formatter.format_search_results(ranked_results)
            
            search_time = int((time.time() - start_time) * 1000)
            
            logger.info(f"Поиск '{query}' завершен за {search_time}ms. Найдено: {len(formatted_results)}")
            
            return {
                "results": formatted_results,
                "total": total_count,
                "query": query,
                "search_time_ms": search_time,
                "search_type": search_type
            }
            
        except Exception as e:
            search_time = int((time.time() - start_time) * 1000)
            logger.error(f"Ошибка поиска '{query}': {e}")
            
            return {
                "results": [],
                "total": 0,
                "query": query,
                "search_time_ms": search_time,
                "error": str(e)
            }
    
    async def get_function_details(self, function_name: str) -> Optional[Dict[str, Any]]:
        """
        Получение подробной информации о функции.
        
        Args:
            function_name: Точное имя функции
        
        Returns:
            Подробная информация о функции или None
        """
        try:
            # Строим точный запрос по имени
            es_query = self.query_builder.build_exact_query(function_name)
            
            response = await es_client.search(es_query)
            
            if not response:
                return None
            
            hits = response.get("hits", {}).get("hits", [])
            
            if not hits:
                return None
            
            # Берем первый результат (наиболее релевантный)
            result = hits[0]["_source"]
            
            # Форматируем детальную информацию
            return self.formatter.format_function_details(result)
            
        except Exception as e:
            logger.error(f"Ошибка получения деталей функции '{function_name}': {e}")
            return None
    
    async def get_object_info(self, object_name: str) -> Dict[str, Any]:
        """
        Получение информации об объекте 1С (методы, свойства, события).
        
        Args:
            object_name: Имя объекта 1С
        
        Returns:
            Информация об объекте с методами, свойствами и событиями
        """
        try:
            # Строим запрос для поиска всех элементов объекта
            es_query = self.query_builder.build_object_query(object_name)
            
            response = await es_client.search(es_query)
            
            if not response:
                return {
                    "object": object_name,
                    "methods": [],
                    "properties": [],
                    "events": [],
                    "total": 0
                }
            
            hits = response.get("hits", {}).get("hits", [])
            
            # Группируем результаты по типам
            methods = []
            properties = []
            events = []
            
            for hit in hits:
                doc = hit["_source"]
                doc_type = doc.get("type", "")
                
                if "method" in doc_type.lower():
                    methods.append(self.formatter.format_object_method(doc))
                elif "property" in doc_type.lower():
                    properties.append(self.formatter.format_object_property(doc))
                elif "event" in doc_type.lower():
                    events.append(self.formatter.format_object_event(doc))
            
            return {
                "object": object_name,
                "methods": methods,
                "properties": properties,
                "events": events,
                "total": len(methods) + len(properties) + len(events)
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения информации об объекте '{object_name}': {e}")
            return {
                "object": object_name,
                "methods": [],
                "properties": [],
                "events": [],
                "total": 0,
                "error": str(e)
            }


# Глобальный экземпляр сервиса поиска
search_service = SearchService()
