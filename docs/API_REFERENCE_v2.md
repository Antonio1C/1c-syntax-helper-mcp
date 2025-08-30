# API Reference v2.0 - 1C Syntax Helper MCP Server

## Обзор

Этот документ содержит полное описание REST API для MCP сервера синтаксис-помощника 1С версии 2.0. API предоставляет функции поиска по документации 1С, управления индексом и мониторинга системы.

## Базовый URL

```
http://localhost:8000
```

## Аутентификация

В текущей версии аутентификация не требуется.

## Rate Limiting

API использует ограничение скорости запросов:
- **60 запросов в минуту** на IP-адрес
- **1000 запросов в час** на IP-адрес

При превышении лимита возвращается статус `429 Too Many Requests` с заголовком `Retry-After`.

## Обработка ошибок

### Коды ошибок

- `400 Bad Request` - Ошибка валидации данных
- `404 Not Found` - Ресурс не найден
- `429 Too Many Requests` - Превышен лимит запросов
- `500 Internal Server Error` - Внутренняя ошибка сервера
- `503 Service Unavailable` - Elasticsearch недоступен

### Формат ошибок

```json
{
  "error": "Error type",
  "message": "Detailed error description"
}
```

## Эндпоинты

### 1. Проверка здоровья системы

**GET** `/health`

Проверяет состояние системы, подключение к Elasticsearch и наличие индекса.

#### Ответ

```json
{
  "status": "healthy|unhealthy",
  "elasticsearch": true,
  "index_exists": true,
  "documents_count": 1234
}
```

#### Поля ответа

- `status` - Общий статус системы
- `elasticsearch` - Статус подключения к Elasticsearch
- `index_exists` - Существует ли индекс
- `documents_count` - Количество документов в индексе

---

### 2. Статус индекса

**GET** `/index/status`

Получает детальную информацию о состоянии индекса.

#### Ответ

```json
{
  "elasticsearch_connected": true,
  "index_exists": true,
  "documents_count": 1234,
  "index_name": "help1c_docs"
}
```

---

### 3. Переиндексация

**POST** `/index/rebuild`

Запускает переиндексацию документации из .hbk файла.

#### Ответ

```json
{
  "status": "success|error",
  "message": "Описание результата",
  "documents_indexed": 1234,
  "file_processed": "/path/to/file.hbk"
}
```

---

### 4. Получение доступных инструментов

**GET** `/tools`

Возвращает список доступных MCP инструментов.

#### Ответ

```json
{
  "tools": [
    {
      "name": "search_1c_syntax",
      "description": "Поиск по синтаксису и документации 1С",
      "parameters": {
        "query": {
          "type": "string",
          "description": "Поисковый запрос"
        },
        "limit": {
          "type": "integer",
          "description": "Максимальное количество результатов (по умолчанию: 20)"
        }
      }
    }
  ]
}
```

---

### 5. Выполнение MCP запроса

**POST** `/mcp`

Выполняет MCP запрос для поиска по документации.

#### Тело запроса

```json
{
  "tool": "search_1c_syntax",
  "arguments": {
    "query": "СтрДлина",
    "limit": 10,
    "categories": ["functions"]
  }
}
```

#### Параметры

- `tool` (string, required) - Имя инструмента
- `arguments` (object, required) - Аргументы для инструмента

#### Валидация query

- Минимальная длина: 1 символ
- Максимальная длина: 1000 символов
- Запрещенные символы: `< > { } \ ; & | `

#### Ответ

```json
{
  "content": [
    {
      "type": "text",
      "text": "Результат поиска по документации 1С"
    }
  ],
  "error": null
}
```

---

### 6. Метрики системы

**GET** `/metrics`

Получение общих метрик системы и производительности.

#### Ответ

```json
{
  "metrics": {
    "counters": {
      "requests.total": 1500,
      "requests.search": 1200,
      "errors.total": 15
    },
    "gauges": {
      "system.cpu.usage_percent": 25.5,
      "system.memory.usage_percent": 68.2,
      "system.disk.free_gb": 45.8
    },
    "timers": {
      "request.duration": {
        "count": 1500,
        "avg": 0.156,
        "min": 0.012,
        "max": 2.345
      }
    }
  },
  "performance": {
    "total_requests": 1500,
    "successful_requests": 1485,
    "failed_requests": 15,
    "success_rate": 99.0,
    "avg_response_time": 0.156,
    "max_response_time": 2.345,
    "min_response_time": 0.012,
    "current_active_requests": 3
  },
  "rate_limiting": {
    "active_clients": 25,
    "total_requests_tracked": 5678
  }
}
```

---

### 7. Метрики клиента

**GET** `/metrics/{client_id}`

Получение метрик rate limiting для конкретного клиента.

#### Параметры пути

- `client_id` (string) - Идентификатор клиента (обычно IP-адрес)

#### Ответ

```json
{
  "client_id": "192.168.1.100",
  "rate_limiting": {
    "requests_per_minute": 15,
    "requests_per_hour": 234,
    "limit_per_minute": 60,
    "limit_per_hour": 1000,
    "remaining_minute": 45,
    "remaining_hour": 766
  }
}
```

## Инструменты MCP

### search_1c_syntax

Поиск по синтаксису и документации 1С.

#### Параметры

- `query` (string, required) - Поисковый запрос
- `limit` (integer, optional) - Максимальное количество результатов (1-100, по умолчанию: 20)
- `offset` (integer, optional) - Смещение для пагинации (по умолчанию: 0)
- `timeout` (integer, optional) - Таймаут поиска в секундах (1-300, по умолчанию: 30)
- `min_score` (float, optional) - Минимальный скор для результатов (0.0-1.0, по умолчанию: 0.1)
- `categories` (array[string], optional) - Фильтр по категориям

#### Пример использования

```json
{
  "tool": "search_1c_syntax",
  "arguments": {
    "query": "СтрДлина строка",
    "limit": 5,
    "categories": ["functions", "methods"]
  }
}
```

### get_1c_function_details

Получение детальной информации о функции 1С.

#### Параметры

- `function_name` (string, required) - Название функции

### get_1c_object_info

Получение информации об объекте 1С.

#### Параметры

- `object_name` (string, required) - Название объекта

## Мониторинг и метрики

### Системные метрики

Сервер автоматически собирает следующие метрики:

- **CPU**: Использование процессора
- **Memory**: Использование памяти
- **Disk**: Свободное место на диске
- **Network**: Статистика сети (если доступно)

### Метрики производительности

- **Счетчики**: Общее количество запросов, успешных/неуспешных запросов
- **Таймеры**: Время выполнения запросов
- **Gauges**: Текущие значения системных ресурсов

### Rate Limiting

Каждый клиент отслеживается по IP-адресу с ограничениями:

- 60 запросов в минуту
- 1000 запросов в час

## Безопасность

### Валидация входных данных

Все входные данные проходят строгую валидацию:

- Проверка размера payload (максимум 1MB)
- Валидация типов данных
- Санитизация строк
- Проверка на path traversal

### Безопасные операции

- Все системные команды выполняются через безопасный subprocess
- Валидация имен файлов и путей
- Ограничение размера обрабатываемых файлов
- Таймауты для всех операций

## Конфигурация

### Переменные окружения

- `ELASTICSEARCH_HOST` - Хост Elasticsearch (по умолчанию: localhost)
- `ELASTICSEARCH_PORT` - Порт Elasticsearch (по умолчанию: 9200)
- `ELASTICSEARCH_INDEX` - Имя индекса (по умолчанию: help1c_docs)
- `SERVER_HOST` - Хост сервера (по умолчанию: 0.0.0.0)
- `SERVER_PORT` - Порт сервера (по умолчанию: 8000)
- `LOG_LEVEL` - Уровень логирования (по умолчанию: INFO)

### Лимиты по умолчанию

- Максимальный размер файла: 50MB
- Размер батча для индексации: 100 документов
- Таймаут Elasticsearch: 30 секунд
- Максимальное количество результатов поиска: 100

## Примеры использования

### Поиск функций

```bash
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "search_1c_syntax",
    "arguments": {
      "query": "СтрДлина",
      "limit": 5
    }
  }'
```

### Проверка статуса

```bash
curl http://localhost:8000/health
```

### Переиндексация

```bash
curl -X POST http://localhost:8000/index/rebuild
```

### Получение метрик

```bash
curl http://localhost:8000/metrics
```

## Changelog

### v2.0.0 (текущая версия)

- ✅ Добавлен rate limiting (60/мин, 1000/час)
- ✅ Улучшена валидация входных данных (pydantic модели)
- ✅ Добавлены метрики и мониторинг системы
- ✅ Реализован dependency injection
- ✅ Улучшена обработка ошибок (специфичные исключения)
- ✅ Добавлена безопасность subprocess операций
- ✅ Константы вынесены в отдельный модуль
- ✅ Обновлена документация API

### v1.0.0

- Базовая функциональность поиска
- Индексация .hbk файлов
- MCP протокол
- Интеграция с Elasticsearch

## Архитектурные улучшения

### Исправленные проблемы

1. **Небезопасный subprocess** → Безопасный модуль `src.core.utils.safe_subprocess_run`
2. **Отсутствие валидации** → Строгая валидация через `src.core.validation`
3. **Глобальные состояния** → Dependency injection через `src.core.dependency_injection`
4. **Магические числа** → Константы в `src.core.constants`
5. **Отсутствие rate limiting** → Модуль `src.core.rate_limiter`
6. **Улучшение обработки ошибок** → Специфичные исключения
7. **Добавление метрик** → Модуль `src.core.metrics`
8. **Улучшение типизации** → Строгая типизация во всех модулях
9. **Документация API** → Полная документация с примерами

### Производительность

- Асинхронная обработка запросов
- Batch индексация документов
- Кэширование подключений
- Мониторинг ресурсов системы
- Rate limiting для защиты от перегрузки
