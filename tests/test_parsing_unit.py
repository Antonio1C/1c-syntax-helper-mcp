"""Unit тесты для парсера .hbk файлов."""

import pytest
from pathlib import Path
from bs4 import BeautifulSoup

from src.models.doc_models import Documentation, DocumentType
from src.parsers.html_parser import HTMLParser


def _extract_names(title: str, document_type: DocumentType) -> Documentation:
    soup = BeautifulSoup(
        f'<h1 class="V8SH_pagetitle">{title}</h1>',
        'html.parser'
    )
    document = Documentation(id="test", type=document_type, name="initial")
    HTMLParser()._extract_title_and_description(soup, document)
    return document


@pytest.mark.unit
@pytest.mark.parser
def test_extracts_global_function_names():
    document = _extract_names("ПоместитьФайл   (PutFile).", DocumentType.GLOBAL_FUNCTION)

    assert document.name_ru == "ПоместитьФайл"
    assert document.name_en == "PutFile"
    assert document.name == "ПоместитьФайл (PutFile)"


@pytest.mark.unit
@pytest.mark.parser
def test_extracts_object_method_names():
    document = _extract_names(
        "ТаблицаЗначений.Количество (ValueTable.Count)",
        DocumentType.OBJECT_FUNCTION
    )

    assert document.name_ru == "Количество"
    assert document.name_en == "Count"
    assert document.name == "Количество (Count)"


@pytest.mark.unit
@pytest.mark.parser
def test_extracts_object_names():
    document = _extract_names(
        "ТипДанных.ИмяОбъекта (DataType.ObjectName)",
        DocumentType.OBJECT
    )

    assert document.name_ru == "ИмяОбъекта"
    assert document.name_en == "ObjectName"
    assert document.name == "ИмяОбъекта (ObjectName)"


@pytest.mark.unit
@pytest.mark.parser
def test_extracts_name_without_english_translation():
    document = _extract_names("Объект.РусскоеИмя...", DocumentType.OBJECT_PROPERTY)

    assert document.name_ru == "РусскоеИмя"
    assert document.name_en == ""
    assert document.name == "РусскоеИмя"


@pytest.mark.unit
@pytest.mark.parser
def test_parsed_hbk_structure(mock_parsed_hbk):
    """Тест структуры распарсенных данных."""
    assert mock_parsed_hbk is not None
    assert mock_parsed_hbk.documentation is not None
    assert len(mock_parsed_hbk.documentation) > 0
    assert mock_parsed_hbk.file_info is not None
    assert mock_parsed_hbk.categories is not None
    assert mock_parsed_hbk.stats is not None


@pytest.mark.unit
@pytest.mark.parser
def test_parsed_hbk_documentation_types(mock_parsed_hbk):
    """Тест типов документации в распарсенных данных."""
    docs = mock_parsed_hbk.documentation
    
    # Проверяем наличие разных типов
    types_found = {doc.type for doc in docs}
    
    assert DocumentType.GLOBAL_FUNCTION in types_found
    assert DocumentType.GLOBAL_EVENT in types_found
    assert DocumentType.OBJECT_PROPERTY in types_found
    assert DocumentType.OBJECT_PROCEDURE in types_found


@pytest.mark.unit
@pytest.mark.parser
def test_parsed_hbk_global_functions(mock_parsed_hbk):
    """Тест глобальных функций."""
    global_funcs = [
        doc for doc in mock_parsed_hbk.documentation 
        if doc.type == DocumentType.GLOBAL_FUNCTION
    ]
    
    assert len(global_funcs) >= 2
    
    # Проверяем структуру первой функции
    func = global_funcs[0]
    assert func.name is not None
    assert func.syntax_ru is not None
    assert func.description is not None
    assert func.object is None  # Глобальная функция


@pytest.mark.unit
@pytest.mark.parser
def test_parsed_hbk_object_members(mock_parsed_hbk):
    """Тест членов объектов."""
    object_members = [
        doc for doc in mock_parsed_hbk.documentation 
        if doc.object is not None
    ]
    
    assert len(object_members) >= 2
    
    # Проверяем что у членов есть объект
    for member in object_members:
        assert member.object is not None
        assert member.name is not None


@pytest.mark.unit
@pytest.mark.parser
def test_parsed_hbk_parameters(mock_parsed_hbk):
    """Тест параметров функций."""
    funcs_with_params = [
        doc for doc in mock_parsed_hbk.documentation 
        if doc.parameters and len(doc.parameters) > 0
    ]
    
    assert len(funcs_with_params) > 0
    
    # Проверяем структуру параметров
    func = funcs_with_params[0]
    param = func.parameters[0]
    
    assert param.name is not None
    assert param.type is not None
    assert param.description is not None
    assert param.required is not None


@pytest.mark.unit
@pytest.mark.parser
def test_parsed_hbk_stats(mock_parsed_hbk):
    """Тест статистики парсинга."""
    stats = mock_parsed_hbk.stats
    
    assert 'html_files' in stats
    assert 'processed_html' in stats
    
    # Проверяем что статистика не пустая
    assert stats['html_files'] > 0
    assert stats['processed_html'] > 0
    assert isinstance(stats, dict)


@pytest.mark.unit
@pytest.mark.parser
def test_parsed_hbk_categories(mock_parsed_hbk):
    """Тест категорий документации."""
    categories = mock_parsed_hbk.categories
    
    assert len(categories) > 0
    assert 'Глобальный контекст' in categories or 'Массив' in categories


@pytest.mark.unit
@pytest.mark.parser
def test_parsed_hbk_no_errors(mock_parsed_hbk):
    """Тест отсутствия ошибок парсинга."""
    errors = mock_parsed_hbk.errors
    
    # В mock данных не должно быть ошибок
    assert len(errors) == 0


@pytest.mark.unit
@pytest.mark.parser
def test_documentation_full_path(mock_parsed_hbk):
    """Тест полных путей документов."""
    docs = mock_parsed_hbk.documentation
    
    for doc in docs:
        assert doc.full_path is not None
        assert len(doc.full_path) > 0
        
        # Глобальные функции должны содержать "Глобальный контекст"
        if doc.type == DocumentType.GLOBAL_FUNCTION:
            assert "Глобальный контекст" in doc.full_path or doc.name in doc.full_path


@pytest.mark.unit
@pytest.mark.parser
def test_documentation_examples(mock_parsed_hbk):
    """Тест наличия примеров кода."""
    docs_with_examples = [
        doc for doc in mock_parsed_hbk.documentation 
        if doc.examples
    ]
    
    # Хотя бы у некоторых документов должны быть примеры
    assert len(docs_with_examples) > 0
    
    # Проверяем что примеры не пустые
    for doc in docs_with_examples:
        assert len(doc.examples) > 0
