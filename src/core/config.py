"""Конфигурация приложения."""

from pydantic import BaseModel
from pydantic_settings import BaseSettings
from typing import Optional
import os


class ElasticsearchConfig(BaseModel):
    """Конфигурация Elasticsearch."""
    url: str = "http://localhost:9200"
    index_name: str = "1c_docs_index"
    timeout: int = 30
    max_retries: int = 3


class ServerConfig(BaseModel):
    """Конфигурация сервера."""
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    log_level: str = "INFO"


class DataConfig(BaseModel):
    """Конфигурация данных."""
    hbk_directory: str = "/app/data/hbk"
    logs_directory: str = "/app/logs"
    
    
class Settings(BaseSettings):
    """Основные настройки приложения."""
    
    # Elasticsearch настройки
    elasticsearch_url: str = "http://localhost:9200"
    elasticsearch_index: str = "1c_docs_index"
    elasticsearch_timeout: int = 30
    
    # Сервер настройки
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    log_level: str = "INFO"
    
    # Пути к данным
    hbk_directory: str = "data/hbk"
    logs_directory: str = "data/logs"
    
    # Режим разработки
    debug: bool = False
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    @property
    def elasticsearch(self) -> ElasticsearchConfig:
        """Получить конфигурацию Elasticsearch."""
        return ElasticsearchConfig(
            url=self.elasticsearch_url,
            index_name=self.elasticsearch_index,
            timeout=self.elasticsearch_timeout
        )
    
    @property
    def server(self) -> ServerConfig:
        """Получить конфигурацию сервера."""
        return ServerConfig(
            host=self.server_host,
            port=self.server_port,
            log_level=self.log_level
        )
    
    @property
    def data(self) -> DataConfig:
        """Получить конфигурацию данных."""
        return DataConfig(
            hbk_directory=self.hbk_directory,
            logs_directory=self.logs_directory
        )


# Глобальный экземпляр настроек
settings = Settings()
