"""Обработчики MCP запросов."""

from src.models.mcp_models import (
    MCPResponse, SearchRequest, FunctionDetailsRequest, ObjectInfoRequest
)
from src.search.search_service import search_service
from src.core.logging import get_logger

logger = get_logger(__name__)


async def handle_search(request: SearchRequest) -> MCPResponse:
    """Обработка поиска по синтаксису."""
    logger.info(f"Поиск: {request.query}")
    
    try:
        # Выполняем поиск через сервис
        search_results = await search_service.search_1c_syntax(
            query=request.query,
            limit=getattr(request, 'limit', 10),
            search_type="auto"
        )
        
        # Проверяем наличие ошибок
        if search_results.get("error"):
            return MCPResponse(
                content=[],
                error=f"Ошибка поиска: {search_results['error']}"
            )
        
        # Форматируем результаты для MCP
        results = search_results.get("results", [])
        
        if not results:
            return MCPResponse(
                content=[{
                    "type": "text",
                    "text": f"По запросу '{request.query}' ничего не найдено."
                }]
            )
        
        # Формируем ответ с результатами
        content = []
        
        # Добавляем заголовок с информацией о поиске
        content.append({
            "type": "text",
            "text": f"**Результаты поиска по запросу:** `{request.query}`\n"
                   f"**Найдено:** {len(results)} из {search_results.get('total', 0)}\n"
                   f"**Время поиска:** {search_results.get('search_time_ms', 0)}ms\n"
        })
        
        # Добавляем результаты
        for i, result in enumerate(results[:10], 1):  # Ограничиваем 10 результатами
            content.append({
                "type": "text", 
                "text": _format_search_result(result, i)
            })
        
        return MCPResponse(content=content)
        
    except Exception as e:
        logger.error(f"Ошибка обработки поиска: {e}")
        return MCPResponse(
            content=[],
            error=f"Внутренняя ошибка поиска: {str(e)}"
        )


async def handle_function_details(request: FunctionDetailsRequest) -> MCPResponse:
    """Обработка запроса деталей функции."""
    logger.info(f"Детали функции: {request.function_name}")
    
    try:
        # Получаем детали функции
        function_details = await search_service.get_function_details(request.function_name)
        
        if not function_details:
            return MCPResponse(
                content=[{
                    "type": "text",
                    "text": f"Функция '{request.function_name}' не найдена."
                }]
            )
        
        # Форматируем детали для MCP
        content = [{
            "type": "text",
            "text": _format_function_details(function_details)
        }]
        
        return MCPResponse(content=content)
        
    except Exception as e:
        logger.error(f"Ошибка получения деталей функции: {e}")
        return MCPResponse(
            content=[],
            error=f"Ошибка получения деталей функции: {str(e)}"
        )


async def handle_object_info(request: ObjectInfoRequest) -> MCPResponse:
    """Обработка запроса информации об объекте."""
    logger.info(f"Информация об объекте: {request.object_name}")
    
    try:
        # Получаем информацию об объекте
        object_info = await search_service.get_object_info(request.object_name)
        
        if object_info.get("error"):
            return MCPResponse(
                content=[],
                error=f"Ошибка получения информации об объекте: {object_info['error']}"
            )
        
        # Форматируем информацию для MCP
        content = [{
            "type": "text",
            "text": _format_object_info(object_info)
        }]
        
        return MCPResponse(content=content)
        
    except Exception as e:
        logger.error(f"Ошибка получения информации об объекте: {e}")
        return MCPResponse(
            content=[],
            error=f"Ошибка получения информации об объекте: {str(e)}"
        )


def _format_search_result(result: dict, index: int) -> str:
    """Форматирует результат поиска для вывода."""
    name = result.get("name", "")
    obj = result.get("object", "")
    full_path = result.get("full_path", "")
    description = result.get("description", "")
    doc_type = result.get("type", "")
    syntax_ru = result.get("syntax", {}).get("russian", "")
    
    # Формируем заголовок
    title = f"{index}. **{name}**"
    if obj:
        title += f" _(объект: {obj})_"
    
    # Добавляем тип документа
    type_emoji = {
        "global_function": "🔧",
        "function": "⚙️", 
        "method": "🔨",
        "property": "📋",
        "event": "⚡",
    }
    emoji = type_emoji.get(doc_type, "📄")
    
    result_text = f"\n---\n{emoji} {title}\n"
    
    # Добавляем синтаксис
    if syntax_ru:
        result_text += f"**Синтаксис:** `{syntax_ru}`\n"
    
    # Добавляем описание
    if description:
        # Ограничиваем длину описания
        desc = description[:200] + "..." if len(description) > 200 else description
        result_text += f"**Описание:** {desc}\n"
    
    # Добавляем полный путь если отличается от имени
    if full_path and full_path != name:
        result_text += f"**Полный путь:** `{full_path}`\n"
    
    return result_text


def _format_function_details(details: dict) -> str:
    """Форматирует подробную информацию о функции."""
    name = details.get("name", "")
    description = details.get("description", "")
    
    result_text = f"# 🔧 Функция: {name}\n\n"
    
    # Описание
    if description:
        result_text += f"**Описание:** {description}\n\n"
    
    # Синтаксис
    function_details = details.get("details", {})
    syntax = function_details.get("full_syntax", {})
    
    if syntax.get("russian"):
        result_text += f"**Синтаксис (рус):** `{syntax['russian']}`\n\n"
    
    if syntax.get("english"):
        result_text += f"**Синтаксис (англ):** `{syntax['english']}`\n\n"
    
    # Параметры
    parameters = function_details.get("parameters_detailed", [])
    if parameters:
        result_text += "## Параметры:\n\n"
        for param in parameters:
            required = " *(обязательный)*" if param.get("required") else " *(необязательный)*"
            result_text += f"- **{param.get('name', '')}** ({param.get('type', '')}){required}\n"
            if param.get("description"):
                result_text += f"  {param['description']}\n"
        result_text += "\n"
    
    # Возвращаемое значение
    return_value = function_details.get("return_value", {})
    if return_value.get("type"):
        result_text += f"**Возвращает:** {return_value['type']}\n"
        if return_value.get("description"):
            result_text += f"{return_value['description']}\n"
        result_text += "\n"
    
    # Примеры
    examples = function_details.get("usage_examples", [])
    if examples:
        result_text += "## Примеры использования:\n\n"
        for example in examples[:3]:  # Показываем максимум 3 примера
            result_text += f"```\n{example}\n```\n\n"
    
    return result_text


def _format_object_info(object_info: dict) -> str:
    """Форматирует информацию об объекте."""
    object_name = object_info.get("object", "")
    total = object_info.get("total", 0)
    
    result_text = f"# 📦 Объект: {object_name}\n\n"
    result_text += f"**Всего элементов:** {total}\n\n"
    
    # Методы
    methods = object_info.get("methods", [])
    if methods:
        result_text += f"## 🔨 Методы ({len(methods)}):\n\n"
        for method in methods[:10]:  # Показываем максимум 10 методов
            result_text += f"- **{method.get('name', '')}**"
            if method.get('syntax_ru'):
                result_text += f" - `{method['syntax_ru']}`"
            if method.get('description'):
                desc = method['description'][:100] + "..." if len(method['description']) > 100 else method['description']
                result_text += f"\n  {desc}"
            result_text += "\n"
        result_text += "\n"
    
    # Свойства
    properties = object_info.get("properties", [])
    if properties:
        result_text += f"## 📋 Свойства ({len(properties)}):\n\n"
        for prop in properties[:10]:  # Показываем максимум 10 свойств
            result_text += f"- **{prop.get('name', '')}** ({prop.get('type', '')})"
            if prop.get('description'):
                desc = prop['description'][:100] + "..." if len(prop['description']) > 100 else prop['description']
                result_text += f" - {desc}"
            result_text += "\n"
        result_text += "\n"
    
    # События
    events = object_info.get("events", [])
    if events:
        result_text += f"## ⚡ События ({len(events)}):\n\n"
        for event in events[:10]:  # Показываем максимум 10 событий
            result_text += f"- **{event.get('name', '')}**"
            if event.get('description'):
                desc = event['description'][:100] + "..." if len(event['description']) > 100 else event['description']
                result_text += f" - {desc}"
            result_text += "\n"
        result_text += "\n"
    
    return result_text
