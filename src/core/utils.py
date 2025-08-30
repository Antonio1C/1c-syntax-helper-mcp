"""
Безопасные утилиты для системных операций.
"""

import subprocess
import shlex
import tempfile
import os
import shutil
from pathlib import Path
from typing import List, Optional, Tuple
import logging
from .constants import EXTRACTION_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)


class SafeSubprocessError(Exception):
    """Исключение для ошибок безопасного subprocess."""
    pass


def safe_subprocess_run(
    command: List[str], 
    cwd: Optional[Path] = None,
    timeout: int = EXTRACTION_TIMEOUT_SECONDS,
    capture_output: bool = True
) -> subprocess.CompletedProcess:
    """
    Безопасный запуск subprocess с проверкой команды.
    
    Args:
        command: Список аргументов команды
        cwd: Рабочая директория
        timeout: Таймаут в секундах
        capture_output: Захватывать ли вывод
        
    Returns:
        CompletedProcess результат
        
    Raises:
        SafeSubprocessError: При ошибке выполнения
    """
    if not command or not isinstance(command, list):
        raise SafeSubprocessError("Команда должна быть непустым списком")
    
    # Проверка безопасности команды
    executable = command[0]
    allowed_executables = {"7z", "7z.exe", "unzip", "unzip.exe"}
    
    if not any(executable.endswith(allowed) for allowed in allowed_executables):
        raise SafeSubprocessError(f"Недопустимая команда: {executable}")
    
    # Проверка аргументов на инъекции
    for arg in command[1:]:
        if any(char in arg for char in [";", "&", "|", "`", "$", "(", ")", "<", ">"]):
            raise SafeSubprocessError(f"Подозрительный аргумент: {arg}")
    
    try:
        logger.debug(f"Выполнение команды: {' '.join(shlex.quote(arg) for arg in command)}")
        
        result = subprocess.run(
            command,
            cwd=cwd,
            timeout=timeout,
            capture_output=capture_output,
            text=True,
            check=False  # Не выбрасывать исключение при ненулевом коде возврата
        )
        
        if result.returncode != 0:
            logger.warning(f"Команда завершилась с кодом {result.returncode}: {result.stderr}")
        
        return result
        
    except subprocess.TimeoutExpired as e:
        raise SafeSubprocessError(f"Таймаут выполнения команды: {e}")
    except Exception as e:
        raise SafeSubprocessError(f"Ошибка выполнения команды: {e}")


def create_safe_temp_dir(prefix: str = "help1c_") -> Path:
    """
    Создание безопасной временной директории.
    
    Args:
        prefix: Префикс для имени директории
        
    Returns:
        Path к созданной директории
    """
    try:
        temp_dir = Path(tempfile.mkdtemp(prefix=prefix))
        logger.debug(f"Создана временная директория: {temp_dir}")
        return temp_dir
    except Exception as e:
        raise SafeSubprocessError(f"Ошибка создания временной директории: {e}")


def safe_remove_dir(path: Path) -> None:
    """
    Безопасное удаление директории.
    
    Args:
        path: Путь к директории
    """
    try:
        if path.exists() and path.is_dir():
            shutil.rmtree(path)
            logger.debug(f"Удалена директория: {path}")
    except Exception as e:
        logger.warning(f"Ошибка удаления директории {path}: {e}")


def validate_file_path(file_path: Path, allowed_extensions: Optional[List[str]] = None) -> bool:
    """
    Валидация пути к файлу.
    
    Args:
        file_path: Путь к файлу
        allowed_extensions: Список разрешенных расширений
        
    Returns:
        True если путь валиден
        
    Raises:
        SafeSubprocessError: При невалидном пути
    """
    if not file_path.exists():
        raise SafeSubprocessError(f"Файл не существует: {file_path}")
    
    if not file_path.is_file():
        raise SafeSubprocessError(f"Путь не является файлом: {file_path}")
    
    # Проверка на path traversal
    try:
        file_path.resolve(strict=True)
    except Exception:
        raise SafeSubprocessError(f"Невалидный путь: {file_path}")
    
    if allowed_extensions:
        if file_path.suffix.lower() not in allowed_extensions:
            raise SafeSubprocessError(
                f"Недопустимое расширение файла: {file_path.suffix}. "
                f"Разрешены: {allowed_extensions}"
            )
    
    return True
