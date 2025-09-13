# Настройка подключения MCP сервера синтаксис-помощника 1С

## Обзор

Этот документ описывает, как настроить подключение к MCP серверу синтаксис-помощника 1С для различных клиентов (VS Code, Claude Desktop, GitHub Copilot и других).

## Требования

- Python 3.9+
- Виртуальное окружение с установленными зависимостями
- Elasticsearch (запущен на localhost:9200)
- Проиндексированные данные справки 1С

## Быстрый старт

### 1. Запуск сервера

#### Windows (Command Prompt)
```cmd
start_mcp_server.bat
```

#### Windows (PowerShell)
```powershell
.\start_mcp_server.ps1
```

#### Ручной запуск
```bash
# Активируем виртуальное окружение
.\venv\Scripts\Activate.ps1

# Устанавливаем переменные
$env:PYTHONPATH = (Get-Location).Path
$env:ELASTICSEARCH_HOST = "localhost"
$env:ELASTICSEARCH_PORT = "9200"

# Запускаем сервер
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Проверка работы сервера

После запуска сервер будет доступен на:
- **API документация**: http://localhost:8000/docs
- **Health check**: http://localhost:8000/health
- **MCP endpoint**: http://localhost:8000/mcp

## Настройка клиентов

### VS Code с MCP расширением

Добавьте в ваш `settings.json`:

```json
{
  "mcp.servers": {
    "1c-syntax-helper": {
      "command": "python",
      "args": [
        "-m", 
        "uvicorn", 
        "src.main:app", 
        "--host", 
        "127.0.0.1", 
        "--port", 
        "8000"
      ],
      "cwd": "d:\\Projects\\python\\help1c",
      "env": {
        "PYTHONPATH": "d:\\Projects\\python\\help1c",
        "ELASTICSEARCH_HOST": "localhost",
        "ELASTICSEARCH_PORT": "9200",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

### Claude Desktop

Создайте или отредактируйте файл `claude_desktop_config.json`:

**Расположение файла:**
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

**Содержимое:**
```json
{
  "mcpServers": {
    "1c-syntax-helper": {
      "command": "python",
      "args": [
        "-m", 
        "uvicorn", 
        "src.main:app", 
        "--host", 
        "127.0.0.1", 
        "--port", 
        "8000"
      ],
      "cwd": "d:\\Projects\\python\\help1c",
      "env": {
        "PYTHONPATH": "d:\\Projects\\python\\help1c",
        "ELASTICSEARCH_HOST": "localhost",
        "ELASTICSEARCH_PORT": "9200",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

### GitHub Copilot / Другие HTTP клиенты

Используйте прямое HTTP соединение:
- **Base URL**: `http://localhost:8000`
- **MCP Endpoint**: `http://localhost:8000/mcp`

Пример HTTP запроса:
```http
POST http://localhost:8000/mcp
Content-Type: application/json

{
  "tool": "find_1c_help",
  "arguments": {
    "query": "ТаблицаЗначений.Добавить",
    "limit": 10
  }
}
```

## Доступные MCP инструменты

Сервер предоставляет следующие инструменты:

### 1. find_1c_help
Поиск по справке 1С
```json
{
  "tool": "find_1c_help",
  "arguments": {
    "query": "строка поиска",
    "limit": 10
  }
}
```

### 2. get_syntax_info
Получение синтаксической информации
```json
{
  "tool": "get_syntax_info",
  "arguments": {
    "object_name": "ТаблицаЗначений",
    "element_name": "Добавить"
  }
}
```

### 3. list_object_members
Список членов объекта
```json
{
  "tool": "list_object_members",
  "arguments": {
    "object_name": "ТаблицаЗначений",
    "member_type": "method"
  }
}
```

### 4. search_by_context
Поиск по контексту
```json
{
  "tool": "search_by_context",
  "arguments": {
    "context": "работа с таблицами",
    "limit": 5
  }
}
```

### 5. get_quick_reference
Быстрая справка
```json
{
  "tool": "get_quick_reference",
  "arguments": {
    "topic": "ТаблицаЗначений"
  }
}
```

## Тестирование подключения

### Проверка HTTP endpoint'а
```bash
# Тестовый запрос
python test_mcp_flexible.py
```

### Проверка health endpoint'а
```bash
curl http://localhost:8000/health
```

### Проверка tools endpoint'а
```bash
curl http://localhost:8000/tools
```

## Устранение неполадок

### Сервер не запускается
1. Проверьте активацию виртуального окружения
2. Убедитесь, что установлены все зависимости: `pip install -r requirements.txt`
3. Проверьте доступность Elasticsearch на localhost:9200

### Elasticsearch недоступен
1. Запустите Elasticsearch
2. Проверьте настройки в переменных окружения
3. Убедитесь, что индекс создан и содержит данные

### Клиент не может подключиться
1. Проверьте, что сервер запущен и доступен на http://localhost:8000
2. Убедитесь в правильности путей в конфигурации
3. Проверьте логи сервера на наличие ошибок

## Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|-------------|
| `PYTHONPATH` | Путь к проекту | Текущая директория |
| `ELASTICSEARCH_HOST` | Хост Elasticsearch | localhost |
| `ELASTICSEARCH_PORT` | Порт Elasticsearch | 9200 |
| `LOG_LEVEL` | Уровень логирования | INFO |
| `SERVER_HOST` | Хост сервера | 0.0.0.0 |
| `SERVER_PORT` | Порт сервера | 8000 |

## Файлы конфигурации

- `mcp_config.json` - Базовая конфигурация MCP
- `mcp_client_config.md` - Примеры конфигураций для различных клиентов
- `start_mcp_server.bat` - Скрипт запуска для Windows Command Prompt
- `start_mcp_server.ps1` - Скрипт запуска для PowerShell

## Примеры использования

См. файл `test_mcp_flexible.py` для примеров HTTP запросов к серверу.