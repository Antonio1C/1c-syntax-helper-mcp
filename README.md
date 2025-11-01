# 1C Syntax Helper MCP Server

MCP-сервер для быстрого поиска по синтаксису 1С, предоставляющий ИИ-агентам в VS Code доступ к общей документации платформы 1С:Предприятие через централизованный сервис.

## � Документация

- **[📖 SETUP_GUIDE.md](SETUP_GUIDE.md)** - Подробная инструкция по развертыванию
- **[📋 ТЕХНИЧЕСКОЕ_ЗАДАНИЕ.md](ТЕХНИЧЕСКОЕ_ЗАДАНИЕ.md)** - Техническое задание проекта

## �🚀 Быстрый старт

### Системные требования
- Windows 10/11 64-bit
- Docker Desktop
- 4+ ГБ RAM
- VS Code с MCP расширением

### Развертывание сервиса

```bash
# 1. Клонировать проект
git clone <repo-url> 1c-syntax-helper-mcp
cd 1c-syntax-helper-mcp

# 2. Поместить .hbk файл документации
copy "path\to\1c_documentation.hbk" "data\hbk\1c_documentation.hbk"

# 3. Запустить сервисы
docker compose up -d

# 4. Проверить доступность
curl http://localhost:8000/health
```

### Настройка VS Code

Добавьте в настройки VS Code (`settings.json`):

```json
{
  "mcp.servers": {
    "1c-syntax-helper": {
      "command": "curl",
      "args": [
        "-X", "POST",
        "-H", "Content-Type: application/json", 
        "-d", "@-",
        "http://localhost:8000/mcp"
      ]
    }
  }
}
```

> **💡 Подробные инструкции** смотрите в [SETUP_GUIDE.md](SETUP_GUIDE.md)

## 🏗️ Архитектура

```
                    🖥️ Сервер (localhost)
┌─────────────────────────────────────────────────────────┐
│  ┌─────────────────┐    ┌──────────────────────────────┐ │
│  │  Elasticsearch  │    │    FastAPI MCP Server        │ │
│  │    (общий)      │◄───┤      (shared service)       │ │
│  │ 1c_docs_index   │    │   - Single .hbk file        │ │
│  └─────────────────┘    │   - No authentication       │ │
│                         │   - Shared documentation    │ │
│                         └──────────────┬───────────────┘ │
└────────────────────────────────────────┼─────────────────┘
                                         │ Port 8000
        ┌────────────────────────────────┼────────────────┐
        │                                │                │
   ┌────▼────┐                     ┌────▼────┐     ┌────▼────┐
   │VS Code  │                     │VS Code  │ ... │VS Code  │
   │ User 1  │                     │ User 2  │     │ User 8  │
   └─────────┘                     └─────────┘     └─────────┘
```

## 📁 Структура проекта

```
1c-syntax-helper-mcp/
├── docker-compose.yml          # Оркестрация контейнеров
├── Dockerfile                  # Образ MCP сервера
├── requirements.txt           # Python зависимости
├── .env.example              # Пример конфигурации
├── src/                      # Исходный код
│   ├── main.py              # FastAPI приложение
│   ├── mcp_handler.py       # MCP Protocol обработка
│   ├── core/                # Ядро системы
│   ├── parsers/             # Парсеры .hbk документации
│   ├── search/              # Модули поиска
│   └── models/              # Pydantic модели
├── data/                    # Данные
│   ├── hbk/                # .hbk файл документации
│   └── logs/               # Логи приложения
├── tests/                   # Тесты
└── docs/                   # Документация
```

## 🔧 Основные возможности

- **Поиск глобальных функций**: `СтрДлина`, `ЧислоПрописью`
- **Поиск методов объектов**: `ТаблицаЗначений.Добавить`
- **Поиск свойств**: `ТаблицаЗначений.Колонки`
- **Информация об объектах**: получение всех методов/свойств/событий
- **Фоновая индексация**: автоматическая индексация при первом запуске
- **Принудительная переиндексация**: через параметр `--reindex` или API

## 🔄 Переиндексация

### Быстрый запуск с переиндексацией

```bash
# Windows (bat)
start_mcp_server.bat --reindex

# Windows (PowerShell)
.\start_mcp_server.ps1 --reindex

# Или через переменную окружения в .env
REINDEX_ON_STARTUP=true
```

**📖 Подробнее:** [REINDEX_GUIDE.md](REINDEX_GUIDE.md)

## 📚 Документация

### Пользовательская документация
- [Техническое задание](ТЕХНИЧЕСКОЕ_ЗАДАНИЕ.md)
- [Инструкции по настройке](docs/SETUP_GUIDE.md)
- [Настройка VS Code](docs/VS_CODE_CONFIG.md)
- [API Reference](docs/API_REFERENCE.md)
- [Обслуживание](docs/MAINTENANCE.md)

### Разработка и рефакторинг
- [Техническое задание на рефакторинг](ТЕХНИЧЕСКОЕ_ЗАДАНИЕ_РЕФАКТОРИНГ.md)
- [Отчёты по спринтам](docs/sprints/) - Детальные отчёты о выполнении рефакторинга
  - [Sprint 1.1 - Разделение main.py](docs/sprints/sprint_1.1_report.md) ✅

## 🛠️ Разработка

### Требования

- Docker Engine 20.0+
- Docker Compose 2.0+
- Python 3.11+ (для разработки)

### Локальная разработка

```bash
# Создать виртуальное окружение
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows
# source venv/bin/activate   # Linux/Mac

# Установить зависимости
pip install -r requirements.txt

# Запустить в режиме разработки
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### Тестирование

```bash
# Запустить тесты
python -m pytest tests/ -v

# Проверить покрытие
python -m pytest tests/ --cov=src --cov-report=html
```

## 🔄 Обновление документации

Документация обновляется вручную раз в год:

```bash
# 1. Остановить сервисы
docker-compose down

# 2. Заменить .hbk файл
copy "new_1c_documentation.hbk" "data\hbk\1c_documentation.hbk"

# 3. Запустить и переиндексировать
docker-compose up -d
curl -X POST http://localhost:8000/index/rebuild
```

## 📋 MCP Protocol

Сервер реализует [Model Context Protocol 2025-06-18](https://modelcontextprotocol.io/specification/2025-06-18/index) со следующими tools:

- `search_1c_syntax` - поиск функций/методов/объектов
- `get_1c_function_details` - детальная информация о функции
- `get_1c_object_info` - информация об объекте и его методах

## ⚡ Performance

- Время отклика поиска: < 500ms
- Поддержка 8 одновременных пользователей
- Размер индекса: ~32MB (80% от 40MB .hbk файла)
- Потребление памяти: ~2GB (1GB ES + 1GB MCP сервер)

## 🐛 Поддержка

При возникновении проблем:

1. Проверить логи: `docker-compose logs mcp-server`
2. Проверить статус Elasticsearch: `curl http://localhost:9200/_cluster/health`
3. Проверить статус индексации: `curl http://localhost:8000/index/status`

## 📄 Лицензия

MIT License

---

**Разработано для работы с документацией 1С:Предприятие 8.3.24+**
