"""Тесты для фоновой индексации."""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from src.infrastructure.background.indexing_manager import (
    BackgroundIndexingManager,
    setup_indexing_manager,
    get_indexing_manager
)
from src.models.index_status import IndexingStatus, IndexProgressInfo
from src.core.elasticsearch import ElasticsearchClient


@pytest.fixture
def mock_es_client():
    """Мок Elasticsearch клиента."""
    client = AsyncMock(spec=ElasticsearchClient)
    client.is_connected.return_value = True
    client.index_exists.return_value = False
    client.get_documents_count.return_value = 0
    return client


@pytest.fixture
def indexing_manager():
    """Создание экземпляра менеджера индексации."""
    return BackgroundIndexingManager(
        shutdown_timeout=5,
        progress_log_interval=100
    )


@pytest.mark.asyncio
async def test_initial_status(indexing_manager):
    """Тест начального статуса менеджера."""
    status = await indexing_manager.get_status()
    
    assert status.status == IndexingStatus.IDLE
    assert status.total_documents == 0
    assert status.indexed_documents == 0
    assert status.start_time is None
    assert status.end_time is None
    assert status.error_message is None


@pytest.mark.asyncio
async def test_is_indexing_initially_false(indexing_manager):
    """Тест что изначально индексация не активна."""
    assert not indexing_manager.is_indexing()


@pytest.mark.asyncio
async def test_progress_callback(indexing_manager):
    """Тест callback функции для прогресса."""
    # Проверяем, что callback обновляет прогресс
    indexing_manager._update_progress(50, 100)
    
    assert indexing_manager._progress_info.indexed_documents == 50
    assert indexing_manager._progress_info.total_documents == 100
    assert indexing_manager._progress_info.progress_percent == 50.0


@pytest.mark.asyncio
async def test_progress_info_properties():
    """Тест вычисляемых свойств IndexProgressInfo."""
    from datetime import datetime, timedelta
    
    start = datetime.now()
    end = start + timedelta(seconds=10)
    
    info = IndexProgressInfo(
        status=IndexingStatus.IN_PROGRESS,
        total_documents=100,
        indexed_documents=50,
        start_time=start,
        end_time=end
    )
    
    assert info.progress_percent == 50.0
    assert info.duration_seconds == pytest.approx(10.0, rel=1e-2)


@pytest.mark.asyncio
async def test_progress_info_to_dict():
    """Тест сериализации IndexProgressInfo в словарь."""
    from datetime import datetime
    
    start = datetime.now()
    
    info = IndexProgressInfo(
        status=IndexingStatus.COMPLETED,
        total_documents=100,
        indexed_documents=100,
        start_time=start,
        file_path="/test/file.hbk"
    )
    
    result = info.to_dict()
    
    assert result["status"] == "completed"
    assert result["progress_percent"] == 100.0
    assert result["total_documents"] == 100
    assert result["indexed_documents"] == 100
    assert result["file_path"] == "/test/file.hbk"
    assert "start_time" in result


@pytest.mark.asyncio
async def test_singleton_setup():
    """Тест singleton pattern для менеджера."""
    manager1 = setup_indexing_manager()
    manager2 = get_indexing_manager()
    
    assert manager1 is manager2


@pytest.mark.asyncio
async def test_graceful_shutdown_no_indexing(indexing_manager):
    """Тест graceful shutdown когда индексация не активна."""
    result = await indexing_manager.graceful_shutdown(timeout=5)
    
    assert result is True


@pytest.mark.asyncio 
async def test_status_during_indexing(indexing_manager, mock_es_client, tmp_path):
    """Тест статуса во время индексации."""
    # Создаём временный файл
    test_file = tmp_path / "test.hbk"
    test_file.write_text("test content")
    
    # Мокаем парсер и индексер с правильными путями
    with patch('src.parsers.hbk_parser.HBKParser') as mock_parser, \
         patch('src.parsers.indexer.ElasticsearchIndexer') as mock_indexer:
        
        # Настраиваем моки
        mock_parsed = MagicMock()
        mock_parsed.documentation = [MagicMock() for _ in range(100)]
        mock_parser.return_value.parse_file.return_value = mock_parsed
        
        mock_indexer_instance = mock_indexer.return_value
        
        # Делаем индексацию медленной чтобы успеть проверить статус
        async def slow_reindex(parsed, progress_callback=None):
            if progress_callback:
                progress_callback(50, 100)
            await asyncio.sleep(0.5)
            if progress_callback:
                progress_callback(100, 100)
            return True
        
        mock_indexer_instance.reindex_all = slow_reindex
        
        # Запускаем индексацию
        await indexing_manager.start_indexing(str(test_file), mock_es_client)
        
        # Даём немного времени на запуск
        await asyncio.sleep(0.1)
        
        # Проверяем что индексация активна
        assert indexing_manager.is_indexing()
        
        # Ждём завершения
        while indexing_manager.is_indexing():
            await asyncio.sleep(0.1)
        
        # Проверяем финальный статус
        status = await indexing_manager.get_status()
        assert status.status == IndexingStatus.COMPLETED


@pytest.mark.asyncio
async def test_indexing_with_error(indexing_manager, mock_es_client, tmp_path):
    """Тест индексации с ошибкой."""
    # Создаём несуществующий файл
    test_file = tmp_path / "nonexistent.hbk"
    
    # Запускаем индексацию
    await indexing_manager.start_indexing(str(test_file), mock_es_client)
    
    # Ждём завершения
    await asyncio.sleep(0.5)
    
    # Проверяем статус
    status = await indexing_manager.get_status()
    assert status.status == IndexingStatus.FAILED
    assert status.error_message is not None
    assert "не найден" in status.error_message.lower()


@pytest.mark.asyncio
async def test_concurrent_indexing_blocked(indexing_manager, mock_es_client, tmp_path):
    """Тест что невозможно запустить две индексации одновременно."""
    # Создаём временный файл
    test_file = tmp_path / "test.hbk"
    test_file.write_text("test content")
    
    with patch('src.parsers.hbk_parser.HBKParser') as mock_parser, \
         patch('src.parsers.indexer.ElasticsearchIndexer') as mock_indexer:
        
        mock_parsed = MagicMock()
        mock_parsed.documentation = [MagicMock() for _ in range(10)]
        mock_parser.return_value.parse_file.return_value = mock_parsed
        
        # Медленная индексация
        async def slow_reindex(parsed, progress_callback=None):
            await asyncio.sleep(1)
            return True
        
        mock_indexer.return_value.reindex_all = slow_reindex
        
        # Первый запуск
        await indexing_manager.start_indexing(str(test_file), mock_es_client)
        await asyncio.sleep(0.1)
        
        assert indexing_manager.is_indexing()
        
        # Попытка второго запуска (должна быть проигнорирована)
        await indexing_manager.start_indexing(str(test_file), mock_es_client)
        
        # Всё ещё должна быть только одна активная задача
        assert indexing_manager.is_indexing()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
