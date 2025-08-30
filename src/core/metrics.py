"""
Модуль метрик и мониторинга производительности.
"""

import time
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from enum import Enum
import psutil
from src.core.logging import get_logger

logger = get_logger(__name__)


class MetricType(Enum):
    """Типы метрик."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class MetricValue:
    """Значение метрики."""
    value: float
    timestamp: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class PerformanceStats:
    """Статистика производительности."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time: float = 0.0
    max_response_time: float = 0.0
    min_response_time: float = float('inf')
    current_active_requests: int = 0


class MetricsCollector:
    """Сборщик метрик."""
    
    def __init__(self, history_size: int = 1000):
        self.history_size = history_size
        self._metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=history_size))
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = defaultdict(float)
        self._timers: Dict[str, List[float]] = defaultdict(list)
        
        # Статистика производительности
        self.performance_stats = PerformanceStats()
        
        # Блокировка для thread safety
        self._lock = asyncio.Lock()
    
    async def increment(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """
        Увеличение счетчика.
        
        Args:
            name: Имя метрики
            value: Значение для увеличения
            labels: Метки
        """
        async with self._lock:
            self._counters[name] += value
            
            metric_value = MetricValue(
                value=self._counters[name],
                timestamp=time.time(),
                labels=labels or {}
            )
            
            self._metrics[name].append(metric_value)
            logger.debug(f"Counter {name} incremented by {value}, total: {self._counters[name]}")
    
    async def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """
        Установка значения gauge метрики.
        
        Args:
            name: Имя метрики
            value: Значение
            labels: Метки
        """
        async with self._lock:
            self._gauges[name] = value
            
            metric_value = MetricValue(
                value=value,
                timestamp=time.time(),
                labels=labels or {}
            )
            
            self._metrics[name].append(metric_value)
            logger.debug(f"Gauge {name} set to {value}")
    
    async def record_timer(self, name: str, duration: float, labels: Optional[Dict[str, str]] = None):
        """
        Запись времени выполнения.
        
        Args:
            name: Имя метрики
            duration: Продолжительность в секундах
            labels: Метки
        """
        async with self._lock:
            self._timers[name].append(duration)
            
            # Оставляем только последние значения
            if len(self._timers[name]) > self.history_size:
                self._timers[name] = self._timers[name][-self.history_size:]
            
            metric_value = MetricValue(
                value=duration,
                timestamp=time.time(),
                labels=labels or {}
            )
            
            self._metrics[name].append(metric_value)
            logger.debug(f"Timer {name} recorded: {duration:.3f}s")
    
    @asynccontextmanager
    async def timer(self, name: str, labels: Optional[Dict[str, str]] = None):
        """
        Контекстный менеджер для измерения времени выполнения.
        
        Args:
            name: Имя метрики
            labels: Метки
        """
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            await self.record_timer(name, duration, labels)
    
    async def get_metric_stats(self, name: str) -> Dict[str, Any]:
        """
        Получение статистики по метрике.
        
        Args:
            name: Имя метрики
            
        Returns:
            Словарь со статистикой
        """
        async with self._lock:
            if name in self._counters:
                return {
                    'type': 'counter',
                    'value': self._counters[name],
                    'history_size': len(self._metrics[name])
                }
            
            if name in self._gauges:
                return {
                    'type': 'gauge',
                    'value': self._gauges[name],
                    'history_size': len(self._metrics[name])
                }
            
            if name in self._timers:
                timers = self._timers[name]
                if timers:
                    return {
                        'type': 'timer',
                        'count': len(timers),
                        'avg': sum(timers) / len(timers),
                        'min': min(timers),
                        'max': max(timers),
                        'last': timers[-1] if timers else 0
                    }
            
            return {'type': 'unknown', 'value': None}
    
    async def get_all_metrics(self) -> Dict[str, Any]:
        """
        Получение всех метрик.
        
        Returns:
            Словарь со всеми метриками
        """
        async with self._lock:
            result = {
                'counters': dict(self._counters),
                'gauges': dict(self._gauges),
                'timers': {}
            }
            
            for name, timers in self._timers.items():
                if timers:
                    result['timers'][name] = {
                        'count': len(timers),
                        'avg': sum(timers) / len(timers),
                        'min': min(timers),
                        'max': max(timers)
                    }
            
            return result
    
    async def update_performance_stats(self, success: bool, response_time: float):
        """
        Обновление статистики производительности.
        
        Args:
            success: Успешный ли запрос
            response_time: Время ответа в секундах
        """
        async with self._lock:
            self.performance_stats.total_requests += 1
            
            if success:
                self.performance_stats.successful_requests += 1
            else:
                self.performance_stats.failed_requests += 1
            
            # Обновляем статистику времени ответа
            if response_time > self.performance_stats.max_response_time:
                self.performance_stats.max_response_time = response_time
            
            if response_time < self.performance_stats.min_response_time:
                self.performance_stats.min_response_time = response_time
            
            # Вычисляем среднее время ответа
            total_time = (self.performance_stats.avg_response_time * 
                         (self.performance_stats.total_requests - 1) + response_time)
            self.performance_stats.avg_response_time = total_time / self.performance_stats.total_requests


class SystemMonitor:
    """Монитор системных ресурсов."""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
    
    async def start_monitoring(self, interval: int = 30):
        """
        Запуск мониторинга системных ресурсов.
        
        Args:
            interval: Интервал сбора метрик в секундах
        """
        if self._monitoring:
            logger.warning("System monitoring already started")
            return
        
        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop(interval))
        logger.info(f"System monitoring started with {interval}s interval")
    
    async def stop_monitoring(self):
        """Остановка мониторинга."""
        self._monitoring = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("System monitoring stopped")
    
    async def _monitor_loop(self, interval: int):
        """Основной цикл мониторинга."""
        while self._monitoring:
            try:
                await self._collect_system_metrics()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(interval)
    
    async def _collect_system_metrics(self):
        """Сбор системных метрик."""
        try:
            # CPU
            cpu_percent = psutil.cpu_percent()
            await self.metrics.set_gauge('system.cpu.usage_percent', cpu_percent)
            
            # Memory
            memory = psutil.virtual_memory()
            await self.metrics.set_gauge('system.memory.usage_percent', memory.percent)
            await self.metrics.set_gauge('system.memory.used_mb', memory.used / 1024 / 1024)
            await self.metrics.set_gauge('system.memory.available_mb', memory.available / 1024 / 1024)
            
            # Disk
            disk = psutil.disk_usage('/')
            await self.metrics.set_gauge('system.disk.usage_percent', 
                                       (disk.used / disk.total) * 100)
            await self.metrics.set_gauge('system.disk.free_gb', disk.free / 1024 / 1024 / 1024)
            
            # Network (if available)
            try:
                network = psutil.net_io_counters()
                await self.metrics.set_gauge('system.network.bytes_sent', network.bytes_sent)
                await self.metrics.set_gauge('system.network.bytes_recv', network.bytes_recv)
            except Exception:
                pass  # Network stats might not be available
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")


# Глобальный экземпляр сборщика метрик
_global_metrics: Optional[MetricsCollector] = None
_global_monitor: Optional[SystemMonitor] = None


def get_metrics_collector() -> MetricsCollector:
    """
    Получение глобального сборщика метрик.
    
    Returns:
        Экземпляр MetricsCollector
    """
    global _global_metrics
    
    if _global_metrics is None:
        _global_metrics = MetricsCollector()
    
    return _global_metrics


def get_system_monitor() -> SystemMonitor:
    """
    Получение глобального монитора системы.
    
    Returns:
        Экземпляр SystemMonitor
    """
    global _global_monitor, _global_metrics
    
    if _global_monitor is None:
        if _global_metrics is None:
            _global_metrics = MetricsCollector()
        _global_monitor = SystemMonitor(_global_metrics)
    
    return _global_monitor


def reset_metrics():
    """Сброс глобальных метрик (для тестов)."""
    global _global_metrics, _global_monitor
    
    if _global_monitor:
        asyncio.create_task(_global_monitor.stop_monitoring())
    
    _global_metrics = None
    _global_monitor = None
