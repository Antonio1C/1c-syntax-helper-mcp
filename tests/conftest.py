"""
Конфигурация pytest для тестов проекта.
"""

import pytest
import asyncio
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Включаем режим asyncio для pytest
pytest_asyncio_mode = "auto"


@pytest.fixture(scope="session")
def event_loop():
    """Создает event loop для асинхронных тестов."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_hbk_path():
    """Путь к тестовому .hbk файлу."""
    from src.core.config import settings
    hbk_dir = Path(settings.data.hbk_directory)
    hbk_files = list(hbk_dir.glob("*.hbk"))
    
    if hbk_files:
        return str(hbk_files[0])
    else:
        pytest.skip("Нет доступных .hbk файлов для тестирования")


@pytest.fixture
def mock_elasticsearch():
    """Мок для Elasticsearch клиента."""
    from unittest.mock import Mock
    
    mock_client = Mock()
    mock_client.is_connected.return_value = True
    mock_client.index_exists.return_value = True
    mock_client.get_documents_count.return_value = 100
    
    return mock_client
