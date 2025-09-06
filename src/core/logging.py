"""Система логирования."""

import logging
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

from src.core.config import settings


class JSONFormatter(logging.Formatter):
    """Форматтер для вывода логов в JSON формате."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Форматирует запись лога в JSON."""
        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Добавляем исключение, если есть
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Добавляем дополнительные поля
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)
            
        return json.dumps(log_data, ensure_ascii=False)


def setup_logging() -> None:
    """Настраивает систему логирования."""
    
    # Создаем директорию для логов
    logs_dir = Path(settings.logs_directory)
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Основной логгер
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, settings.log_level.upper()))
    
    # Очищаем существующие обработчики
    logger.handlers.clear()
    
    # Консольный обработчик
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    if settings.debug:
        # В режиме разработки - простой формат
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    else:
        # В продакшене - JSON формат
        console_formatter = JSONFormatter()
    
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # Файловый обработчик
    file_handler = logging.FileHandler(
        logs_dir / "app.log", 
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(JSONFormatter())
    logger.addHandler(file_handler)
    
    # Обработчик для ошибок
    error_handler = logging.FileHandler(
        logs_dir / "errors.log", 
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(JSONFormatter())
    logger.addHandler(error_handler)
    
    # Настраиваем уровни для внешних библиотек
    logging.getLogger("elasticsearch").setLevel(logging.WARNING)
    logging.getLogger("elastic_transport").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """Получает логгер с указанным именем."""
    return logging.getLogger(name)


# Инициализируем логирование при импорте модуля
setup_logging()
