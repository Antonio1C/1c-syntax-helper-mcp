# Тесты проекта

Этот каталог содержит все тесты для MCP сервера синтаксис-помощника 1С.

## Структура

- `conftest.py` - конфигурация pytest и общие фикстуры
- `test_*.py` - файлы с тестами
- `fixtures/` - тестовые данные и фикстуры

## Запуск тестов

### Запуск всех тестов
```bash
pytest tests/
```

### Запуск конкретного теста
```bash
pytest tests/test_parsing.py
```

### Запуск с подробным выводом
```bash
pytest tests/ -v
```

### Запуск с покрытием кода
```bash
pytest tests/ --cov=src
```

## Соглашения

1. **Именование файлов:** `test_<модуль>.py`
2. **Именование функций:** `test_<функциональность>()`
3. **Асинхронные тесты:** используйте `pytest.mark.asyncio`
4. **Фикстуры:** размещайте в `conftest.py` или локально в тестах

## Категории тестов

- **Unit тесты:** тестирование отдельных функций и классов
- **Integration тесты:** тестирование взаимодействия компонентов
- **End-to-end тесты:** полное тестирование сценариев использования

## Примеры

### Простой тест
```python
def test_function():
    assert True
```

### Асинхронный тест
```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None
```

### Тест с фикстурой
```python
def test_with_fixture(sample_hbk_path):
    assert sample_hbk_path.endswith('.hbk')
```
