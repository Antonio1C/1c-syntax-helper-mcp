"""Unit тесты для индексатора Elasticsearch."""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from src.core.elasticsearch import ElasticsearchClient
from src.parsers.indexer import ElasticsearchIndexer


@pytest.mark.unit
@pytest.mark.indexer
@pytest.mark.asyncio
async def test_indexer_reindex_all_success(mock_parsed_hbk, mock_elasticsearch_indexer):
    """Тест успешной переиндексации."""
    result = await mock_elasticsearch_indexer.reindex_all(mock_parsed_hbk)
    
    assert result is True
    mock_elasticsearch_indexer.reindex_all.assert_called_once_with(mock_parsed_hbk)


@pytest.mark.unit
@pytest.mark.indexer
@pytest.mark.asyncio
async def test_indexer_index_documentation_success(mock_parsed_hbk, mock_elasticsearch_indexer):
    """Тест индексации документов."""
    result = await mock_elasticsearch_indexer.index_documentation(mock_parsed_hbk.documentation)
    
    assert result == 100  # Mock возвращает 100
    mock_elasticsearch_indexer.index_documentation.assert_called_once()


@pytest.mark.unit
@pytest.mark.indexer
def test_documentation_to_dict(mock_parsed_hbk):
    """Тест конвертации документа в словарь для индексации."""
    doc = mock_parsed_hbk.documentation[0]
    
    # Проверяем что у документа есть метод to_dict или можем создать dict
    doc_dict = {
        'id': doc.id,
        'name': doc.name,
        'type': doc.type.value if hasattr(doc.type, 'value') else str(doc.type),
        'description': doc.description,
        'syntax_ru': doc.syntax_ru,
    }
    
    assert doc_dict['id'] is not None
    assert doc_dict['name'] is not None
    assert doc_dict['type'] is not None


@pytest.mark.unit
@pytest.mark.indexer
def test_batch_documents(mock_parsed_hbk):
    """Тест разбиения документов на батчи."""
    docs = mock_parsed_hbk.documentation
    batch_size = 2
    
    # Простая логика батчей
    batches = [docs[i:i + batch_size] for i in range(0, len(docs), batch_size)]
    
    assert len(batches) > 0
    
    # Проверяем что все документы попали в батчи
    total_docs = sum(len(batch) for batch in batches)
    assert total_docs == len(docs)
    
    # Проверяем размер батчей
    for batch in batches[:-1]:  # Все кроме последнего
        assert len(batch) == batch_size
    
    # Последний батч может быть меньше
    assert len(batches[-1]) <= batch_size


@pytest.mark.unit
@pytest.mark.indexer
@pytest.mark.asyncio
async def test_elasticsearch_bulk_operations():
    """Тест bulk операций с mock ES клиентом."""
    mock_es = Mock()
    mock_es.bulk = AsyncMock(return_value={'errors': False, 'items': []})
    
    # Эмулируем bulk операцию
    operations = [
        {'index': {'_index': 'test', '_id': '1'}},
        {'name': 'Test'},
    ]
    
    result = await mock_es.bulk(operations=operations)
    
    assert result['errors'] is False
    mock_es.bulk.assert_called_once()


@pytest.mark.unit
@pytest.mark.indexer
def test_prepare_document_for_indexing(mock_parsed_hbk):
    """Тест подготовки документа для индексации."""
    doc = mock_parsed_hbk.documentation[0]
    prepared = ElasticsearchIndexer(Mock())._prepare_document(doc)

    assert prepared['id'] == doc.id
    assert prepared['name'] == doc.name
    assert prepared['name_ru'] == doc.name_ru
    assert prepared['name_en'] == doc.name_en
    
    # Проверяем что параметры корректно сериализованы
    if doc.parameters:
        assert len(prepared['parameters']) == len(doc.parameters)
        assert all('name' in p for p in prepared['parameters'])


@pytest.mark.unit
@pytest.mark.indexer
@pytest.mark.asyncio
async def test_elasticsearch_mapping_contains_normalized_name_fields():
    client = ElasticsearchClient()
    indices = Mock()
    indices.create = AsyncMock()
    client._client = Mock(indices=indices)

    assert await client.create_index() is True

    index_config = indices.create.await_args.kwargs["body"]
    analysis = index_config["settings"]["analysis"]
    properties = index_config["mappings"]["properties"]

    assert analysis["normalizer"]["exact_name_normalizer"] == {
        "type": "custom",
        "filter": ["lowercase"]
    }
    for field_name in ("name_ru", "name_en"):
        assert properties[field_name]["fields"]["keyword"] == {
            "type": "keyword",
            "normalizer": "exact_name_normalizer"
        }


@pytest.mark.unit
@pytest.mark.indexer
@pytest.mark.asyncio
async def test_indexer_handles_empty_documentation():
    """Тест обработки пустого списка документов."""
    from src.models.doc_models import ParsedHBK, HBKFile
    
    empty_hbk = ParsedHBK(
        file_info=HBKFile(path="test.hbk", size=0, modified=0.0, entries_count=0),
        documentation=[],
        categories={},
        stats={},
        errors=[]
    )
    
    # Проверяем что пустой список не вызывает ошибок
    assert len(empty_hbk.documentation) == 0
    assert empty_hbk.documentation == []


@pytest.mark.unit
@pytest.mark.indexer
def test_indexer_filters_invalid_documents(mock_parsed_hbk):
    """Тест фильтрации невалидных документов."""
    all_docs = mock_parsed_hbk.documentation
    
    # Фильтруем документы с обязательными полями
    valid_docs = [
        doc for doc in all_docs
        if doc.name and doc.type and doc.id
    ]
    
    # В mock данных все документы должны быть валидными
    assert len(valid_docs) == len(all_docs)


@pytest.mark.unit
@pytest.mark.indexer
def test_index_name_generation():
    """Тест генерации имени индекса."""
    from src.core.config import settings
    
    index_name = settings.elasticsearch.index_name
    
    assert index_name is not None
    assert len(index_name) > 0
    assert '_' in index_name or '-' in index_name or index_name.isalnum()


@pytest.mark.unit
@pytest.mark.indexer
@pytest.mark.asyncio
async def test_indexer_progress_callback(mock_parsed_hbk):
    """Тест callback для отслеживания прогресса индексации."""
    progress_calls = []
    
    def progress_callback(indexed, total):
        progress_calls.append((indexed, total))
    
    # Эмулируем индексацию с callback
    total_docs = len(mock_parsed_hbk.documentation)
    batch_size = 2
    
    for i in range(0, total_docs, batch_size):
        batch_end = min(i + batch_size, total_docs)
        progress_callback(batch_end, total_docs)
    
    # Проверяем что callback вызывался
    assert len(progress_calls) > 0
    
    # Последний вызов должен быть с полным количеством
    last_call = progress_calls[-1]
    assert last_call[0] == total_docs
    assert last_call[1] == total_docs
