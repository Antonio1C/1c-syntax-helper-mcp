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


@pytest.fixture
def mock_parsed_hbk():
    """Mock данных распарсенного .hbk файла для unit тестов."""
    from src.models.doc_models import (
        ParsedHBK, Documentation, DocumentType, 
        HBKFile, Parameter
    )
    from datetime import datetime
    
    # Создаём тестовые документы
    docs = [
        Documentation(
            id="global_func_add",
            name="Добавить",
            name_ru="Добавить",
            name_en="Add",
            type=DocumentType.GLOBAL_FUNCTION,
            object=None,
            syntax_ru="Добавить(<Значение>)",
            syntax_en="Add(<Value>)",
            description="Добавляет значение в массив",
            parameters=[
                Parameter(
                    name="Значение",
                    type="Произвольный",
                    description="Добавляемое значение",
                    required=True
                )
            ],
            return_type="Булево",
            version_from="8.3.5",
            examples=["Массив.Добавить(10);"],
            source_file="GlobalContext/Add.html",
            full_path="Глобальный контекст.Добавить"
        ),
        Documentation(
            id="global_func_delete",
            name="Удалить",
            name_ru="Удалить",
            name_en="Delete",
            type=DocumentType.GLOBAL_FUNCTION,
            object=None,
            syntax_ru="Удалить(<Индекс>)",
            syntax_en="Delete(<Index>)",
            description="Удаляет элемент из массива",
            parameters=[
                Parameter(
                    name="Индекс",
                    type="Число",
                    description="Индекс удаляемого элемента",
                    required=True
                )
            ],
            return_type=None,
            version_from="8.3.5",
            examples=["Массив.Удалить(0);"],
            source_file="GlobalContext/Delete.html",
            full_path="Глобальный контекст.Удалить"
        ),
        Documentation(
            id="object_array_count",
            name="Количество",
            name_ru="Количество",
            name_en="Count",
            type=DocumentType.OBJECT_PROPERTY,
            object="Массив",
            syntax_ru="Массив.Количество()",
            syntax_en="Array.Count()",
            description="Возвращает количество элементов в массиве",
            parameters=[],
            return_type="Число",
            version_from="8.0",
            examples=["КоличествоЭлементов = Массив.Количество();"],
            source_file="Objects/Array/Count.html",
            full_path="Массив.Количество"
        ),
        Documentation(
            id="object_array_clear",
            name="Очистить",
            name_ru="Очистить",
            name_en="Clear",
            type=DocumentType.OBJECT_PROCEDURE,
            object="Массив",
            syntax_ru="Массив.Очистить()",
            syntax_en="Array.Clear()",
            description="Очищает массив",
            parameters=[],
            return_type=None,
            version_from="8.0",
            examples=["Массив.Очистить();"],
            source_file="Objects/Array/Clear.html",
            full_path="Массив.Очистить"
        ),
        Documentation(
            id="event_before_write",
            name="ПередЗаписью",
            name_ru="ПередЗаписью",
            name_en="BeforeWrite",
            type=DocumentType.GLOBAL_EVENT,
            object=None,
            syntax_ru="Процедура ПередЗаписью(Отказ)",
            syntax_en="Procedure BeforeWrite(Cancel)",
            description="Событие перед записью объекта",
            parameters=[
                Parameter(
                    name="Отказ",
                    type="Булево",
                    description="Признак отказа от записи",
                    required=True
                )
            ],
            return_type=None,
            version_from="8.0",
            examples=["Процедура ПередЗаписью(Отказ)\n  // Код обработчика\nКонецПроцедуры"],
            source_file="Events/BeforeWrite.html",
            full_path="События.ПередЗаписью"
        )
    ]
    
    # Создаём информацию о файле
    file_info = HBKFile(
        path="data/hbk/test.hbk",
        size=1024 * 1024,  # 1 MB
        modified=1234567890.0,
        entries_count=5
    )
    
    # Создаём статистику
    stats = {
        'html_files': 5,
        'processed_html': 5,
        'total_docs': 5,
        'by_type': 5
    }
    
    # Создаём категории
    from src.models.doc_models import CategoryInfo
    categories = {
        'Глобальный контекст': CategoryInfo(name='Глобальный контекст'),
        'Массив': CategoryInfo(name='Массив'),
        'События': CategoryInfo(name='События')
    }
    
    return ParsedHBK(
        file_info=file_info,
        documentation=docs,
        categories=categories,
        stats=stats,
        errors=[]
    )


@pytest.fixture
def mock_hbk_parser():
    """Mock HBKParser для unit тестов."""
    from unittest.mock import Mock
    
    parser = Mock()
    parser.max_files_per_type = 10
    parser.max_total_files = 50
    
    # Метод parse_file возвращает mock_parsed_hbk
    def parse_file_side_effect(file_path):
        # Возвращаем простой mock результат
        from src.models.doc_models import ParsedHBK, HBKFile
        return ParsedHBK(
            file_info=HBKFile(
                path=file_path,
                size=1024,
                modified=1234567890.0,
                entries_count=5
            ),
            documentation=[],
            categories={},
            stats={},
            errors=[]
        )
    
    parser.parse_file.side_effect = parse_file_side_effect
    return parser


@pytest.fixture
async def mock_elasticsearch_indexer():
    """Mock ElasticsearchIndexer для unit тестов."""
    from unittest.mock import AsyncMock, Mock
    
    indexer = Mock()
    indexer.reindex_all = AsyncMock(return_value=True)
    indexer.index_documentation = AsyncMock(return_value=100)
    
    return indexer
