"""Форматирование результатов поиска для MCP протокола."""

from typing import List, Dict, Any, Optional


class SearchFormatter:
    """Форматировщик результатов поиска для MCP протокола."""
    
    def format_search_results(self, ranked_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Форматирует результаты поиска для MCP.
        
        Args:
            ranked_results: Отранжированные результаты поиска
        
        Returns:
            Список отформатированных результатов
        """
        formatted_results = []
        
        for result in ranked_results:
            doc = result["document"]
            formatted_doc = self._format_document(doc)
            
            # Добавляем метаинформацию о ранжировании
            formatted_doc["_score"] = round(result["score"], 3)
            formatted_doc["_relevance"] = self._calculate_relevance_level(result["score"])
            
            formatted_results.append(formatted_doc)
        
        return formatted_results
    
    def format_function_details(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Форматирует подробную информацию о функции."""
        formatted = self._format_document(doc)
        
        # Добавляем дополнительные детали для функции
        formatted["details"] = {
            "full_syntax": {
                "russian": doc.get("syntax_ru", ""),
                "english": doc.get("syntax_en", "")
            },
            "parameters_detailed": self._format_parameters_detailed(doc.get("parameters", [])),
            "usage_examples": doc.get("examples", []),
            "return_value": {
                "type": doc.get("return_type", ""),
                "description": self._get_return_description(doc)
            },
            "version_info": {
                "available_from": doc.get("version_from", ""),
                "source_file": doc.get("source_file", "")
            }
        }
        
        return formatted
    
    def format_object_method(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Форматирует метод объекта."""
        return {
            "name": doc.get("name", ""),
            "syntax_ru": doc.get("syntax_ru", ""),
            "syntax_en": doc.get("syntax_en", ""),
            "description": doc.get("description", ""),
            "parameters": self._format_parameters_brief(doc.get("parameters", [])),
            "return_type": doc.get("return_type", ""),
            "type": "method"
        }
    
    def format_object_property(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Форматирует свойство объекта."""
        return {
            "name": doc.get("name", ""),
            "type": doc.get("return_type", ""),
            "description": doc.get("description", ""),
            "access": self._determine_property_access(doc),
            "type": "property"
        }
    
    def format_object_event(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Форматирует событие объекта."""
        return {
            "name": doc.get("name", ""),
            "description": doc.get("description", ""),
            "parameters": self._format_parameters_brief(doc.get("parameters", [])),
            "type": "event"
        }
    
    def _format_document(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Базовое форматирование документа."""
        return {
            "type": doc.get("type", ""),
            "name": doc.get("name", ""),
            "object": doc.get("object", ""),
            "full_path": doc.get("full_path", ""),
            "description": doc.get("description", ""),
            "syntax": {
                "russian": doc.get("syntax_ru", ""),
                "english": doc.get("syntax_en", "")
            },
            "parameters": self._format_parameters_brief(doc.get("parameters", [])),
            "return_type": doc.get("return_type", ""),
            "examples": doc.get("examples", []),
            "version_from": doc.get("version_from", "")
        }
    
    def _format_parameters_brief(self, parameters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Краткое форматирование параметров."""
        if not parameters:
            return []
        
        formatted_params = []
        for param in parameters:
            formatted_params.append({
                "name": param.get("name", ""),
                "type": param.get("type", ""),
                "required": param.get("required", False),
                "description": param.get("description", "")
            })
        
        return formatted_params
    
    def _format_parameters_detailed(self, parameters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Подробное форматирование параметров."""
        if not parameters:
            return []
        
        formatted_params = []
        for param in parameters:
            formatted_param = {
                "name": param.get("name", ""),
                "type": param.get("type", ""),
                "required": param.get("required", False),
                "description": param.get("description", ""),
                "default_value": param.get("default_value", ""),
                "constraints": param.get("constraints", "")
            }
            
            # Добавляем дополнительную информацию если есть
            if param.get("enum_values"):
                formatted_param["possible_values"] = param["enum_values"]
            
            formatted_params.append(formatted_param)
        
        return formatted_params
    
    def _get_return_description(self, doc: Dict[str, Any]) -> str:
        """Получает описание возвращаемого значения."""
        # Ищем описание возвращаемого значения в описании функции
        description = doc.get("description", "")
        
        # Простой поиск ключевых слов
        return_keywords = [
            "возвращает", "возвращаемое значение", "результат",
            "returns", "return value", "result"
        ]
        
        for keyword in return_keywords:
            if keyword.lower() in description.lower():
                # Находим предложение с ключевым словом
                sentences = description.split(".")
                for sentence in sentences:
                    if keyword.lower() in sentence.lower():
                        return sentence.strip()
        
        return ""
    
    def _determine_property_access(self, doc: Dict[str, Any]) -> str:
        """Определяет тип доступа к свойству."""
        description = doc.get("description", "").lower()
        
        if "только чтение" in description or "read-only" in description:
            return "readonly"
        elif "только запись" in description or "write-only" in description:
            return "writeonly"
        else:
            return "readwrite"
    
    def _calculate_relevance_level(self, score: float) -> str:
        """Вычисляет уровень релевантности."""
        if score >= 10.0:
            return "very_high"
        elif score >= 5.0:
            return "high"
        elif score >= 2.0:
            return "medium"
        elif score >= 1.0:
            return "low"
        else:
            return "very_low"
