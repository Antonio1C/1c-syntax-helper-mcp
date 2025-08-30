# Настройка VS Code MCP Extension

## Предварительные требования

- VS Code версии 1.85+
- Запущенный MCP сервер на `localhost:8000`
- Активное подключение к интернету

## Установка MCP расширения

### Способ 1: Через магазин расширений VS Code

1. Откройте VS Code
2. Нажмите `Ctrl+Shift+X` (Extensions)
3. Найдите **"Model Context Protocol"**
4. Нажмите **Install**
5. Перезапустите VS Code

### Способ 2: Через команду

```bash
code --install-extension ms-vscode.vscode-mcp
```

## Настройка подключения к серверу

### Метод 1: Через настройки UI

1. Откройте VS Code Settings (`Ctrl+,`)
2. Найдите "MCP" в поиске
3. Нажмите **"Edit in settings.json"**
4. Добавьте конфигурацию сервера

### Метод 2: Прямое редактирование settings.json

1. Откройте Command Palette (`Ctrl+Shift+P`)
2. Выполните команду: `Preferences: Open Settings (JSON)`
3. Добавьте следующую конфигурацию:

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
      ],
      "env": {},
      "cwd": "",
      "timeout": 30000
    }
  },
  "mcp.autoConnect": true,
  "mcp.logging.level": "info"
}
```

## Подключение к серверу

### Автоматическое подключение

Если включен `"mcp.autoConnect": true`, VS Code автоматически подключится к серверу при запуске.

### Ручное подключение

1. Откройте Command Palette (`Ctrl+Shift+P`)
2. Выполните команду: `MCP: Connect to Server`
3. Выберите `1c-syntax-helper` из списка
4. Дождитесь сообщения "Connected"

## Использование MCP инструментов

### Через Chat интерфейс

1. Откройте VS Code Chat (`Ctrl+Shift+I`)
2. Введите команду с использованием 1С синтаксиса:

```
Найди информацию о функции СтрДлина в 1С
```

```
Покажи все методы объекта ТаблицаЗначений
```

```
Как использовать функцию ВРег в 1С?
```

### Через GitHub Copilot

Если у вас установлен GitHub Copilot:

1. Откройте Copilot Chat
2. Задайте вопросы о 1С:

```
@workspace Объясни синтаксис функции СтрНайти в 1С
```

## Доступные MCP команды

### 1. search_1c_syntax
Поиск по синтаксису 1С
- **Параметры**: query (строка поиска), limit (количество результатов)
- **Пример**: "СтрДлина", "ТаблицаЗначений.Добавить"

### 2. get_1c_function_details  
Подробная информация о функции
- **Параметры**: function_name (точное имя функции)
- **Пример**: "СтрДлина", "ВРег"

### 3. get_1c_object_info
Информация об объекте 1С
- **Параметры**: object_name (имя объекта)  
- **Пример**: "ТаблицаЗначений", "Запрос"

## Проверка работы

### 1. Проверка подключения

```
Command Palette → MCP: Show Server Status
```

Должен отображаться статус: `1c-syntax-helper: Connected`

### 2. Тест поиска

В Chat введите:
```
Найди информацию о функции СтрДлина
```

Ожидаемый результат: подробная информация о функции с синтаксисом и примерами.

### 3. Проверка логов

```
Command Palette → MCP: Show Logs
```

## Устранение неполадок

### Проблема: "Server not found"

**Решение:**
1. Убедитесь, что MCP сервер запущен:
   ```bash
   curl http://localhost:8000/health
   ```
2. Проверьте настройки в `settings.json`
3. Перезапустите VS Code

### Проблема: "Connection timeout"

**Решение:**
1. Увеличьте timeout в настройках:
   ```json
   "timeout": 60000
   ```
2. Проверьте брандмауэр (порт 8000)
3. Проверьте логи сервера

### Проблема: "No response from server"

**Решение:**
1. Проверьте логи MCP сервера:
   ```bash
   docker compose logs mcp-server
   ```
2. Убедитесь, что Elasticsearch запущен:
   ```bash
   curl http://localhost:9200/_cluster/health
   ```
3. Перезапустите сервисы:
   ```bash
   docker compose restart
   ```

### Проблема: "MCP extension not working"

**Решение:**
1. Обновите VS Code до последней версии
2. Переустановите MCP расширение
3. Очистите кэш VS Code:
   - Windows: `%APPDATA%\Code\User\workspaceStorage`
   - Удалите папки с кэшем

## Полезные команды VS Code

```
Ctrl+Shift+P → MCP: Connect to Server
Ctrl+Shift+P → MCP: Disconnect from Server  
Ctrl+Shift+P → MCP: Show Server Status
Ctrl+Shift+P → MCP: Show Logs
Ctrl+Shift+P → MCP: Restart Server
```

## Примеры использования

### Поиск функций
```
Ассистент: Найди все функции для работы со строками в 1С
```

### Информация об объектах
```  
Ассистент: Покажи все методы объекта Запрос в 1С
```

### Помощь с синтаксисом
```
Ассистент: Как правильно использовать функцию ЗначениеЗаполнено в 1С?
```

### Примеры кода
```
Ассистент: Покажи пример использования ТаблицаЗначений.Добавить
```
