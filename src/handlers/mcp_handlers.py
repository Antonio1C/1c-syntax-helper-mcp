"""Обработчики MCP запросов."""

from src.models.mcp_models import (
    MCPResponse, Find1CHelpRequest, GetSyntaxInfoRequest, GetQuickReferenceRequest,
    SearchByContextRequest, ListObjectMembersRequest
)
from src.core.elasticsearch import ElasticsearchClient
from src.search.search_service import SearchService
from src.handlers.mcp_formatter import mcp_formatter
from src.core.logging import get_logger

logger = get_logger(__name__)


def _log_mcp_request(tool_name: str, **context):
    """Логирует MCP запрос с контекстом."""
    logger.debug(f"MCP запрос: {tool_name}", extra={"extra_data": {"tool": tool_name, **context}})


def _log_mcp_success(tool_name: str, count: int = None, **context):
    """Логирует успешный MCP ответ."""
    extra = {"tool": tool_name, "status": "success", **context}
    if count is not None:
        extra["results_count"] = count
    logger.debug(f"MCP успех: {tool_name}", extra={"extra_data": extra})


def _log_mcp_error(tool_name: str, error: str, **context):
    """Логирует ошибку MCP запроса."""
    logger.error(f"MCP ошибка: {tool_name} - {error}", 
                extra={"extra_data": {"tool": tool_name, "status": "error", "error": error, **context}})


async def handle_find_1c_help(request: Find1CHelpRequest, es_client: ElasticsearchClient) -> MCPResponse:
    """Универсальный поиск справки по любому элементу 1С."""
    _log_mcp_request("find_1c_help", query=request.query, limit=request.limit)
    
    try:
        search_service = SearchService(es_client)
        results = await search_service.find_help_by_query(request.query, request.limit)
        
        if results.get("error"):
            _log_mcp_error("find_1c_help", results["error"])
            return mcp_formatter.create_error_response("Ошибка поиска", results["error"])
        
        search_results = results.get("results", [])
        
        if not search_results:
            _log_mcp_success("find_1c_help", count=0)
            return mcp_formatter.create_not_found_response(request.query)
        
        content = [mcp_formatter.format_search_header(len(search_results), request.query)]
        
        # Результаты
        for i, result in enumerate(search_results, 1):
            content.append(mcp_formatter.format_search_result(result, i))
        
        _log_mcp_success("find_1c_help", count=len(search_results))
        return mcp_formatter.create_success_response(content)
        
    except Exception as e:
        _log_mcp_error("find_1c_help", str(e))
        return mcp_formatter.create_error_response("Внутренняя ошибка поиска", str(e))


async def handle_get_syntax_info(request: GetSyntaxInfoRequest, es_client: ElasticsearchClient) -> MCPResponse:
    """Получить полную техническую информацию об элементе."""
    _log_mcp_request("get_syntax_info", element_name=request.element_name, 
                    object_name=request.object_name, include_examples=request.include_examples)
    
    try:
        search_service = SearchService(es_client)
        result = await search_service.get_detailed_syntax_info(
            request.element_name, 
            request.object_name, 
            request.include_examples
        )

        if result and result.get("ambiguous"):
            _log_mcp_success("get_syntax_info", count=0, ambiguous=True)
            return mcp_formatter.create_success_response([{
                "type": "text",
                "text": result["message"]
            }])
        
        if not result:
            element_context = f" объекта '{request.object_name}'" if request.object_name else ""
            _log_mcp_success("get_syntax_info", count=0)
            return mcp_formatter.create_not_found_response(f"Элемент '{request.element_name}'{element_context}")
        
        # Форматируем детальную информацию
        text = mcp_formatter.format_syntax_info(result)
        
        # Добавляем примеры если нужно
        if request.include_examples and result.get('examples'):
            examples = result['examples']
            if isinstance(examples, list) and examples:
                text += "💡 **Примеры:**\n"
                for example in examples[:2]:  # Максимум 2 примера
                    text += f"   ```\n   {example}\n   ```\n"
        
        _log_mcp_success("get_syntax_info", count=1, has_examples=bool(result.get('examples')))
        return mcp_formatter.create_success_response([{
            "type": "text",
            "text": text
        }])
        
    except Exception as e:
        _log_mcp_error("get_syntax_info", str(e))
        return mcp_formatter.create_error_response("Ошибка получения информации", str(e))


async def handle_get_quick_reference(request: GetQuickReferenceRequest, es_client: ElasticsearchClient) -> MCPResponse:
    """Получить краткую справку."""
    _log_mcp_request("get_quick_reference", element_name=request.element_name, object_name=request.object_name)
    
    try:
        search_service = SearchService(es_client)
        result = await search_service.get_detailed_syntax_info(
            request.element_name, 
            request.object_name, 
            include_examples=False
        )

        if result and result.get("ambiguous"):
            _log_mcp_success("get_quick_reference", count=0, ambiguous=True)
            return mcp_formatter.create_success_response([{
                "type": "text",
                "text": result["message"]
            }])
        
        if not result:
            _log_mcp_success("get_quick_reference", count=0)
            return mcp_formatter.create_not_found_response(f"⚡ Элемент '{request.element_name}'")
        
        text = mcp_formatter.format_quick_reference(result)
        
        _log_mcp_success("get_quick_reference", count=1)
        return mcp_formatter.create_success_response([{
            "type": "text",
            "text": text
        }])
        
    except Exception as e:
        _log_mcp_error("get_quick_reference", str(e))
        return mcp_formatter.create_error_response("Ошибка получения справки", str(e))


async def handle_search_by_context(request: SearchByContextRequest, es_client: ElasticsearchClient) -> MCPResponse:
    """Поиск с фильтром по контексту."""
    _log_mcp_request("search_by_context", query=request.query, context=request.context, 
                    object_name=request.object_name, limit=request.limit)
    
    try:
        search_service = SearchService(es_client)
        results = await search_service.search_with_context_filter(
            request.query,
            request.context, 
            request.object_name,
            request.limit
        )
        
        if results.get("error"):
            _log_mcp_error("search_by_context", results["error"])
            return mcp_formatter.create_error_response("Ошибка поиска", results["error"])
        
        search_results = results.get("results", [])
        
        if not search_results:
            context_name = {"global": "глобальном", "object": "объектном", "all": "любом"}
            context_text = context_name.get(request.context, request.context)
            _log_mcp_success("search_by_context", count=0, context=request.context)
            return mcp_formatter.create_not_found_response(request.query, f"{context_text} контексте")
        
        text = mcp_formatter.format_context_search(search_results, request.query, request.context)
        
        _log_mcp_success("search_by_context", count=len(search_results), context=request.context)
        return mcp_formatter.create_success_response([{
            "type": "text",
            "text": text
        }])
        
    except Exception as e:
        _log_mcp_error("search_by_context", str(e))
        return mcp_formatter.create_error_response("Ошибка поиска", str(e))


async def handle_list_object_members(request: ListObjectMembersRequest, es_client: ElasticsearchClient) -> MCPResponse:
    """Получить список элементов объекта."""
    _log_mcp_request("list_object_members", object_name=request.object_name, member_type=request.member_type, limit=request.limit)
    try:
        search_service = SearchService(es_client)
        result = await search_service.get_object_members_list(
            request.object_name,
            request.member_type,
            request.limit
        )

        if result.get("error"):
            _log_mcp_error("list_object_members", result["error"])
            return mcp_formatter.create_error_response("Ошибка", result["error"])

        methods = result.get("methods", [])
        properties = result.get("properties", [])
        events = result.get("events", [])
        total = result.get("total", 0)

        if total == 0:
            _log_mcp_success("list_object_members", count=0)
            return mcp_formatter.create_not_found_response(f"Объект '{request.object_name}' не найден или не содержит элементов")

        text = mcp_formatter.format_object_members_list(
            request.object_name,
            request.member_type,
            methods,
            properties,
            events,
            total
        )

        _log_mcp_success("list_object_members", count=total)
        return mcp_formatter.create_success_response([{
            "type": "text",
            "text": text
        }])

    except Exception as e:
        _log_mcp_error("list_object_members", str(e))
        return mcp_formatter.create_error_response("Ошибка получения элементов", str(e))