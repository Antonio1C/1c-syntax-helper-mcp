# 1C Syntax Helper MCP Server

MCP-сервер для быстрого поиска по синтаксису 1С, предоставляющий ИИ-агентам в VS Code доступ к общей документации платформы 1С:Предприятие через централизованный сервис.

## 📚 Документация

- **[📑 Каталог инструкций](docs/instructions/README.md)** - развертывание, локальная разработка и подключение MCP-клиентов
- **[📖 DEPLOYMENT_GUIDE.md](docs/instructions/DEPLOYMENT_GUIDE.md)** - Развертывание на Windows 10/11 и Linux Server (AMD64/ARM64)
- **[📖 SETUP_GUIDE.md](docs/instructions/SETUP_GUIDE.md)** - Инструкция по локальной разработке

## 🚀 Быстрый старт (локальная разработка)

### Системные требования
- Windows 10/11 64-bit или Linux
- Docker Desktop
- 7-Zip для локального запуска Python-приложения вне Docker (в Docker-образе он уже установлен)
- 4+ ГБ RAM
- VS Code (опционально)

### Развертывание для локального тестирования

```powershell
# 1. Клонировать проект
git clone https://github.com/Antonio1C/1c-syntax-helper-mcp.git
cd 1c-syntax-helper-mcp

# 2. Скопировать shcntx_ru.hbk из установленной справки 1С
Copy-Item "C:\path\to\shcntx_ru.hbk" ".\data\hbk\shcntx_ru.hbk"

# 3. Запустить контейнеры
docker compose up -d

# 4. Проверить доступность
Invoke-RestMethod -Uri "http://localhost:8000/health"
```

Файл `shcntx_ru.hbk` не входит в репозиторий. Для Linux используйте `cp /path/to/shcntx_ru.hbk data/hbk/shcntx_ru.hbk`.

### Для развертывания на сервер

📖 **Полная инструкция**: [DEPLOYMENT_GUIDE.md](docs/instructions/DEPLOYMENT_GUIDE.md)

**Краткий алгоритм:**

1. **Для Windows 10/11 (AMD64) и Linux Server (AMD64)**
   ```powershell
   docker build -t help1c-mcp:amd64 .
   docker save help1c-mcp:amd64 -o help1c-mcp-amd64.tar
  # Для Windows 10/11 используйте Docker Desktop с Linux containers.
  # На целевой машине загрузите архив через docker load.
   ```

2. **Для Linux Server (ARM64)**
   ```powershell
   docker buildx build --platform linux/arm64 -t help1c-mcp:arm64 -o type=docker .
   docker save help1c-mcp:arm64 -o help1c-mcp-arm64.tar
   # Скопировать .tar файл на сервер и загрузить через docker load
   ```

### Настройка VS Code для подключения к серверу

Создайте файл `.vscode/mcp.json` в проекте и добавьте HTTP-конфигурацию:

```json
{
  "servers": {
    "mcp-helper1c-http": {
      "url": "http://SERVER_IP:8000/mcp",
      "type": "http"
    }
  },
  "inputs": []
}
```

Замените `SERVER_IP` на IP-адрес сервера (например, `192.168.1.100`). Для локального тестирования укажите `localhost`.

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

```powershell
# Windows (bat)
start_mcp_server.bat --reindex

# Windows (PowerShell)
.\start_mcp_server.ps1 --reindex

# Или через переменную окружения в .env
REINDEX_ON_STARTUP=true
```

**Подробнее**: [REINDEX_GUIDE.md](docs/instructions/REINDEX_GUIDE.md)

## 🛠️ Разработка

### Требования

- Docker Engine 20.0+
- Docker Compose 2.0+
- Python 3.14+ (для разработки)

### Локальная разработка

```powershell
# Windows PowerShell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

# Запустить в режиме разработки
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Для Linux используйте отдельный набор команд:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### Тестирование

```powershell
# Запустить тесты
python -m pytest tests/ -v

# Проверить покрытие
python -m pytest tests/ --cov=src --cov-report=html
```

## 🔄 Обновление документации

Документация обновляется при необходимости:

```powershell
# 1. Остановить сервисы
docker compose down

# 2. Заменить HBK-файл (сохраните обязательное имя)
Copy-Item "C:\path\to\shcntx_ru.hbk" "data\hbk\shcntx_ru.hbk"

# 3. Запустить и переиндексировать
docker compose up -d
Invoke-RestMethod -Uri "http://localhost:8000/index/rebuild" -Method Post
```

**Подробнее**: [DEPLOYMENT_GUIDE.md](docs/instructions/DEPLOYMENT_GUIDE.md#обновление-hbk-файла)

## 📋 MCP Protocol

Сервер реализует [Model Context Protocol 2025-06-18](https://modelcontextprotocol.io/specification/2025-06-18/index) со следующими tools:

- `find_1c_help` - поиск справки по элементам 1С
- `get_syntax_info` - полная информация об элементе и его синтаксисе
- `get_quick_reference` - краткая справка об элементе
- `search_by_context` - поиск с фильтром по контексту
- `list_object_members` - список элементов объекта

## ⚡ Performance

- Время отклика поиска: < 500ms
- Поддержка 8 одновременных пользователей
- Размер индекса: ~32MB (80% от 40MB .hbk файла)
- Потребление памяти: ~2GB (1GB ES + 1GB MCP сервер)

## 🐛 Поддержка

При возникновении проблем:

1. Проверить логи: `docker compose logs mcp-server`
2. Проверить статус Elasticsearch: `Invoke-RestMethod -Uri "http://localhost:9200/_cluster/health"`
3. Проверить статус индексации: `Invoke-RestMethod -Uri "http://localhost:8000/index/status"`

**Подробнее**: [DEPLOYMENT_GUIDE.md](docs/instructions/DEPLOYMENT_GUIDE.md#-устранение-проблем)

## 📄 Лицензия

MIT License

---

**Разработано для работы с документацией 1С:Предприятие 8.3.24+**
