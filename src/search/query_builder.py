"""Построитель запросов для Elasticsearch."""

from typing import Dict, Any, List, Optional


class QueryBuilder:
    """Построитель Elasticsearch запросов для поиска по документации 1С."""

    GLOBAL_TYPES = ["global_function", "global_procedure", "global_event"]

    def build_search_query(
        self,
        query: str,
        limit: int = 10,
        search_type: str = "auto"
    ) -> Dict[str, Any]:
        """
        Строит поисковый запрос.

        Args:
            query: Поисковый запрос
            limit: Максимальное количество результатов
            search_type: Тип поиска (auto, exact, fuzzy, semantic)
        
        Returns:
            Elasticsearch запрос
        """
        # Определяем тип поиска автоматически
        if search_type == "auto":
            search_type = self._detect_search_type(query)
        
        if search_type == "exact":
            return self.build_phrase_query(query, limit)
        elif search_type == "fuzzy":
            return self.build_fuzzy_query(query, limit)
        elif search_type == "semantic":
            return self.build_semantic_query(query, limit)
        else:
            return self.build_multi_match_query(query, limit)
    
    def build_strict_exact_query(self, element_name: str, object_name: Optional[str] = None) -> Dict[str, Any]:
        """Строит строго точный запрос по имени элемента.
        
        Ищет точное совпадение в полях name_ru.keyword или name_en.keyword.
        """
        normalized_name = element_name.lower()
        name_query = {
            "bool": {
                "should": [
                    {"term": {"name_ru.keyword": {"value": normalized_name, "boost": 10.0}}},
                    {"term": {"name_en.keyword": {"value": normalized_name, "boost": 10.0}}}
                ],
                "minimum_should_match": 1
            }
        }
        bool_query = {
            "must": [name_query],
            "should": [
                {"terms": {"type": self.GLOBAL_TYPES, "boost": 2.0}}
            ]
        }

        query_structure = {
            "query": {
                "bool": bool_query
            },
            "size": 1
        }
        
        # Добавляем фильтр по объекту если указан
        if object_name:
            bool_query["filter"] = [{"term": {"object": object_name}}]
        
        return query_structure
    
    def build_exact_query(self, element_name: str, object_name: Optional[str] = None, limit: int = 5) -> Dict[str, Any]:
        """Строит fuzzy запрос по имени элемента с поддержкой фильтра по объекту."""
        normalized_name = element_name.lower()
        query_structure = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "bool": {
                                "should": [
                                    {"term": {"name_ru.keyword": {"value": normalized_name, "boost": 10.0}}},
                                    {"term": {"name_en.keyword": {"value": normalized_name, "boost": 10.0}}},
                                    {"term": {"name.keyword": {"value": element_name, "boost": 5.0}}},
                                    {"match": {"name_ru": {"query": element_name, "boost": 3.0}}},
                                    {"match": {"name_en": {"query": element_name, "boost": 3.0}}},
                                    {"wildcard": {"name_ru.keyword": {"value": f"*{normalized_name}*", "boost": 2.0}}},
                                    {"wildcard": {"name_en.keyword": {"value": f"*{normalized_name}*", "boost": 2.0}}}
                                ],
                                "minimum_should_match": 1
                            }
                        }
                    ],
                    "should": [
                        {"terms": {"type": self.GLOBAL_TYPES, "boost": 2.0}}
                    ]
                }
            },
            "size": limit,
            "sort": [
                {"_score": {"order": "desc"}}
            ]
        }
        
        # Добавляем фильтр по объекту если указан
        if object_name:
            query_structure["query"]["bool"]["filter"] = [
                {"term": {"object": object_name}}
            ]
        
        return query_structure
    
    def build_object_query(self, object_name: str, limit: int = 50) -> Dict[str, Any]:
        """Строит запрос для поиска всех элементов объекта."""
        return {
            "query": {
                "bool": {
                    "should": [
                        {"term": {"object": {"value": object_name, "boost": 3.0}}},
                        {"prefix": {"full_path": {"value": f"{object_name}.", "boost": 2.0}}},
                        {"match": {"full_path": {"query": object_name, "boost": 1.5}}}
                    ]
                }
            },
            "size": limit,
            "sort": [
                {"type": {"order": "asc"}},
                {"name.keyword": {"order": "asc"}}
            ]
        }
    
    def _detect_search_type(self, query: str) -> str:
        """Автоматически определяет тип поиска по запросу."""
        # Точный поиск - если запрос содержит точку (метод объекта)
        if "." in query and len(query.split(".")) == 2:
            return "exact"
        
        # Точный поиск - если запрос короткий и не содержит пробелов
        if len(query.split()) == 1 and len(query) < 30:
            return "exact"
        
        # Семантический поиск - если запрос длинный или содержит много слов
        if len(query.split()) > 3 or len(query) > 50:
            return "semantic"
        
        # По умолчанию - обычный поиск
        return "multi_match"
    
    def build_phrase_query(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Строит точный поиск по фразе."""
        return {
            "query": {
                "bool": {
                    "should": [
                        {"match_phrase": {"name": {"query": query, "boost": 5.0}}},
                        {"match_phrase": {"full_path": {"query": query, "boost": 4.0}}},
                        {"match_phrase": {"syntax_ru": {"query": query, "boost": 3.0}}},
                        {"match_phrase": {"syntax_en": {"query": query, "boost": 3.0}}},
                        {"match": {"description": {"query": query, "boost": 2.0}}}
                    ]
                }
            },
            "size": limit,
            "sort": [
                {"_score": {"order": "desc"}}
            ]
        }
    
    def build_multi_match_query(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Строит обычный multi-match поиск."""
        return {
            "query": {
                "bool": {
                    "must": {
                        "multi_match": {
                            "query": query,
                            "fields": [
                                "name^5",
                                "full_path^4", 
                                "syntax_ru^3",
                                "syntax_en^3",
                                "description^2",
                                "parameters.name^1.5",
                                "examples^1"
                            ],
                            "type": "best_fields",
                            "fuzziness": "AUTO"
                        }
                    },
                    "should": [
                        {"match_phrase": {"name": {"query": query, "boost": 2.0}}},
                        {"prefix": {"name": {"value": query, "boost": 1.5}}}
                    ]
                }
            },
            "size": limit,
            "sort": [
                {"_score": {"order": "desc"}}
            ]
        }
    
    def build_fuzzy_query(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Строит нечеткий поиск."""
        return {
            "query": {
                "bool": {
                    "should": [
                        {
                            "multi_match": {
                                "query": query,
                                "fields": [
                                    "name^3",
                                    "full_path^2",
                                    "description^1"
                                ],
                                "fuzziness": 2,
                                "type": "best_fields"
                            }
                        },
                        {
                            "wildcard": {
                                "name.keyword": {
                                    "value": f"*{query}*",
                                    "boost": 1.5
                                }
                            }
                        }
                    ]
                }
            },
            "size": limit,
            "sort": [
                {"_score": {"order": "desc"}}
            ]
        }
    
    def build_semantic_query(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Строит семантический поиск."""
        return {
            "query": {
                "bool": {
                    "should": [
                        {
                            "multi_match": {
                                "query": query,
                                "fields": [
                                    "description^3",
                                    "name^2",
                                    "full_path^2",
                                    "syntax_ru^1.5",
                                    "examples^1",
                                    "parameters.description^1"
                                ],
                                "type": "most_fields",
                                "minimum_should_match": "50%"
                            }
                        },
                        {
                            "match_phrase": {
                                "description": {
                                    "query": query,
                                    "boost": 2.0,
                                    "slop": 3
                                }
                            }
                        }
                    ]
                }
            },
            "size": limit,
            "sort": [
                {"_score": {"order": "desc"}}
            ]
        }
