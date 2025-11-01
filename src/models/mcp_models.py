"""Модели для MCP Protocol."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class MCPToolType(str, Enum):
    """Типы MCP инструментов."""
    FIND_1C_HELP = "find_1c_help"
    GET_SYNTAX_INFO = "get_syntax_info"
    GET_QUICK_REFERENCE = "get_quick_reference"
    SEARCH_BY_CONTEXT = "search_by_context"
    LIST_OBJECT_MEMBERS = "list_object_members"


class DocumentationType(str, Enum):
    """Типы документации 1С."""
    GLOBAL_FUNCTION = "global_function"
    GLOBAL_PROCEDURE = "global_procedure"
    GLOBAL_EVENT = "global_event"
    OBJECT_FUNCTION = "object_function"
    OBJECT_PROCEDURE = "object_procedure"
    OBJECT_PROPERTY = "object_property"
    OBJECT_EVENT = "object_event"
    OBJECT_CONSTRUCTOR = "object_constructor"
    OBJECT = "object"


class ContextType(str, Enum):
    """Типы контекстов поиска."""
    GLOBAL = "global"
    OBJECT = "object"
    ALL = "all"


class MemberType(str, Enum):
    """Типы элементов объекта."""
    ALL = "all"
    METHODS = "methods"
    PROPERTIES = "properties"
    EVENTS = "events"


class MCPRequest(BaseModel):
    """Базовая модель MCP запроса."""
    tool: MCPToolType
    arguments: Dict[str, Any]


class Find1CHelpRequest(BaseModel):
    """Модель запроса универсального поиска справки."""
    query: str = Field(..., description="Поисковый запрос")
    limit: Optional[int] = Field(5, description="Максимальное количество результатов")


class GetSyntaxInfoRequest(BaseModel):
    """Модель запроса полной технической информации."""
    element_name: str = Field(..., description="Точное имя элемента")
    object_name: Optional[str] = Field(None, description="Имя объекта для методов/свойств")
    include_examples: Optional[bool] = Field(True, description="Включать примеры")


class GetQuickReferenceRequest(BaseModel):
    """Модель запроса краткой справки."""
    element_name: str = Field(..., description="Имя элемента")
    object_name: Optional[str] = Field(None, description="Имя объекта")


class SearchByContextRequest(BaseModel):
    """Модель запроса поиска с фильтром по контексту."""
    query: str = Field(..., description="Поисковый запрос")
    context: ContextType = Field(..., description="Контекст поиска")
    object_name: Optional[str] = Field(None, description="Конкретный объект для фильтрации")
    limit: Optional[int] = Field(10, description="Максимальное количество результатов")


class ListObjectMembersRequest(BaseModel):
    """Модель запроса списка элементов объекта."""
    object_name: str = Field(..., description="Имя объекта")
    member_type: MemberType = Field(MemberType.ALL, description="Тип элементов")
    limit: Optional[int] = Field(50, description="Максимальное количество результатов")


class MCPResponse(BaseModel):
    """Базовая модель MCP ответа."""
    content: List[Dict[str, str]]
    error: Optional[str] = None


class MCPToolParameter(BaseModel):
    """Параметр MCP инструмента."""
    name: str
    type: str = "string"
    description: str
    required: bool = True


class MCPTool(BaseModel):
    """Описание MCP инструмента."""
    name: MCPToolType
    description: str
    parameters: List[MCPToolParameter] = []


class MCPToolsResponse(BaseModel):
    """Ответ со списком доступных MCP инструментов."""
    tools: List[MCPTool]


class HealthResponse(BaseModel):
    """Модель ответа health check."""
    status: str
    elasticsearch: bool
    index_exists: bool
    documents_count: Optional[int] = None
    indexing_status: Optional[str] = None
    indexing_active: Optional[bool] = None
    version: str = "1.0.0"
