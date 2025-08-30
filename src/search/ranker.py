"""Система ранжирования результатов поиска."""

from typing import List, Dict, Any
import re


class SearchRanker:
    """Система ранжирования результатов поиска по документации 1С."""
    
    def rank_results(self, hits: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """
        Ранжирует результаты поиска.
        
        Args:
            hits: Результаты поиска из Elasticsearch
            query: Исходный поисковый запрос
        
        Returns:
            Отранжированный список результатов
        """
        if not hits:
            return []
        
        # Извлекаем документы и добавляем дополнительные оценки
        ranked_results = []
        
        for hit in hits:
            doc = hit["_source"]
            base_score = hit["_score"]
            
            # Вычисляем дополнительные факторы ранжирования
            ranking_factors = self._calculate_ranking_factors(doc, query)
            
            # Применяем факторы к базовой оценке
            final_score = self._apply_ranking_factors(base_score, ranking_factors)
            
            ranked_results.append({
                "document": doc,
                "score": final_score,
                "base_score": base_score,
                "ranking_factors": ranking_factors
            })
        
        # Сортируем по финальной оценке
        ranked_results.sort(key=lambda x: x["score"], reverse=True)
        
        return ranked_results
    
    def _calculate_ranking_factors(self, doc: Dict[str, Any], query: str) -> Dict[str, float]:
        """Вычисляет дополнительные факторы ранжирования."""
        factors = {}
        
        # Фактор точного совпадения имени
        factors["exact_name_match"] = self._exact_name_match_factor(doc, query)
        
        # Фактор типа документа (функции важнее свойств)
        factors["doc_type_priority"] = self._doc_type_priority_factor(doc)
        
        # Фактор популярности (на основе длины описания)
        factors["description_quality"] = self._description_quality_factor(doc)
        
        # Фактор полноты информации
        factors["completeness"] = self._completeness_factor(doc)
        
        # Фактор соответствия по синтаксису
        factors["syntax_match"] = self._syntax_match_factor(doc, query)
        
        return factors
    
    def _exact_name_match_factor(self, doc: Dict[str, Any], query: str) -> float:
        """Фактор точного совпадения имени."""
        name = doc.get("name", "").lower()
        full_path = doc.get("full_path", "").lower()
        query_lower = query.lower()
        
        # Полное совпадение имени - максимальный бонус
        if name == query_lower or full_path == query_lower:
            return 3.0
        
        # Начинается с запроса
        if name.startswith(query_lower) or full_path.startswith(query_lower):
            return 2.0
        
        # Содержит запрос
        if query_lower in name or query_lower in full_path:
            return 1.5
        
        return 1.0
    
    def _doc_type_priority_factor(self, doc: Dict[str, Any]) -> float:
        """Фактор приоритета типа документа."""
        doc_type = doc.get("type", "").lower()
        
        # Приоритеты типов документов
        type_priorities = {
            "global_function": 2.0,    # Глобальные функции - высший приоритет
            "function": 1.8,           # Обычные функции
            "method": 1.6,             # Методы объектов
            "property": 1.2,           # Свойства объектов
            "event": 1.1,              # События
            "constant": 1.0,           # Константы
        }
        
        for type_key, priority in type_priorities.items():
            if type_key in doc_type:
                return priority
        
        return 1.0  # По умолчанию
    
    def _description_quality_factor(self, doc: Dict[str, Any]) -> float:
        """Фактор качества описания."""
        description = doc.get("description", "")
        
        if not description:
            return 0.8  # Штраф за отсутствие описания
        
        desc_length = len(description)
        
        # Оптимальная длина описания - от 50 до 500 символов
        if 50 <= desc_length <= 500:
            return 1.3
        elif 20 <= desc_length < 50:
            return 1.1
        elif desc_length > 500:
            return 1.2
        else:
            return 0.9
    
    def _completeness_factor(self, doc: Dict[str, Any]) -> float:
        """Фактор полноты информации."""
        completeness_score = 1.0
        
        # Бонус за наличие синтаксиса
        if doc.get("syntax_ru") or doc.get("syntax_en"):
            completeness_score += 0.3
        
        # Бонус за наличие параметров
        parameters = doc.get("parameters", [])
        if parameters:
            completeness_score += 0.2
            # Дополнительный бонус за описания параметров
            param_descriptions = sum(1 for p in parameters if p.get("description"))
            if param_descriptions > 0:
                completeness_score += 0.1 * (param_descriptions / len(parameters))
        
        # Бонус за примеры
        examples = doc.get("examples", [])
        if examples:
            completeness_score += 0.2
        
        # Бонус за тип возвращаемого значения
        if doc.get("return_type"):
            completeness_score += 0.1
        
        return completeness_score
    
    def _syntax_match_factor(self, doc: Dict[str, Any], query: str) -> float:
        """Фактор соответствия по синтаксису."""
        syntax_ru = doc.get("syntax_ru", "").lower()
        syntax_en = doc.get("syntax_en", "").lower()
        query_lower = query.lower()
        
        # Проверяем вхождение запроса в синтаксис
        if query_lower in syntax_ru or query_lower in syntax_en:
            return 1.4
        
        # Проверяем частичное совпадение
        query_parts = query_lower.split()
        if len(query_parts) > 1:
            matches = 0
            for part in query_parts:
                if part in syntax_ru or part in syntax_en:
                    matches += 1
            
            if matches > 0:
                return 1.0 + (matches / len(query_parts)) * 0.3
        
        return 1.0
    
    def _apply_ranking_factors(
        self,
        base_score: float,
        factors: Dict[str, float]
    ) -> float:
        """Применяет факторы ранжирования к базовой оценке."""
        final_score = base_score
        
        # Веса факторов
        factor_weights = {
            "exact_name_match": 0.4,
            "doc_type_priority": 0.2,
            "description_quality": 0.15,
            "completeness": 0.15,
            "syntax_match": 0.1
        }
        
        # Применяем взвешенные факторы
        for factor_name, factor_value in factors.items():
            weight = factor_weights.get(factor_name, 0.1)
            final_score *= (1.0 + (factor_value - 1.0) * weight)
        
        return final_score
