"""Тесты извлечения и передачи раздела "Доступность"."""

from unittest.mock import AsyncMock, Mock

import pytest

from src.core.elasticsearch import ElasticsearchClient
from src.handlers.mcp_formatter import MCPResponseFormatter
from src.models.doc_models import Documentation, DocumentType
from src.parsers.html_parser import HTMLParser
from src.parsers.indexer import ElasticsearchIndexer


AVAILABILITY = (
    "Сервер, толстый клиент, внешнее соединение, мобильное приложение "
    "(сервер), мобильный автономный сервер."
)


def _html(title: str, body: str) -> bytes:
    return (
        '<html><body>'
        f'<h1 class="V8SH_pagetitle">{title}</h1>'
        f'{body}'
        '</body></html>'
    ).encode("utf-8")


@pytest.mark.unit
@pytest.mark.parser
@pytest.mark.parametrize(
    ("file_path", "title"),
    [
        ("objects/catalog213/catalog393/Query.html", "Запрос (Query)"),
        (
            "objects/catalog213/catalog393/Query/methods/Execute564.html",
            "Запрос.Выполнить (Query.Execute)",
        ),
        (
            "objects/catalog213/catalog393/Query/properties/Text1019.html",
            "Запрос.Текст (Query.Text)",
        ),
    ],
)
def test_parser_extracts_availability_for_supported_document_types(file_path, title):
    content = _html(
        title,
        '<p class="V8SH_chapter">Описание:</p><p>Описание элемента.</p>'
        '<p class="V8SH_chapter">Доступность: </p>'
        f'<p>{AVAILABILITY}</p>'
        '<p class="V8SH_chapter">Использование в версии:</p>'
        '<p>Доступен, начиная с версии 8.0.</p>',
    )

    doc = HTMLParser().parse_html_content(content, file_path)

    assert doc is not None
    assert doc.availability == AVAILABILITY


@pytest.mark.unit
@pytest.mark.parser
def test_parser_does_not_inherit_missing_availability_for_constructor():
    content = _html(
        "Запрос.По умолчанию",
        '<p class="V8SH_chapter">Синтаксис:</p>Новый Запрос()'
        '<p class="V8SH_chapter">Использование в версии:</p>'
        '<p>Доступен, начиная с версии 8.0.</p>',
    )

    doc = HTMLParser().parse_html_content(
        content,
        "objects/catalog213/catalog393/Query/ctors/ctor29.html",
    )

    assert doc is not None
    assert doc.availability is None


@pytest.mark.unit
@pytest.mark.parser
def test_parser_stops_availability_at_next_chapter():
    content = _html(
        "Запрос.Выполнить (Query.Execute)",
        '<p class="V8SH_chapter">Доступность:</p><p>Сервер.</p>'
        '<p class="V8SH_chapter">Примечание:</p><p>Не включать в доступность.</p>',
    )

    doc = HTMLParser().parse_html_content(
        content,
        "objects/catalog213/catalog393/Query/methods/Execute564.html",
    )

    assert doc is not None
    assert doc.availability == "Сервер."


@pytest.mark.unit
@pytest.mark.parser
def test_parser_skips_hbk_navigation_pages_that_can_shadow_objects():
    content = _html(
        "Запрос",
        "В разделе описываются системные перечисления запроса.",
    )

    doc = HTMLParser().parse_html_content(content, "objects/catalog2/catalog259.html")

    assert doc is None


@pytest.mark.unit
@pytest.mark.indexer
def test_indexer_serializes_availability():
    doc = Documentation(
        id="query",
        type=DocumentType.OBJECT,
        name="Запрос",
        availability=AVAILABILITY,
    )
    indexer = ElasticsearchIndexer(Mock())

    prepared = indexer._prepare_document(doc)

    assert prepared["availability"] == AVAILABILITY


@pytest.mark.unit
@pytest.mark.indexer
@pytest.mark.asyncio
async def test_elasticsearch_mapping_contains_availability():
    client = ElasticsearchClient()
    indices = Mock()
    indices.create = AsyncMock()
    client._client = Mock(indices=indices)

    assert await client.create_index() is True

    index_config = indices.create.await_args.kwargs["body"]
    assert index_config["mappings"]["properties"]["availability"] == {"type": "text"}


@pytest.mark.unit
@pytest.mark.parametrize("formatter", ["format_syntax_info", "format_quick_reference"])
def test_mcp_formatters_include_availability(formatter):
    result = {
        "name": "Запрос",
        "description": "Выполняет запрос.",
        "availability": AVAILABILITY,
    }

    text = getattr(MCPResponseFormatter, formatter)(result)

    assert "Доступность:" in text
    assert AVAILABILITY in text


@pytest.mark.unit
@pytest.mark.parametrize("formatter", ["format_syntax_info", "format_quick_reference"])
def test_mcp_formatters_omit_empty_availability(formatter):
    result = {"name": "Запрос", "description": "Выполняет запрос."}

    text = getattr(MCPResponseFormatter, formatter)(result)

    assert "Доступность:" not in text
