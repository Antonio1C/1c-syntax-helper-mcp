"""Форматтер ответов MCP."""

from typing import Dict, List, Any
from src.models.mcp_models import MCPResponse


class MCPResponseFormatter:
    """Класс для стандартизированного форматирования ответов MCP."""
    
    @staticmethod
    def create_error_response(message: str, details: str = None) -> MCPResponse:
        """Создаёт стандартизированный ответ с ошибкой."""
        error_text = message
        if details:
            error_text += f": {details}"
        return MCPResponse(content=[], error=error_text)
    
    @staticmethod
    def create_not_found_response(query: str, context: str = "") -> MCPResponse:
        """Создаёт стандартизированный ответ для случая 'не найдено'."""
        if context:
            text = f"По запросу '{query}' в контексте '{context}' ничего не найдено."
        else:
            text = f"По запросу '{query}' ничего не найдено."
        
        return MCPResponse(content=[{"type": "text", "text": text}])
    
    @staticmethod
    def create_success_response(content: List[Dict[str, str]]) -> MCPResponse:
        """Создаёт стандартизированный успешный ответ."""
        return MCPResponse(content=content)
    
    @staticmethod
    def format_search_header(count: int, query: str) -> Dict[str, str]:
        """Форматирует заголовок результатов поиска."""
        return {
            "type": "text",
            "text": f"📋 **Найдено:** {count} элементов по запросу \"{query}\"\n"
        }
    
    @staticmethod
    def format_search_result(result: Dict[str, Any], index: int) -> Dict[str, str]:
        """Форматирует отдельный результат поиска."""
        name = result.get("name", "")
        obj = result.get("object", "")
        description = result.get("description", "")
        
        text = f"{index}. **{name}**"
        if obj:
            text += f" ({obj} → Метод)" if obj != "Global context" else " (Глобальная функция)"
        
        if description:
            desc = description[:100] + "..." if len(description) > 100 else description
            text += f"\n   └ {desc}"
        
        return {"type": "text", "text": text + "\n"}
    
    @staticmethod
    def format_syntax_info(result: Dict[str, Any]) -> str:
        """Форматирует техническую справку."""
        text = f"🔧 **ТЕХНИЧЕСКАЯ СПРАВКА:** {result.get('name', '')}"
        
        if result.get('object'):
            text += f" ({result['object']})"
        
        text += "\n\n"
        
        if result.get('description'):
            text += f"📝 **Описание:**\n   {result['description']}\n\n"
        
        if result.get('syntax_ru'):
            text += f"🔤 **Синтаксис:**\n   `{result['syntax_ru']}`\n\n"
        
        # Параметры
        parameters = result.get('parameters')
        if parameters and isinstance(parameters, list):
            text += "⚙️ **Параметры:**\n"
            for param in parameters:
                if isinstance(param, dict):
                    required = " (обязательный)" if param.get('required') else " (необязательный)"
                    text += f"   • {param.get('name', '')} ({param.get('type', '')}){required}"
                    if param.get('description'):
                        text += f" - {param['description']}"
                    text += "\n"
            text += "\n"
        
        if result.get('return_type'):
            text += f"↩️ **Возвращает:** {result['return_type']}\n\n"
        
        return text
    
    @staticmethod
    def format_quick_reference(result: Dict[str, Any]) -> str:
        """Форматирует краткую справку."""
        name = result.get('name', '')
        syntax = result.get('syntax_ru', '')
        description = result.get('description', '')
        
        text = "⚡ **КРАТКАЯ СПРАВКА**\n\n"
        
        if syntax:
            text += f"`{syntax}`\n"
        else:
            text += f"`{name}`\n"
        
        if description:
            # Берем только первое предложение
            desc = description.split('.')[0] + '.' if '.' in description else description
            desc = desc[:100] + "..." if len(desc) > 100 else desc
            text += f"└ {desc}"
        
        return text
    
    @staticmethod
    def format_context_search(
        search_results: List[Dict[str, Any]], 
        query: str, 
        context: str
    ) -> str:
        """Форматирует результаты контекстного поиска."""
        if context == "object":
            objects = {}
            for result in search_results:
                obj = result.get("object", "Неизвестно")
                if obj not in objects:
                    objects[obj] = []
                objects[obj].append(result)
            
            text = f"🎯 **ПОИСК В КОНТЕКСТЕ:** {context}\n\n"
            text += f"Найдено {len(search_results)} элементов по запросу \"{query}\"\n\n"
            
            for obj, items in list(objects.items())[:5]:  # Максимум 5 объектов
                text += f"📦 **{obj}:**\n"
                for item in items[:3]:  # Максимум 3 элемента на объект
                    name = item.get("name", "")
                    syntax = item.get("syntax_ru", "")
                    desc = item.get("description", "")
                    
                    text += f"   • {name}"
                    if syntax:
                        text += f" - `{syntax}`"
                    if desc:
                        short_desc = desc[:50] + "..." if len(desc) > 50 else desc
                        text += f"\n     {short_desc}"
                    text += "\n"
                text += "\n"
        else:
            text = f"🔍 **ПОИСК В КОНТЕКСТЕ:** {context}\n\n"
            text += f"Найдено {len(search_results)} элементов\n\n"
            
            for i, result in enumerate(search_results[:8], 1):
                name = result.get("name", "")
                syntax = result.get("syntax_ru", "")
                text += f"{i}. **{name}**"
                if syntax:
                    text += f" - `{syntax}`"
                text += "\n"
        
        return text
    
    @staticmethod
    def format_quick_reference(result: dict) -> str:
        """Форматирует краткую справку."""
        name = result.get('name', '')
        syntax = result.get('syntax_ru', '')
        description = result.get('description', '')
        
        text = "⚡ **КРАТКАЯ СПРАВКА**\n\n"
        
        if syntax:
            text += f"`{syntax}`\n"
        else:
            text += f"`{name}`\n"
        
        if description:
            # Берем только первое предложение
            desc = description.split('.')[0] + '.' if '.' in description else description
            desc = desc[:100] + "..." if len(desc) > 100 else desc
            text += f"└ {desc}"
        
        return text

    @staticmethod
    def format_object_members_list(object_name: str, member_type: str, methods: list, 
                                 properties: list, events: list, total: int) -> str:
        """Форматирует список элементов объекта."""
        text = f"📦 **ОБЪЕКТ:** {object_name}\n\n"
        
        # Методы
        if member_type in ["all", "methods"] and methods:
            text += f"🔨 **Методы ({len(methods)}):**\n"
            for method in methods[:20]:  # Максимум 20
                name = method.get("name", "")
                syntax = method.get("syntax_ru", "")
                desc = method.get("description", "")
                
                text += f"   • **{name}**"
                if syntax:
                    text += f" - `{syntax}`"
                if desc:
                    short_desc = desc[:80] + "..." if len(desc) > 80 else desc
                    text += f"\n     {short_desc}"
                text += "\n"
            text += "\n"
        
        # Свойства
        if member_type in ["all", "properties"] and properties:
            text += f"📋 **Свойства ({len(properties)}):**\n"
            for prop in properties[:15]:  # Максимум 15
                name = prop.get("name", "")
                desc = prop.get("description", "")
                
                text += f"   • **{name}**"
                if desc:
                    short_desc = desc[:60] + "..." if len(desc) > 60 else desc
                    text += f" - {short_desc}"
                text += "\n"
            text += "\n"
        
        # События
        if member_type in ["all", "events"] and events:
            text += f"⚡ **События ({len(events)}):**\n"
            for event in events[:10]:  # Максимум 10
                name = event.get("name", "")
                desc = event.get("description", "")
                
                text += f"   • **{name}**"
                if desc:
                    short_desc = desc[:60] + "..." if len(desc) > 60 else desc
                    text += f" - {short_desc}"
                text += "\n"
        
        return text


# Глобальный экземпляр форматтера
mcp_formatter = MCPResponseFormatter()
