"""Главное приложение MCP сервера синтаксис-помощника 1С."""

import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.core.config import settings
from src.core.logging import get_logger
from src.core.elasticsearch import es_client
from src.core.validation import ValidationError
from src.core.rate_limiter import get_rate_limiter, RateLimitExceeded
from src.core.metrics import get_metrics_collector, get_system_monitor
from src.core.dependency_injection import setup_dependencies, get_container
from src.parsers.hbk_parser import HBKParser, HBKParserError
from src.parsers.indexer import indexer
from src.models.mcp_models import (
    MCPRequest, MCPResponse, HealthResponse, 
    MCPToolsResponse, MCPTool, MCPToolParameter, MCPToolType,
    SearchRequest, FunctionDetailsRequest, ObjectInfoRequest
)
from src.handlers.mcp_handlers import handle_search, handle_function_details, handle_object_info

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения."""
    # Startup
    logger = get_logger(__name__)
    metrics = get_metrics_collector()
    monitor = get_system_monitor()
    
    logger.info("Запуск MCP сервера синтаксис-помощника 1С")
    
    # Настройка dependency injection
    setup_dependencies()
    
    # Запуск мониторинга системы
    await monitor.start_monitoring(interval=60)
    
    # Подключаемся к Elasticsearch
    connected = await es_client.connect()
    if not connected:
        logger.error("Не удалось подключиться к Elasticsearch")
        await metrics.increment("startup.elasticsearch.connection_failed")
    else:
        logger.info("Успешно подключились к Elasticsearch")
        await metrics.increment("startup.elasticsearch.connection_success")
        
        # Проверяем наличие .hbk файла и запускаем автоиндексацию
        await auto_index_on_startup()
    
    await metrics.increment("startup.completed")
    
    yield
    
    # Shutdown
    logger.info("Остановка MCP сервера")
    await monitor.stop_monitoring()
    await es_client.disconnect()
    await metrics.increment("shutdown.completed")


async def auto_index_on_startup():
    """Автоматическая индексация при запуске, если найден .hbk файл."""
    try:
        from pathlib import Path
        
        # Ищем .hbk файлы в директории данных
        hbk_dir = Path(settings.data.hbk_directory)
        if not hbk_dir.exists():
            logger.warning(f"Директория .hbk файлов не найдена: {hbk_dir}")
            return
        
        hbk_files = list(hbk_dir.glob("*.hbk"))
        if not hbk_files:
            logger.info(f"Файлы .hbk не найдены в {hbk_dir}. Индексация будет выполнена при загрузке файла.")
            return
        
        # Проверяем, нужна ли индексация
        index_exists = await es_client.index_exists()
        docs_count = await es_client.get_documents_count() if index_exists else 0
        
        if index_exists and docs_count and docs_count > 0:
            logger.info(f"Индекс уже существует с {docs_count} документами. Пропускаем автоиндексацию.")
            return
        
        # Запускаем индексацию первого найденного файла
        hbk_file = hbk_files[0]
        logger.info(f"Запускаем автоматическую индексацию файла: {hbk_file}")
        
        success = await index_hbk_file(str(hbk_file))
        if success:
            logger.info("Автоматическая индексация завершена успешно")
        else:
            logger.error("Ошибка автоматической индексации")
            
    except Exception as e:
        logger.error(f"Ошибка при автоматической индексации: {e}")


async def index_hbk_file(file_path: str) -> bool:
    """Индексирует .hbk файл в Elasticsearch."""
    try:
        logger.info(f"Начинаем индексацию файла: {file_path}")
        
        # Парсим .hbk файл
        parser = HBKParser()
        parsed_hbk = parser.parse_file(file_path)
        
        if not parsed_hbk:
            logger.error("Ошибка парсинга .hbk файла")
            return False
        
        if not parsed_hbk.documentation:
            logger.warning("В файле не найдена документация для индексации")
            return False
        
        logger.info(f"Найдено {len(parsed_hbk.documentation)} документов для индексации")
        
        # Индексируем в Elasticsearch
        success = await indexer.reindex_all(parsed_hbk)
        
        if success:
            docs_count = await es_client.get_documents_count()
            logger.info(f"Индексация завершена. Документов в индексе: {docs_count}")
        
        return success
        
    except Exception as e:
        logger.error(f"Ошибка индексации файла {file_path}: {e}")
        return False


# Создаем приложение FastAPI
app = FastAPI(
    title="1C Syntax Helper MCP Server",
    description="MCP сервер для поиска по синтаксису 1С",
    version="1.0.0",
    lifespan=lifespan
)

# Добавляем CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware для rate limiting
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Middleware для ограничения скорости запросов."""
    rate_limiter = get_rate_limiter()
    metrics = get_metrics_collector()
    
    # Получаем IP клиента
    client_ip = request.client.host if request.client else "unknown"
    
    try:
        # Проверяем rate limit
        await rate_limiter.check_rate_limit(client_ip)
        
        # Измеряем время выполнения запроса
        start_time = time.time()
        response = await call_next(request)
        response_time = time.time() - start_time
        
        # Записываем метрики
        await metrics.record_timer("request.duration", response_time, 
                                 {"method": request.method, "path": request.url.path})
        await metrics.update_performance_stats(
            success=200 <= response.status_code < 400,
            response_time=response_time
        )
        
        return response
        
    except RateLimitExceeded as e:
        await metrics.increment("requests.rate_limited", labels={"client_ip": client_ip})
        
        return JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded",
                "message": str(e),
                "retry_after": e.retry_after
            },
            headers={"Retry-After": str(e.retry_after)}
        )
    except Exception as e:
        await metrics.increment("requests.middleware_error")
        logger.error(f"Error in rate limit middleware: {e}")
        
        response = await call_next(request)
        return response


# Обработчик глобальных исключений
@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """Обработчик ошибок валидации."""
    metrics = get_metrics_collector()
    await metrics.increment("errors.validation")
    
    return JSONResponse(
        status_code=400,
        content={
            "error": "Validation error",
            "message": str(exc)
        }
    )


@app.exception_handler(HBKParserError)
async def parser_exception_handler(request: Request, exc: HBKParserError):
    """Обработчик ошибок парсера."""
    metrics = get_metrics_collector()
    await metrics.increment("errors.parser")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Parser error", 
            "message": str(exc)
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Общий обработчик исключений."""
    metrics = get_metrics_collector()
    await metrics.increment("errors.general")
    
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred"
        }
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Проверка состояния системы."""
    metrics = get_metrics_collector()
    
    async with metrics.timer("health_check.duration"):
        es_connected = await es_client.is_connected()
        index_exists = await es_client.index_exists() if es_connected else False
        docs_count = await es_client.get_documents_count() if index_exists else None
    
    await metrics.increment("health_check.requests")
    
    return HealthResponse(
        status="healthy" if es_connected else "unhealthy",
        elasticsearch=es_connected,
        index_exists=index_exists,
        documents_count=docs_count
    )


@app.get("/index/status")
async def index_status():
    """Статус индексации."""
    es_connected = await es_client.is_connected()
    index_exists = await es_client.index_exists() if es_connected else False
    docs_count = await es_client.get_documents_count() if index_exists else 0
    
    return {
        "elasticsearch_connected": es_connected,
        "index_exists": index_exists,
        "documents_count": docs_count,
        "index_name": settings.elasticsearch.index_name
    }


@app.post("/index/rebuild")
async def rebuild_index():
    """Переиндексация документации из .hbk файла."""
    try:
        from pathlib import Path
        
        # Проверяем подключение к Elasticsearch
        if not await es_client.is_connected():
            raise HTTPException(
                status_code=503,
                detail="Elasticsearch недоступен"
            )
        
        # Ищем .hbk файлы
        hbk_dir = Path(settings.data.hbk_directory)
        if not hbk_dir.exists():
            raise HTTPException(
                status_code=400,
                detail=f"Директория .hbk файлов не найдена: {hbk_dir}"
            )
        
        hbk_files = list(hbk_dir.glob("*.hbk"))
        if not hbk_files:
            raise HTTPException(
                status_code=400,
                detail=f"Файлы .hbk не найдены в {hbk_dir}"
            )
        
        # Индексируем первый найденный файл
        hbk_file = hbk_files[0]
        logger.info(f"Начинаем переиндексацию файла: {hbk_file}")
        
        success = await index_hbk_file(str(hbk_file))
        
        if success:
            docs_count = await es_client.get_documents_count()
            return {
                "status": "success",
                "message": "Переиндексация завершена успешно",
                "file": str(hbk_file),
                "documents_count": docs_count
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Ошибка переиндексации"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка переиндексации: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Внутренняя ошибка: {str(e)}"
        )


@app.get("/mcp/tools", response_model=MCPToolsResponse)
async def get_mcp_tools():
    """Возвращает список доступных MCP инструментов."""
    tools = [
        MCPTool(
            name=MCPToolType.SEARCH_1C_SYNTAX,
            description="Поиск по синтаксису 1С: функции, процедуры, методы объектов",
            parameters=[
                MCPToolParameter(
                    name="query",
                    type="string", 
                    description="Поисковый запрос (например: 'СтрДлина', 'ТаблицаЗначений.Добавить')",
                    required=True
                ),
                MCPToolParameter(
                    name="limit",
                    type="number",
                    description="Максимальное количество результатов (по умолчанию: 10)",
                    required=False
                )
            ]
        ),
        MCPTool(
            name=MCPToolType.GET_1C_FUNCTION_DETAILS,
            description="Получение подробной информации о функции или процедуре 1С",
            parameters=[
                MCPToolParameter(
                    name="function_name",
                    type="string",
                    description="Точное имя функции или процедуры",
                    required=True
                )
            ]
        ),
        MCPTool(
            name=MCPToolType.GET_1C_OBJECT_INFO,
            description="Получение информации об объекте 1С: все методы, свойства и события",
            parameters=[
                MCPToolParameter(
                    name="object_name", 
                    type="string",
                    description="Имя объекта 1С (например: 'ТаблицаЗначений', 'Запрос')",
                    required=True
                )
            ]
        )
    ]
    
    return MCPToolsResponse(tools=tools)


@app.post("/mcp", response_model=MCPResponse)
async def mcp_endpoint(request: MCPRequest):
    """Основной MCP endpoint."""
    logger.info(f"Получен MCP запрос: {request.tool}")
    
    try:
        # Проверяем подключение к Elasticsearch
        if not await es_client.is_connected():
            raise HTTPException(
                status_code=503, 
                detail="Elasticsearch недоступен"
            )
        
        # Маршрутизируем запрос
        if request.tool == "search_1c_syntax":
            return await handle_search(SearchRequest(**request.arguments))
        elif request.tool == "get_1c_function_details":
            return await handle_function_details(FunctionDetailsRequest(**request.arguments))
        elif request.tool == "get_1c_object_info":
            return await handle_object_info(ObjectInfoRequest(**request.arguments))
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Неизвестный инструмент: {request.tool}"
            )
            
    except Exception as e:
        logger.error(f"Ошибка обработки MCP запроса: {e}")
        return MCPResponse(content=[], error=str(e))


@app.get("/metrics")
async def get_metrics():
    """Получение метрик системы."""
    metrics = get_metrics_collector()
    rate_limiter = get_rate_limiter()
    
    all_metrics = await metrics.get_all_metrics()
    performance_stats = metrics.performance_stats
    global_rate_stats = rate_limiter.get_global_stats()
    
    return {
        "metrics": all_metrics,
        "performance": {
            "total_requests": performance_stats.total_requests,
            "successful_requests": performance_stats.successful_requests,
            "failed_requests": performance_stats.failed_requests,
            "success_rate": (performance_stats.successful_requests / max(performance_stats.total_requests, 1)) * 100,
            "avg_response_time": performance_stats.avg_response_time,
            "max_response_time": performance_stats.max_response_time,
            "min_response_time": performance_stats.min_response_time if performance_stats.min_response_time != float('inf') else 0,
            "current_active_requests": performance_stats.current_active_requests
        },
        "rate_limiting": global_rate_stats
    }


@app.get("/metrics/{client_id}")
async def get_client_metrics(client_id: str):
    """Получение метрик для конкретного клиента."""
    rate_limiter = get_rate_limiter()
    client_stats = rate_limiter.get_client_stats(client_id)
    
    return {
        "client_id": client_id,
        "rate_limiting": client_stats
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.main:app",
        host=settings.server.host,
        port=settings.server.port,
        log_level=settings.server.log_level.lower(),
        reload=settings.debug
    )
