# Инструкция по подключению к удаленному Docker

## Шаг 1: Запуск Elasticsearch на удаленном компьютере

На компьютере с установленным Docker:

### 1.1 Создайте директорию проекта
```powershell
New-Item -ItemType Directory -Path .\1c-elasticsearch -Force
Set-Location .\1c-elasticsearch
```

### 1.2 Создайте docker-compose.yml
Создайте файл `docker-compose.yml` с содержимым:

```yaml
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:9.1.0
    container_name: es-1c-helper
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms1g -Xmx1g"
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data
    ports:
      - "9200:9200"
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:9200/_cluster/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 5

volumes:
  elasticsearch_data:
```

### 1.3 Запустите Elasticsearch
```powershell
# Запустите Elasticsearch
docker compose up -d

# Проверьте статус
docker compose ps

# Проверьте логи
docker compose logs elasticsearch

# Проверьте доступность Elasticsearch на удалённом компьютере
Invoke-RestMethod -Uri "http://localhost:9200"
```

## Шаг 2: Узнайте IP-адрес компьютера с Docker

На компьютере с Docker:

В PowerShell на компьютере с Docker:
```powershell
Get-NetIPConfiguration
```
Найдите IPv4-адрес сетевого адаптера локальной сети (обычно `192.168.x.x` или `10.x.x.x`).

## Шаг 3: Настройка подключения на этом компьютере

1. Перейдите в корень клона проекта и скопируйте шаблон окружения:
```powershell
Copy-Item .env.example .env
```

2. Откройте `.env` и задайте IP компьютера с Elasticsearch:
```powershell
notepad .env
```
Замените значение `ELASTICSEARCH_HOST=localhost` на адрес из шага 2, например `ELASTICSEARCH_HOST=192.168.1.100`.

## Шаг 4: Подготовка HBK и 7-Zip

Файл справки не входит в репозиторий. Скопируйте `shcntx_ru.hbk` из установленной поставки справки 1С в `data\hbk\shcntx_ru.hbk` в корне проекта. Это имя требуется для автоматической индексации при запуске.

Проверьте наличие файла:
```powershell
Get-Item .\data\hbk\shcntx_ru.hbk
```

Для разбора HBK на компьютере с MCP-сервером должен быть установлен 7-Zip. Парсер ищет `7z.exe` в `PATH` и стандартных каталогах установки.

## Шаг 5: Подготовка Python окружения

В PowerShell, из корня проекта:
```powershell
py -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Шаг 6: Проверка подключения

Запустите тест подключения:

```powershell
# Проверьте подключение к Elasticsearch
@'
import asyncio
from src.core.elasticsearch import es_client

async def main():
  try:
    connected = await es_client.connect()
    print(f'Подключение: {connected}')
  finally:
    await es_client.disconnect()

asyncio.run(main())
'@ | python -
```

## Шаг 7: Тестирование индексации

Если подключение успешно и HBK-файл с 7-Zip подготовлены, запустите тесты через pytest:

```powershell
python -m pytest -v tests/test_parsing.py tests/test_indexing.py
```

## Шаг 8: Запуск MCP сервера

```powershell
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

## Шаг 9: Проверка работы API

На компьютере с MCP-сервером откройте в браузере:
- http://localhost:8000/health - проверка состояния
- http://localhost:8000/docs - Swagger UI
- http://localhost:8000/metrics - метрики системы

## Возможные проблемы и решения

### Проблема: Не удается подключиться к Elasticsearch

**Решения:**
1. Проверьте, что Elasticsearch запущен: `docker compose ps`
2. Проверьте firewall на компьютере с Docker
3. Убедитесь, что порт 9200 открыт
4. С компьютера с MCP-сервером проверьте порт командой `Test-NetConnection -ComputerName $EsHost -Port 9200`
5. Проверьте HTTP-доступ: `Invoke-RestMethod -Uri "http://$($EsHost):9200"`

### Проблема: TimeoutError

**Решения:**
1. Увеличьте таймаут в `.env`: `ELASTICSEARCH_TIMEOUT=60`
2. Проверьте скорость сети между компьютерами

### Проблема: Connection refused

**Решения:**
1. Проверьте правильность IP-адреса
2. Убедитесь, что Docker Elasticsearch слушает на 0.0.0.0:9200, а не только localhost

## Команды для отладки

```powershell
# На компьютере с Docker: статус контейнера и опубликованный порт
docker compose ps
Get-NetTCPConnection -State Listen -LocalPort 9200

# На компьютере с MCP-сервером: укажите IP компьютера с Docker
$EsHost = "192.168.1.100"
Test-NetConnection -ComputerName $EsHost -Port 9200

# Проверка HTTP-ответа Elasticsearch
Invoke-RestMethod -Uri "http://$($EsHost):9200"
```
