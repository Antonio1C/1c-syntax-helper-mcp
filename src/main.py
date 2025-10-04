"""Главное приложение MCP сервера синтаксис-помощника 1С."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import settings
from src.core.logging import get_logger
from src.core.elasticsearch import es_client
from src.core.metrics import get_metrics_collector, get_system_monitor
from src.core.dependency_injection import setup_dependencies
from src.core.startup import auto_index_on_startup
from src.core.validation import ValidationError
from src.parsers.hbk_parser import HBKParserError

# Import routers
from src.api.routes.health import router as health_router
from src.api.routes.index import router as index_router
from src.api.routes.metrics import router as metrics_router
from src.api.routes.mcp import router as mcp_router

# Import middleware and exception handlers
from src.api.middleware.rate_limit import rate_limit_middleware
from src.api.middleware.error_handler import (
    validation_exception_handler,
    parser_exception_handler,
    general_exception_handler
)

logger = get_logger(__name__)



@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения."""
    logger.info("Запуск MCP сервера синтаксис-помощника 1С")
    
    metrics = get_metrics_collector()
    monitor = get_system_monitor()
    
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

# Добавляем rate limiting middleware
app.middleware("http")(rate_limit_middleware)

# Регистрируем обработчики исключений
app.add_exception_handler(ValidationError, validation_exception_handler)
app.add_exception_handler(HBKParserError, parser_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Подключаем роутеры
app.include_router(health_router)
app.include_router(index_router)
app.include_router(metrics_router)
app.include_router(mcp_router)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.main:app",
        host=settings.server.host,
        port=settings.server.port,
        log_level=settings.server.log_level.lower(),
        reload=settings.debug
    )
