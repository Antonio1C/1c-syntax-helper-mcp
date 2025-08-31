# Инструкция по подключению к удаленному Docker

## Шаг 1: Запуск Elasticsearch на удаленном компьютере

На компьютере с установленным Docker:

### 1.1 Создайте директорию проекта
```bash
mkdir 1c-elasticsearch
cd 1c-elasticsearch
```

### 1.2 Создайте docker-compose.yml
Создайте файл `docker-compose.yml` с содержимым:

```yaml
version: '3.8'

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
```bash
# Запустите Elasticsearch
docker-compose up elasticsearch -d

# Проверьте статус
docker-compose ps

# Проверьте логи
docker-compose logs elasticsearch
```

## Шаг 2: Узнайте IP-адрес компьютера с Docker

На компьютере с Docker:

**Windows:**
```cmd
ipconfig
```

**Linux/Mac:**
```bash
ip addr show
# или
ifconfig
```

Найдите IP-адрес в локальной сети (обычно 192.168.x.x или 10.x.x.x)

## Шаг 3: Настройка подключения на этом компьютере

1. Скопируйте `.env.example` в `.env`:
```bash
cp .env.example .env
```

2. Отредактируйте `.env` файл, заменив IP-адрес:
```bash
ELASTICSEARCH_HOST=192.168.1.100  # Замените на реальный IP
```

## Шаг 4: Проверка подключения

Запустите тест подключения:

```bash
# Активируйте виртуальное окружение
.\venv\Scripts\Activate.ps1

# Проверьте подключение к Elasticsearch
python -c "
import asyncio
from src.core.elasticsearch import es_client

async def test():
    connected = await es_client.connect()
    print(f'Подключение: {connected}')
    if connected:
        print('✅ Elasticsearch доступен!')
    else:
        print('❌ Не удалось подключиться к Elasticsearch')

asyncio.run(test())
"
```

## Шаг 5: Тестирование индексации

Если подключение успешно, запустите тест парсинга и индексации:

```bash
python tests/test_parsing.py
python tests/test_indexing.py
```

## Шаг 6: Запуск MCP сервера

```bash
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

## Шаг 7: Проверка работы API

Откройте в браузере:
- http://localhost:8000/health - проверка состояния
- http://localhost:8000/docs - Swagger UI
- http://localhost:8000/metrics - метрики системы

## Возможные проблемы и решения

### Проблема: Не удается подключиться к Elasticsearch

**Решения:**
1. Проверьте, что Elasticsearch запущен: `docker-compose ps`
2. Проверьте firewall на компьютере с Docker
3. Убедитесь, что порт 9200 открыт
4. Попробуйте подключиться браузером: `http://IP:9200`

### Проблема: TimeoutError

**Решения:**
1. Увеличьте таймаут в `.env`: `ELASTICSEARCH_TIMEOUT=60`
2. Проверьте скорость сети между компьютерами

### Проблема: Connection refused

**Решения:**
1. Проверьте правильность IP-адреса
2. Убедитесь, что Docker Elasticsearch слушает на 0.0.0.0:9200, а не только localhost

## Команды для отладки

```bash
# Проверка портов на удаленном компьютере
netstat -tlnp | grep 9200

# Проверка подключения с этого компьютера
telnet IP_ADDRESS 9200

# Проверка через curl
curl http://IP_ADDRESS:9200
```
