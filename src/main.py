"""Главное приложение MCP сервера синтаксис-помощника 1С."""

import sys
import argparse
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import settings
from src.core.logging import get_logger
from src.core.validation import ValidationError
from src.parsers.hbk_parser import HBKParserError
from src.core.lifecycle import startup, shutdown

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


def parse_arguments():
    """Парсинг аргументов командной строки."""
    parser = argparse.ArgumentParser(
        description="1C Syntax Helper MCP Server"
    )
    parser.add_argument(
        "--reindex",
        action="store_true",
        help="Принудительная переиндексация при запуске (игнорирует существующие данные)"
    )
    
    # Парсим только известные аргументы, чтобы не конфликтовать с uvicorn
    args, unknown = parser.parse_known_args()
    return args


# Обрабатываем аргументы командной строки
args = parse_arguments()
if args.reindex:
    settings.force_reindex = True
    logger.info("Включена принудительная переиндексация (--reindex)")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения."""
    await startup(app)
    yield
    await shutdown(app)


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
        app,  # Передаем объект напрямую, а не строку
        host=settings.server.host,
        port=settings.server.port,
        log_level=settings.server.log_level.lower(),
        reload=False  # Отключаем reload для прямой передачи объекта
    )
