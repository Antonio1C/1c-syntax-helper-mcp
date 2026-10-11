"""Основной сервис поиска по документации 1С."""

from typing import List, Dict, Any, Optional
import time

from src.core.elasticsearch import ElasticsearchClient
from src.core.logging import get_logger
from src.search.query_builder import QueryBuilder
from src.search.ranker import SearchRanker
from src.search.formatter import SearchFormatter

logger = get_logger(__name__)


class SearchService:
    """Сервис поиска по документации 1С."""
    
    def __init__(self, es_client: ElasticsearchClient):
        self.es_client = es_client
        self.query_builder = QueryBuilder()
        self.ranker = SearchRanker()
        self.formatter = SearchFormatter()

    @staticmethod
    def _first_document(response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        hits = response.get("hits", {}).get("hits", [])
        return hits[0].get("_source") if hits else None

    @staticmethod
    def _ambiguous_result(element_name: str) -> Dict[str, Any]:
        return {
            "ambiguous": True,
            "element_name": element_name,
            "message": (
                f"Элемент '{element_name}' найден у объекта. "
                "Укажите русское имя объекта в параметре object_name."
            )
        }

    @staticmethod
    def _is_global_document(document: Dict[str, Any]) -> bool:
        return document.get("type") in QueryBuilder.GLOBAL_TYPES
    
    async def find_help_by_query(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """Универсальный поиск справки по любому элементу 1С."""
        start_time = time.time()
        
        try:
            # Проверяем подключение к Elasticsearch
            if not await self.es_client.is_connected():
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
                search_type="auto"
            )
            
            # Выполняем поиск
            response = await self.es_client.search(es_query)
            
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
                "search_time_ms": search_time
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
    
    async def get_detailed_syntax_info(
        self, 
        element_name: str, 
        object_name: Optional[str] = None, 
        include_examples: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Получить полную техническую информацию об элементе.
        
        Использует двухэтапный поиск:
        1. Строго точное совпадение по name.keyword
        2. Fuzzy поиск если точное не найдено
        """
        try:
            # Этап 1: Строгий точный поиск
            strict_query = self.query_builder.build_strict_exact_query(element_name, object_name)
            response = await self.es_client.search(strict_query)
            doc = self._first_document(response)
            
            if doc:
                if not object_name and not self._is_global_document(doc):
                    logger.info(f"Для элемента '{element_name}' требуется имя объекта")
                    return self._ambiguous_result(element_name)

                logger.debug(f"Найден элемент '{element_name}' через строгий поиск")
                
                # Фильтруем примеры если не нужны
                if not include_examples:
                    doc = doc.copy()
                    doc.pop('examples', None)
                
                return doc
            
            # Этап 2: Fuzzy fallback если точное совпадение не найдено
            logger.info(f"Точное совпадение для '{element_name}' не найдено, используем fuzzy поиск")
            fuzzy_query = self.query_builder.build_exact_query(element_name, object_name, limit=1)
            response = await self.es_client.search(fuzzy_query)
            doc = self._first_document(response)
            
            if doc:
                if not object_name and not self._is_global_document(doc):
                    logger.info(f"Для элемента '{element_name}' требуется имя объекта")
                    return self._ambiguous_result(element_name)

                logger.info(f"Найден элемент '{doc.get('name')}' через fuzzy поиск (запрос: '{element_name}')")
                
                # Фильтруем примеры если не нужны
                if not include_examples:
                    doc = doc.copy()
                    doc.pop('examples', None)
                
                return doc
            
            logger.info(f"Элемент '{element_name}' не найден ни через точный, ни через fuzzy поиск")
            return None
            
        except Exception as e:
            logger.error(f"Ошибка получения детальной информации для '{element_name}': {e}")
            return None
    
    async def search_with_context_filter(
        self, 
        query: str, 
        context: str, 
        object_name: Optional[str] = None, 
        limit: int = 10
    ) -> Dict[str, Any]:
        """Поиск с фильтром по контексту (global/object/all)."""
        try:
            # Строим базовый запрос
            elasticsearch_query = self.query_builder.build_search_query(query, limit)
            
            # Добавляем фильтры по контексту
            context_filters = []
            
            if context == "global":
                context_filters.extend([
                    {"term": {"type": "global_function"}},
                    {"term": {"type": "global_procedure"}},
                    {"term": {"type": "global_event"}}
                ])
            elif context == "object":
                context_filters.extend([
                    {"term": {"type": "object_function"}},
                    {"term": {"type": "object_procedure"}},
                    {"term": {"type": "object_property"}},
                    {"term": {"type": "object_event"}},
                    {"term": {"type": "object_constructor"}}
                ])
            # Для "all" не добавляем фильтры
            
            # Добавляем фильтр по объекту если указан
            if object_name and context != "global":
                context_filters.append({"term": {"object": object_name}})
            
            # Применяем фильтры
            if context_filters:
                elasticsearch_query["query"] = {
                    "bool": {
                        "must": [elasticsearch_query["query"]],
                        "filter": [{"bool": {"should": context_filters}}]
                    }
                }
            
            response = await self.es_client.search(elasticsearch_query)
            
            # Обрабатываем ответ
            if not response:
                return {
                    "results": [],
                    "total": 0,
                    "query": query,
                    "context": context,
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
            
            return {
                "results": formatted_results,
                "total": total_count,
                "query": query,
                "context": context
            }
            
        except Exception as e:
            logger.error(f"Ошибка контекстного поиска '{query}' в контексте '{context}': {e}")
            return {
                "results": [],
                "total": 0,
                "query": query,
                "context": context,
                "error": str(e)
            }
    
    async def get_object_members_list(
        self, 
        object_name: str, 
        member_type: str = "all", 
        limit: int = 50
    ) -> Dict[str, Any]:
        """Получить список элементов объекта с фильтрацией по типу."""
        try:
            # Базовый фильтр по объекту
            query_filters: List[Dict[str, Any]] = [{"term": {"object": object_name}}]
            
            # Добавляем фильтры по типу элементов
            if member_type == "methods":
                type_filters = [
                    {"term": {"type": "object_function"}},
                    {"term": {"type": "object_procedure"}},
                    {"term": {"type": "object_constructor"}}
                ]
                query_filters.append({"bool": {"should": type_filters}})
            elif member_type == "properties":
                query_filters.append({"term": {"type": "object_property"}})
            elif member_type == "events":
                query_filters.append({"term": {"type": "object_event"}})
            
            # Строим запрос
            elasticsearch_query = {
                "query": {
                    "bool": {
                        "filter": query_filters
                    }
                },
                "size": limit,
                "sort": [{"name.keyword": {"order": "asc"}}]
            }
            
            response = await self.es_client.search(elasticsearch_query)
            
            # Группируем результаты
            methods = []
            properties = []
            events = []
            
            for hit in response.get('hits', {}).get('hits', []):
                doc = hit['_source']
                doc_type = doc.get('type', '').lower()
                
                if 'function' in doc_type or 'procedure' in doc_type or 'constructor' in doc_type:
                    methods.append(doc)
                elif 'property' in doc_type:
                    properties.append(doc)
                elif 'event' in doc_type:
                    events.append(doc)
            
            return {
                "object": object_name,
                "member_type": member_type,
                "methods": methods,
                "properties": properties,
                "events": events,
                "total": len(methods) + len(properties) + len(events)
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения элементов объекта '{object_name}': {e}")
            return {
                "object": object_name,
                "member_type": member_type,
                "methods": [],
                "properties": [],
                "events": [],
                "total": 0,
                "error": str(e)
            }
