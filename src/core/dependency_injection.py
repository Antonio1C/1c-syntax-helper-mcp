"""
Модуль Dependency Injection для управления зависимостями.
"""

from typing import Any, Dict, Type, TypeVar, Optional, Callable
from abc import ABC, abstractmethod
import inspect
from src.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


class DIContainer:
    """Контейнер для dependency injection."""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._singletons: Dict[str, Any] = {}
    
    def register_singleton(self, interface: Type[T], implementation: T, name: Optional[str] = None):
        """
        Регистрация singleton сервиса.
        
        Args:
            interface: Интерфейс или тип
            implementation: Реализация
            name: Имя сервиса (опционально)
        """
        service_name = name or interface.__name__
        self._singletons[service_name] = implementation
        logger.debug(f"Registered singleton: {service_name}")
    
    def register_factory(self, interface: Type[T], factory: Callable[[], T], name: Optional[str] = None):
        """
        Регистрация фабрики для создания сервиса.
        
        Args:
            interface: Интерфейс или тип
            factory: Фабричная функция
            name: Имя сервиса (опционально)
        """
        service_name = name or interface.__name__
        self._factories[service_name] = factory
        logger.debug(f"Registered factory: {service_name}")
    
    def register_instance(self, interface: Type[T], instance: T, name: Optional[str] = None):
        """
        Регистрация конкретного экземпляра.
        
        Args:
            interface: Интерфейс или тип
            instance: Экземпляр
            name: Имя сервиса (опционально)
        """
        service_name = name or interface.__name__
        self._services[service_name] = instance
        logger.debug(f"Registered instance: {service_name}")
    
    def get(self, interface: Type[T], name: Optional[str] = None) -> T:
        """
        Получение сервиса из контейнера.
        
        Args:
            interface: Интерфейс или тип
            name: Имя сервиса (опционально)
            
        Returns:
            Экземпляр сервиса
            
        Raises:
            DIError: Если сервис не найден
        """
        service_name = name or interface.__name__
        
        # Проверяем singleton
        if service_name in self._singletons:
            return self._singletons[service_name]
        
        # Проверяем обычные экземпляры
        if service_name in self._services:
            return self._services[service_name]
        
        # Создаем через фабрику
        if service_name in self._factories:
            instance = self._factories[service_name]()
            return instance
        
        raise DIError(f"Service not found: {service_name}")
    
    def resolve(self, cls: Type[T]) -> T:
        """
        Автоматическое разрешение зависимостей через конструктор.
        
        Args:
            cls: Класс для создания
            
        Returns:
            Экземпляр класса с внедренными зависимостями
        """
        try:
            # Получаем сигнатуру конструктора
            sig = inspect.signature(cls.__init__)
            params = {}
            
            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue
                
                # Пытаемся найти зависимость по типу
                if param.annotation and param.annotation != inspect.Parameter.empty:
                    try:
                        params[param_name] = self.get(param.annotation)
                    except DIError:
                        # Если зависимость не найдена и есть значение по умолчанию
                        if param.default != inspect.Parameter.empty:
                            params[param_name] = param.default
                        else:
                            raise DIError(f"Cannot resolve dependency: {param_name} of type {param.annotation}")
            
            return cls(**params)
            
        except Exception as e:
            raise DIError(f"Failed to resolve class {cls.__name__}: {e}")


class DIError(Exception):
    """Исключение для ошибок dependency injection."""
    pass


# Интерфейсы для основных сервисов
class IElasticsearchClient(ABC):
    """Интерфейс клиента Elasticsearch."""
    
    @abstractmethod
    async def connect(self):
        """Подключение к Elasticsearch."""
        pass
    
    @abstractmethod
    async def search(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Поиск в Elasticsearch."""
        pass


class IHBKParser(ABC):
    """Интерфейс парсера HBK файлов."""
    
    @abstractmethod
    def parse_file(self, file_path: str):
        """Парсинг HBK файла."""
        pass


class ISearchService(ABC):
    """Интерфейс сервиса поиска."""
    
    @abstractmethod
    async def search(self, query: str, **kwargs):
        """Поиск документов."""
        pass


class IIndexer(ABC):
    """Интерфейс индексатора."""
    
    @abstractmethod
    async def index_documents(self, documents):
        """Индексация документов."""
        pass


# Глобальный контейнер
_global_container: Optional[DIContainer] = None


def get_container() -> DIContainer:
    """
    Получение глобального контейнера DI.
    
    Returns:
        Экземпляр DIContainer
    """
    global _global_container
    
    if _global_container is None:
        _global_container = DIContainer()
    
    return _global_container


def setup_dependencies():
    """Настройка зависимостей приложения."""
    container = get_container()
    
    # Регистрация основных сервисов будет происходить при инициализации приложения
    logger.info("DI container initialized")


def reset_container():
    """Сброс контейнера (для тестов)."""
    global _global_container
    _global_container = None
