"""Модели для MCP Protocol."""

from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
from enum import Enum


class MCPToolType(str, Enum):
    """Типы MCP инструментов."""
    SEARCH_1C_SYNTAX = "search_1c_syntax"
    GET_1C_FUNCTION_DETAILS = "get_1c_function_details"  
    GET_1C_OBJECT_INFO = "get_1c_object_info"


class DocumentationType(str, Enum):
    """Типы документации 1С."""
    GLOBAL_FUNCTION = "global_function"
    GLOBAL_PROCEDURE = "global_procedure"
    OBJECT_METHOD = "object_method"
    OBJECT_PROPERTY = "object_property"
    OBJECT_EVENT = "object_event"
    OBJECT = "object"


class MCPRequest(BaseModel):
    """Базовая модель MCP запроса."""
    tool: MCPToolType
    arguments: Dict[str, Any]


class SearchRequest(BaseModel):
    """Модель запроса поиска."""
    query: str = Field(..., description="Поисковый запрос")
    limit: Optional[int] = Field(10, description="Максимальное количество результатов")


class FunctionDetailsRequest(BaseModel):
    """Модель запроса деталей функции."""
    function_name: str = Field(..., description="Имя функции")


class ObjectInfoRequest(BaseModel):
    """Модель запроса информации об объекте."""
    object_name: str = Field(..., description="Имя объекта")


class ParameterInfo(BaseModel):
    """Информация о параметре."""
    name: str
    type: str
    description: str
    required: bool = True


class FunctionInfo(BaseModel):
    """Информация о функции/методе."""
    type: DocumentationType
    name: str
    object: Optional[str] = None
    syntax_ru: str
    syntax_en: Optional[str] = None
    description: str
    parameters: List[ParameterInfo] = []
    return_type: Optional[str] = None
    version_from: Optional[str] = None
    examples: List[str] = []
    source_file: Optional[str] = None


class ObjectInfo(BaseModel):
    """Информация об объекте."""
    object: str
    description: str
    methods: List[str] = []
    properties: List[str] = []
    events: List[str] = []
    version_from: Optional[str] = None


class MCPResponse(BaseModel):
    """Базовая модель MCP ответа."""
    content: Union[List[FunctionInfo], ObjectInfo, Dict[str, Any]]
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
    version: str = "1.0.0"
