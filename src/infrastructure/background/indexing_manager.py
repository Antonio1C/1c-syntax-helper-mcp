"""Менеджер фоновой индексации."""

import asyncio
from datetime import datetime
from typing import Optional, Callable
from pathlib import Path

from src.core.logging import get_logger
from src.core.elasticsearch import ElasticsearchClient
from src.models.index_status import IndexingStatus, IndexProgressInfo

logger = get_logger(__name__)


class BackgroundIndexingManager:
    """
    Менеджер фоновой индексации без retry механизма.
    
    При ошибке индексации статус устанавливается в FAILED.
    Пользователь может запустить повторную индексацию вручную через API.
    """
    
    def __init__(
        self,
        shutdown_timeout: int = 30,
        progress_log_interval: int = 1000
    ):
        """
        Инициализация менеджера.
        
        Args:
            shutdown_timeout: Максимальное время ожидания при shutdown (сек)
            progress_log_interval: Интервал логирования прогресса (количество документов)
        """
        self._shutdown_timeout = shutdown_timeout
        self._progress_log_interval = progress_log_interval
        
        self._current_task: Optional[asyncio.Task] = None
        self._progress_info = IndexProgressInfo(status=IndexingStatus.IDLE)
        self._lock = asyncio.Lock()
        self._should_stop = False
    
    async def start_indexing(
        self, 
        file_path: str, 
        es_client: ElasticsearchClient
    ) -> None:
        """
        Запустить индексацию в фоновом режиме.
        
        Выполняется одна попытка. При ошибке устанавливается status=FAILED.
        
        Args:
            file_path: Путь к .hbk файлу
            es_client: Клиент Elasticsearch
        """
        if self.is_indexing():
            logger.warning("Индексация уже выполняется, пропускаем запрос")
            return
        
        logger.info(f"Создание фоновой задачи индексации для файла: {file_path}")
        
        # Создаём фоновую задачу
        self._current_task = asyncio.create_task(
            self._do_indexing(file_path, es_client)
        )
    
    async def _do_indexing(
        self, 
        file_path: str, 
        es_client: ElasticsearchClient
    ):
        """
        Выполнить индексацию (внутренний метод).
        
        Args:
            file_path: Путь к .hbk файлу
            es_client: Клиент Elasticsearch
        """
        try:
            # Устанавливаем статус IN_PROGRESS
            async with self._lock:
                self._progress_info = IndexProgressInfo(
                    status=IndexingStatus.IN_PROGRESS,
                    file_path=file_path,
                    start_time=datetime.now()
                )
            
            logger.info(f"Начата фоновая индексация файла: {file_path}")
            
            # Проверяем существование файла
            if not Path(file_path).exists():
                raise FileNotFoundError(f"Файл не найден: {file_path}")
            
            # Парсим .hbk файл в отдельном потоке (не блокируем event loop)
            from src.parsers.hbk_parser import HBKParser
            parser = HBKParser()
            
            # Запускаем синхронный парсинг в executor
            loop = asyncio.get_event_loop()
            parsed_hbk = await loop.run_in_executor(
                None,  # Использует default ThreadPoolExecutor
                parser.parse_file,
                file_path
            )
            
            if not parsed_hbk or not parsed_hbk.documentation:
                raise ValueError("Не удалось распарсить файл или документация пуста")
            
            total = len(parsed_hbk.documentation)
            logger.info(f"Найдено {total} документов для индексации")
            
            # Обновляем total_documents
            async with self._lock:
                self._progress_info.total_documents = total
            
            # Индексируем с прогрессом
            from src.parsers.indexer import ElasticsearchIndexer
            indexer = ElasticsearchIndexer(es_client)
            
            success = await indexer.reindex_all(
                parsed_hbk,
                progress_callback=self._update_progress
            )
            
            if not success:
                raise RuntimeError("Индексация вернула False")
            
            # Успех - устанавливаем статус COMPLETED
            async with self._lock:
                self._progress_info.status = IndexingStatus.COMPLETED
                self._progress_info.end_time = datetime.now()
                self._progress_info.indexed_documents = total
            
            duration = self._progress_info.duration_seconds
            logger.info(
                f"✅ Индексация завершена успешно: {total} документов за {duration:.1f} сек"
            )
                
        except asyncio.CancelledError:
            # Задача отменена (shutdown)
            logger.warning("Индексация отменена (shutdown)")
            async with self._lock:
                self._progress_info.status = IndexingStatus.FAILED
                self._progress_info.error_message = "Индексация отменена"
                self._progress_info.end_time = datetime.now()
            raise
            
        except Exception as e:
            # Ошибка индексации - логируем и сохраняем в статус
            error_msg = f"Ошибка индексации: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            async with self._lock:
                self._progress_info.status = IndexingStatus.FAILED
                self._progress_info.error_message = error_msg
                self._progress_info.end_time = datetime.now()
        
        finally:
            self._current_task = None
    
    def _update_progress(self, indexed: int, total: int):
        """
        Callback для обновления прогресса индексации.
        
        Вызывается синхронно из indexer, логирует каждые N документов.
        
        Args:
            indexed: Количество проиндексированных документов
            total: Общее количество документов
        """
        # Обновляем прогресс (синхронно, т.к. вызывается из sync кода)
        self._progress_info.indexed_documents = indexed
        self._progress_info.total_documents = total
        
        # Логируем только каждые N документов или в конце
        if indexed % self._progress_log_interval == 0 or indexed == total:
            progress_pct = (indexed / total * 100) if total > 0 else 0
            logger.info(f"Прогресс индексации: {indexed}/{total} ({progress_pct:.1f}%)")
    
    async def graceful_shutdown(self, timeout: Optional[int] = None) -> bool:
        """
        Graceful shutdown с ожиданием завершения индексации.
        
        Args:
            timeout: Максимальное время ожидания в секундах.
                    Если None, используется self._shutdown_timeout
        
        Returns:
            True если индексация успешно завершена, False если прервана по таймауту
        """
        if not self.is_indexing():
            logger.debug("Индексация не активна, shutdown не требуется")
            return True
        
        timeout = timeout or self._shutdown_timeout
        logger.info(f"Ожидание завершения индексации (максимум {timeout} сек)...")
        self._should_stop = True
        
        try:
            # Ждём завершения с таймаутом
            await asyncio.wait_for(self._current_task, timeout=timeout)
            logger.info("✅ Индексация успешно завершена перед shutdown")
            return True
            
        except asyncio.TimeoutError:
            # Прерываем по таймауту
            logger.warning(
                f"⚠️ Индексация не завершилась за {timeout} сек. "
                f"Принудительное прерывание. Проиндексировано: "
                f"{self._progress_info.indexed_documents}/"
                f"{self._progress_info.total_documents}"
            )
            
            if self._current_task:
                self._current_task.cancel()
                try:
                    await self._current_task
                except asyncio.CancelledError:
                    pass
            
            return False
    
    async def get_status(self) -> IndexProgressInfo:
        """
        Получить текущий статус индексации.
        
        Returns:
            Информация о прогрессе индексации
        """
        async with self._lock:
            # Возвращаем копию, чтобы избежать race conditions
            return IndexProgressInfo(
                status=self._progress_info.status,
                total_documents=self._progress_info.total_documents,
                indexed_documents=self._progress_info.indexed_documents,
                start_time=self._progress_info.start_time,
                end_time=self._progress_info.end_time,
                error_message=self._progress_info.error_message,
                file_path=self._progress_info.file_path
            )
    
    def is_indexing(self) -> bool:
        """
        Проверить, активна ли индексация в данный момент.
        
        Returns:
            True если индексация выполняется, False иначе
        """
        return (
            self._current_task is not None 
            and not self._current_task.done()
        )


# Singleton instance (будет инициализирован в lifecycle)
_indexing_manager: Optional[BackgroundIndexingManager] = None


def get_indexing_manager() -> BackgroundIndexingManager:
    """
    Получить singleton instance менеджера индексации.
    
    Returns:
        Экземпляр BackgroundIndexingManager
        
    Raises:
        RuntimeError: Если менеджер не инициализирован
    """
    if _indexing_manager is None:
        raise RuntimeError(
            "BackgroundIndexingManager не инициализирован. "
            "Вызовите setup_indexing_manager() в startup."
        )
    return _indexing_manager


def setup_indexing_manager(
    shutdown_timeout: int = 30,
    progress_log_interval: int = 1000
) -> BackgroundIndexingManager:
    """
    Инициализировать singleton instance менеджера индексации.
    
    Args:
        shutdown_timeout: Таймаут для graceful shutdown
        progress_log_interval: Интервал логирования прогресса
        
    Returns:
        Экземпляр BackgroundIndexingManager
    """
    global _indexing_manager
    
    if _indexing_manager is None:
        _indexing_manager = BackgroundIndexingManager(
            shutdown_timeout=shutdown_timeout,
            progress_log_interval=progress_log_interval
        )
        logger.info("BackgroundIndexingManager инициализирован")
    
    return _indexing_manager
