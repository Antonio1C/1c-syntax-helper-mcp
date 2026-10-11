# 1C Syntax Helper MCP Server

MCP-сервер для быстрого поиска по синтаксису 1С, предоставляющий ИИ-агентам в VS Code доступ к общей документации платформы 1С:Предприятие через централизованный сервис.

## 📚 Документация

- **[📖 DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md)** - Подробная инструкция по развертыванию на Windows Server и Linux Server (ARM64)
- **[📋 ТЕХНИЧЕСКОЕ_ЗАДАНИЕ.md](ТЕХНИЧЕСКОЕ_ЗАДАНИЕ.md)** - Техническое задание проекта
- **[📖 SETUP_GUIDE.md](SETUP_GUIDE.md)** - Инструкция по локальной разработке

## 🚀 Быстрый старт (локальная разработка)

### Системные требования
- Windows 10/11 64-bit или Linux
- Docker Desktop
- 4+ ГБ RAM
- VS Code (опционально)

### Развертывание для локального тестирования

```bash
# 1. Клонировать проект
git clone <repo-url> 1c-syntax-helper-mcp
cd 1c-syntax-helper-mcp

# 2. Поместить .hbk файл документации
copy "path\to\1c_documentation.hbk" "data\hbk\1c_documentation.hbk"

# 3. Запустить контейнеры
docker compose up -d

# 4. Проверить доступность
curl http://localhost:8000/health
```

### Для развертывания на сервер

📖 **Полная инструкция**: [DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md)

**Краткий алгоритм:**

1. **Для Windows Server (AMD64)**
   ```powershell
   docker build -t help1c-mcp:amd64 .
   docker save help1c-mcp:amd64 -o help1c-mcp-amd64.tar
   # Скопировать .tar файл на сервер и загрузить через docker load
   ```

2. **Для Linux Server (ARM64)**
   ```powershell
   docker buildx build --platform linux/arm64 -t help1c-mcp:arm64 -o type=docker .
   docker save help1c-mcp:arm64 -o help1c-mcp-arm64.tar
   # Скопировать .tar файл на сервер и загрузить через docker load
   ```

### Настройка VS Code для подключения к серверу

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
        "http://SERVER_IP:8000/mcp"
      ]
    }
  }
}
```

Замените `SERVER_IP` на IP адрес вашего сервера (например, `192.168.1.100` или `localhost` для локального тестирования).

## 📁 Структура проекта

```
1c-syntax-helper-mcp/
├── docker-compose.yml          # Оркестрация контейнеров
├── Dockerfile                  # Образ MCP сервера (поддержка AMD64 и ARM64)
├── requirements.txt            # Python зависимости
├── .env.example                # Пример конфигурации
├── src/                        # Исходный код
│   ├── main.py                 # FastAPI приложение
│   ├── core/                   # Ядро системы
│   ├── parsers/                # Парсеры .hbk документации
│   ├── search/                 # Модули поиска
│   ├── handlers/               # Обработчики MCP
│   ├── models/                 # Pydantic модели
│   └── api/                    # API эндпоинты
├── data/                       # Данные
│   ├── hbk/                    # .hbk файл документации
│   └── logs/                   # Логи приложения
├── tests/                      # Тесты
├── docs/                       # Документация
│   ├── DEPLOYMENT_GUIDE.md     # Инструкция развертывания
│   ├── SETUP_GUIDE.md          # Инструкция локальной разработки
│   └── sprints/                # Отчеты о спринтах
└── README.md                   # Этот файл
```

## 🔧 Основные возможности

- **Поиск глобальных функций**: `СтрДлина`, `ЧислоПрописью`
- **Поиск методов объектов**: `ТаблицаЗначений.Добавить`
- **Поиск свойств**: `ТаблицаЗначений.Колонки`
- **Информация об объектах**: получение всех методов/свойств/событий
- **Фоновая индексация**: автоматическая индексация при первом запуске
- **Принудительная переиндексация**: через параметр `--reindex` или API
- **Поддержка нескольких архитектур**: AMD64 (Windows/Linux) и ARM64 (Raspberry Pi, Apple Silicon)

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

**Подробнее**: [REINDEX_GUIDE.md](REINDEX_GUIDE.md)

## 🛠️ Разработка

### Требования

- Docker Engine 20.0+
- Docker Compose 2.0+
- Python 3.14+ (для разработки)

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

Документация обновляется при необходимости:

```bash
# 1. Остановить сервисы
docker-compose down

# 2. Заменить .hbk файл
copy "new_1c_documentation.hbk" "data\hbk\1c_documentation.hbk"

# 3. Запустить и переиндексировать
docker-compose up -d
curl -X POST http://localhost:8000/index/rebuild
```

**Подробнее**: [DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md#обновление-hbk-файла)

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

**Подробнее**: [DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md#-устранение-проблем)

## 📄 Лицензия

MIT License

---

**Разработано для работы с документацией 1С:Предприятие 8.3.24+**
