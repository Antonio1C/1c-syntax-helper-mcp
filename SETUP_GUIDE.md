# Инструкция по развертыванию MCP сервера синтаксис-помощника 1С

## Оглавление
1. [Системные требования](#системные-требования)
2. [Установка Docker Desktop](#установка-docker-desktop)
3. [Подготовка проекта](#подготовка-проекта)
4. [Запуск сервисов](#запуск-сервисов)
5. [Настройка VS Code](#настройка-vs-code)
6. [Проверка работы](#проверка-работы)
7. [Устранение неполадок](#устранение-неполадок)

---

## Системные требования

### Минимальные требования:
- **ОС**: Windows 10 64-bit Pro/Enterprise/Education (Build 19041+) или Windows 11 64-bit
- **Процессор**: 2+ ядра с поддержкой виртуализации
- **RAM**: 8 ГБ (минимум 4 ГБ для Elasticsearch)
- **Диск**: 10 ГБ свободного места
- **Сеть**: Доступ к интернету для скачивания образов Docker

### Проверка виртуализации:
1. Откройте "Диспетчер задач" → вкладка "Производительность" → "ЦП"
2. Убедитесь, что "Виртуализация" включена
3. Если отключена - включите в BIOS/UEFI

---

## Установка Docker Desktop

### Шаг 1: Скачивание
1. Перейдите на https://www.docker.com/products/docker-desktop/
2. Нажмите **"Download for Windows"**
3. Скачайте файл `Docker Desktop Installer.exe`

### Шаг 2: Установка
1. **Запустите установщик от имени администратора**
2. В мастере установки:
   - ✅ Отметьте "Add shortcut to desktop"
   - ✅ Отметьте "Use WSL 2 instead of Hyper-V" (рекомендуется)
3. Дождитесь завершения установки
4. **Перезагрузите компьютер**

### Шаг 3: Первый запуск
1. Запустите Docker Desktop из меню Пуск
2. Примите лицензионное соглашение
3. Выполните tutorial (опционально)
4. Дождитесь запуска Docker Engine (статус "Engine running")

### Шаг 4: Настройка ресурсов
1. Откройте Docker Desktop
2. Перейдите в **Settings** (⚙️ иконка)
3. Во вкладке **"Resources"** → **"Advanced"**:
   - **Memory**: 4096 MB (минимум для Elasticsearch)
   - **CPUs**: 2+ ядра
   - **Disk image size**: 60 GB
4. Нажмите **"Apply & Restart"**

### Шаг 5: Проверка установки
Откройте PowerShell и выполните:
```powershell
docker --version
docker compose version
```

Ожидаемый результат:
```
Docker version 24.0.x, build xxxxx
Docker Compose version v2.20.x
```

---

## Подготовка проекта

### Шаг 1: Клонирование репозитория
```powershell
git clone https://github.com/Antonio1C/1c-syntax-helper-mcp.git
cd 1c-syntax-helper-mcp
```

### Шаг 2: Подготовка .hbk файла
1. Скопируйте файл документации 1С (например, `1c_documentation.hbk`) в папку:
   ```
   data/hbk/1c_documentation.hbk
   ```

2. Проверьте наличие файла:
   ```powershell
   dir data\hbk\*.hbk
   ```

### Шаг 3: Настройка переменных окружения (опционально)
Создайте файл `.env` в корне проекта:
```bash
# Elasticsearch настройки
ELASTICSEARCH_URL=http://elasticsearch:9200
ELASTICSEARCH_INDEX=1c_docs

# MCP сервер настройки  
LOG_LEVEL=INFO
MAX_CONCURRENT_REQUESTS=8

# Настройки индексации
INDEX_BATCH_SIZE=100
REINDEX_ON_STARTUP=true

# Настройки поиска
SEARCH_MAX_RESULTS=50
SEARCH_TIMEOUT_SECONDS=30
```

---

## Запуск сервисов

### Вариант 1: Запуск всех сервисов
```powershell
# Запуск всех сервисов в фоновом режиме
docker compose up -d

# Просмотр логов
docker compose logs -f
```

### Вариант 2: Поэтапный запуск

#### 1. Запуск только Elasticsearch
```powershell
docker compose up elasticsearch -d
```

#### 2. Проверка готовности Elasticsearch
```powershell
# Ждем готовности (может занять 1-2 минуты)
docker compose logs elasticsearch

# Проверка здоровья
curl http://localhost:9200/_cluster/health
```

#### 3. Запуск MCP сервера
```powershell
docker compose up mcp-server -d
```

### Проверка статуса сервисов
```powershell
# Статус контейнеров
docker compose ps

# Логи сервисов
docker compose logs elasticsearch
docker compose logs mcp-server
```

---

## Настройка VS Code

### Шаг 1: Установка расширения MCP
1. Откройте VS Code
2. Перейдите в Extensions (Ctrl+Shift+X)
3. Найдите и установите **"Model Context Protocol"** расширение
4. Перезапустите VS Code

### Шаг 2: Настройка MCP клиента

#### Способ 1: Через настройки VS Code
1. Откройте настройки VS Code (Ctrl+,)
2. Найдите "MCP" в поиске
3. Добавьте новый сервер:
   - **Name**: `1C Syntax Helper`
   - **Command**: `curl`
   - **Args**: 
     ```json
     [
       "-X", "POST",
       "-H", "Content-Type: application/json",
       "-d", "@-",
       "http://localhost:8000/mcp"
     ]
     ```

#### Способ 2: Через конфигурационный файл
Создайте файл `~/.config/mcp/settings.json`:
```json
{
  "servers": {
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

### Шаг 3: Активация MCP
1. Откройте Command Palette (Ctrl+Shift+P)
2. Выполните команду: `MCP: Connect to Server`
3. Выберите `1C Syntax Helper` из списка
4. Дождитесь подключения

---

## Проверка работы

### Шаг 1: Проверка API сервера
```powershell
# Проверка здоровья
curl http://localhost:8000/health

# Статус индексации
curl http://localhost:8000/index/status

# Список доступных MCP инструментов
curl http://localhost:8000/mcp/tools
```

### Шаг 2: Тестирование поиска через API
```powershell
# Тест поиска
curl -X POST http://localhost:8000/mcp `
  -H "Content-Type: application/json" `
  -d '{
    "tool": "search_1c_syntax",
    "arguments": {
      "query": "СтрДлина"
    }
  }'
```

### Шаг 3: Тестирование в VS Code
1. Откройте новый файл в VS Code
2. Активируйте ИИ-ассистента (например, GitHub Copilot Chat)
3. Задайте вопрос: "Найди информацию о функции СтрДлина в 1С"
4. Ассистент должен использовать MCP инструменты для поиска

---

## Устранение неполадок

### Проблема: Docker не запускается
**Решение:**
1. Убедитесь, что виртуализация включена в BIOS
2. Проверьте, что WSL 2 установлен:
   ```powershell
   wsl --list --verbose
   ```
3. Обновите WSL:
   ```powershell
   wsl --update
   ```

### Проблема: Elasticsearch не стартует
**Решение:**
1. Увеличьте память для Docker до 4+ ГБ
2. Проверьте логи:
   ```powershell
   docker compose logs elasticsearch
   ```
3. Очистите данные Elasticsearch:
   ```powershell
   docker compose down -v
   docker compose up elasticsearch -d
   ```

### Проблема: MCP сервер не подключается
**Решение:**
1. Проверьте статус сервера:
   ```powershell
   curl http://localhost:8000/health
   ```
2. Проверьте логи:
   ```powershell
   docker compose logs mcp-server
   ```
3. Перезапустите сервер:
   ```powershell
   docker compose restart mcp-server
   ```

### Проблема: Индексация не работает
**Решение:**
1. Убедитесь, что .hbk файл находится в `data/hbk/`
2. Запустите переиндексацию:
   ```powershell
   curl -X POST http://localhost:8000/index/rebuild
   ```
3. Проверьте логи индексации:
   ```powershell
   docker compose logs mcp-server | findstr "индекс"
   ```

### Проблема: VS Code не видит MCP расширение
**Решение:**
1. Обновите VS Code до последней версии
2. Переустановите MCP расширение
3. Проверьте настройки брандмауэра (порт 8000 должен быть открыт)

---

## Полезные команды

### Управление сервисами
```powershell
# Запуск
docker compose up -d

# Остановка
docker compose down

# Перезапуск
docker compose restart

# Обновление образов
docker compose pull
docker compose up -d

# Очистка всех данных
docker compose down -v
```

### Мониторинг
```powershell
# Статус контейнеров
docker compose ps

# Использование ресурсов
docker stats

# Логи в реальном времени
docker compose logs -f

# Логи конкретного сервиса
docker compose logs elasticsearch
docker compose logs mcp-server
```

### Отладка
```powershell
# Подключение к контейнеру
docker compose exec mcp-server bash

# Проверка индекса Elasticsearch
curl "http://localhost:9200/1c_docs_index/_search?pretty&size=5"

# Статистика индекса
curl "http://localhost:9200/1c_docs_index/_stats?pretty"
```

---

## Поддержка

При возникновении проблем:

1. **Проверьте логи** сервисов
2. **Убедитесь** в соответствии системным требованиям  
3. **Обратитесь** к разделу "Устранение неполадок"
4. **Создайте issue** в GitHub репозитории с описанием проблемы и логами

**Контакты:**
- GitHub: https://github.com/Antonio1C/1c-syntax-helper-mcp
- Документация: [docs/](docs/)
