"""
Модуль валидации входных данных.
"""

from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import re
from pydantic import BaseModel, validator, Field
from src.core.constants import (
    MAX_SEARCH_RESULTS, 
    SEARCH_TIMEOUT_SECONDS, 
    MIN_SCORE_THRESHOLD,
    MAX_REQUEST_SIZE_MB
)


class ValidationError(Exception):
    """Исключение для ошибок валидации."""
    pass


class SearchRequest(BaseModel):
    """Модель для валидации поискового запроса."""
    
    query: str = Field(..., min_length=1, max_length=1000, description="Поисковый запрос")
    limit: int = Field(default=20, ge=1, le=MAX_SEARCH_RESULTS, description="Максимальное количество результатов")
    offset: int = Field(default=0, ge=0, description="Смещение для пагинации")
    timeout: int = Field(default=SEARCH_TIMEOUT_SECONDS, ge=1, le=300, description="Таймаут в секундах")
    min_score: float = Field(default=MIN_SCORE_THRESHOLD, ge=0.0, le=1.0, description="Минимальный скор для результатов")
    categories: Optional[List[str]] = Field(default=None, description="Фильтр по категориям")
    
    @validator('query')
    def validate_query(cls, v):
        """Валидация поискового запроса."""
        if not v or not v.strip():
            raise ValueError("Поисковый запрос не может быть пустым")
        
        # Проверка на подозрительные символы
        dangerous_chars = ['<', '>', '{', '}', '\\', ';', '&', '|']
        if any(char in v for char in dangerous_chars):
            raise ValueError("Поисковый запрос содержит недопустимые символы")
        
        return v.strip()
    
    @validator('categories')
    def validate_categories(cls, v):
        """Валидация категорий."""
        if v is not None:
            if len(v) > 50:  # Не более 50 категорий
                raise ValueError("Слишком много категорий в фильтре")
            
            for category in v:
                if not isinstance(category, str) or len(category) > 100:
                    raise ValueError("Недопустимое имя категории")
        
        return v


class IndexRequest(BaseModel):
    """Модель для валидации запроса индексации."""
    
    file_path: Optional[str] = Field(default=None, description="Путь к файлу для индексации")
    force_reindex: bool = Field(default=False, description="Принудительная переиндексация")
    batch_size: int = Field(default=100, ge=1, le=1000, description="Размер батча для индексации")
    
    @validator('file_path')
    def validate_file_path(cls, v):
        """Валидация пути к файлу."""
        if v is not None:
            path = Path(v)
            
            # Проверка на path traversal
            if '..' in str(path) or path.is_absolute() == False:
                raise ValueError("Недопустимый путь к файлу")
            
            # Проверка расширения
            allowed_extensions = ['.hbk', '.zip', '.7z']
            if path.suffix.lower() not in allowed_extensions:
                raise ValueError(f"Недопустимое расширение файла. Разрешены: {allowed_extensions}")
        
        return v


class HealthRequest(BaseModel):
    """Модель для валидации запроса проверки здоровья."""
    
    check_elasticsearch: bool = Field(default=True, description="Проверять ли Elasticsearch")
    check_disk_space: bool = Field(default=True, description="Проверять ли дисковое пространство")
    timeout: int = Field(default=10, ge=1, le=60, description="Таймаут проверки")


def validate_elasticsearch_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Валидация конфигурации Elasticsearch.
    
    Args:
        config: Словарь с конфигурацией
        
    Returns:
        Провалидированная конфигурация
        
    Raises:
        ValidationError: При ошибке валидации
    """
    required_fields = ['host', 'port', 'index_name']
    
    for field in required_fields:
        if field not in config:
            raise ValidationError(f"Отсутствует обязательное поле: {field}")
    
    # Валидация хоста
    host = config['host']
    if not isinstance(host, str) or not host.strip():
        raise ValidationError("Host должен быть непустой строкой")
    
    # Простая валидация хоста (домен или IP)
    host_pattern = re.compile(
        r'^(?:(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?|'
        r'(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)|'
        r'localhost)$'
    )
    
    if not host_pattern.match(host):
        raise ValidationError("Недопустимый формат хоста")
    
    # Валидация порта
    port = config['port']
    if not isinstance(port, int) or not (1 <= port <= 65535):
        raise ValidationError("Порт должен быть числом от 1 до 65535")
    
    # Валидация имени индекса
    index_name = config['index_name']
    if not isinstance(index_name, str) or not index_name.strip():
        raise ValidationError("Имя индекса должно быть непустой строкой")
    
    # Имя индекса должно соответствовать правилам Elasticsearch
    index_pattern = re.compile(r'^[a-z0-9][a-z0-9_-]*$')
    if not index_pattern.match(index_name.lower()):
        raise ValidationError("Недопустимое имя индекса Elasticsearch")
    
    return {
        'host': host.strip(),
        'port': port,
        'index_name': index_name.strip().lower(),
        'timeout': config.get('timeout', 30),
        'max_retries': config.get('max_retries', 3)
    }


def validate_file_size(file_path: Path, max_size_mb: int = MAX_REQUEST_SIZE_MB) -> bool:
    """
    Валидация размера файла.
    
    Args:
        file_path: Путь к файлу
        max_size_mb: Максимальный размер в МБ
        
    Returns:
        True если размер допустим
        
    Raises:
        ValidationError: При превышении размера
    """
    if not file_path.exists():
        raise ValidationError(f"Файл не существует: {file_path}")
    
    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    
    if file_size_mb > max_size_mb:
        raise ValidationError(
            f"Файл слишком большой: {file_size_mb:.1f}MB. "
            f"Максимальный размер: {max_size_mb}MB"
        )
    
    return True


def validate_json_payload(payload: Any, max_size_mb: int = 1) -> Dict[str, Any]:
    """
    Валидация JSON payload.
    
    Args:
        payload: JSON данные
        max_size_mb: Максимальный размер в МБ
        
    Returns:
        Провалидированные данные
        
    Raises:
        ValidationError: При ошибке валидации
    """
    if payload is None:
        raise ValidationError("Пустой payload")
    
    if not isinstance(payload, dict):
        raise ValidationError("Payload должен быть объектом")
    
    # Приблизительная оценка размера
    import json
    payload_size = len(json.dumps(payload, ensure_ascii=False))
    max_size_bytes = max_size_mb * 1024 * 1024
    
    if payload_size > max_size_bytes:
        raise ValidationError(
            f"Payload слишком большой: {payload_size / 1024 / 1024:.1f}MB. "
            f"Максимальный размер: {max_size_mb}MB"
        )
    
    return payload


def sanitize_string(value: str, max_length: int = 1000) -> str:
    """
    Очистка и санитизация строки.
    
    Args:
        value: Строка для очистки
        max_length: Максимальная длина
        
    Returns:
        Очищенная строка
    """
    if not isinstance(value, str):
        value = str(value)
    
    # Удаляем управляющие символы
    value = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', value)
    
    # Ограничиваем длину
    if len(value) > max_length:
        value = value[:max_length]
    
    return value.strip()
