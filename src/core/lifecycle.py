"""Application lifecycle management."""

from fastapi import FastAPI

from src.core.logging import get_logger
from src.core.elasticsearch import ElasticsearchClient
from src.core.metrics import get_metrics_collector, get_system_monitor
from src.core.dependency_injection import setup_dependencies
from src.core.startup import auto_index_on_startup

logger = get_logger(__name__)


async def startup(app: FastAPI):
    """
    Startup logic для приложения.
    
    Args:
        app: FastAPI application instance
    """
    logger.info("Запуск MCP сервера синтаксис-помощника 1С")
    
    metrics = get_metrics_collector()
    monitor = get_system_monitor()
    
    # Настройка dependency injection
    setup_dependencies()
    
    # Запуск мониторинга системы
    await monitor.start_monitoring(interval=60)
    
    # Создаём и подключаемся к Elasticsearch
    es_client = ElasticsearchClient()
    connected = await es_client.connect()
    
    if not connected:
        logger.error("Не удалось подключиться к Elasticsearch")
        await metrics.increment("startup.elasticsearch.connection_failed")
    else:
        logger.info("Успешно подключились к Elasticsearch")
        await metrics.increment("startup.elasticsearch.connection_success")
        
        # Сохраняем клиента в app.state
        app.state.es_client = es_client
        
        # Проверяем наличие .hbk файла и запускаем автоиндексацию
        await auto_index_on_startup(es_client)
    
    await metrics.increment("startup.completed")


async def shutdown(app: FastAPI):
    """
    Shutdown logic для приложения.
    
    Args:
        app: FastAPI application instance
    """
    logger.info("Остановка MCP сервера")
    
    metrics = get_metrics_collector()
    monitor = get_system_monitor()
    
    # Останавливаем мониторинг
    await monitor.stop_monitoring()
    
    # Отключаемся от Elasticsearch
    if hasattr(app.state, 'es_client'):
        await app.state.es_client.disconnect()
    
    await metrics.increment("shutdown.completed")
