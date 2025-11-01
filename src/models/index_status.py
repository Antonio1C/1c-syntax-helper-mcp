"""Модели для отслеживания статуса индексации."""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


class IndexingStatus(str, Enum):
    """Статус процесса индексации."""
    
    IDLE = "idle"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class IndexProgressInfo:
    """Информация о прогрессе индексации."""
    
    status: IndexingStatus = IndexingStatus.IDLE
    total_documents: int = 0
    indexed_documents: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    file_path: Optional[str] = None
    
    @property
    def progress_percent(self) -> float:
        """
        Вычислить процент выполнения.
        
        Returns:
            Процент выполнения (0.0 - 100.0)
        """
        if self.total_documents == 0:
            return 0.0
        return (self.indexed_documents / self.total_documents) * 100.0
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """
        Вычислить длительность индексации в секундах.
        
        Returns:
            Длительность в секундах или None если не начата
        """
        if not self.start_time:
            return None
        
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()
    
    def to_dict(self) -> dict:
        """
        Преобразовать в словарь для API response.
        
        Returns:
            Словарь с информацией о прогрессе
        """
        return {
            "status": self.status.value,
            "progress_percent": round(self.progress_percent, 2),
            "total_documents": self.total_documents,
            "indexed_documents": self.indexed_documents,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "error_message": self.error_message,
            "file_path": self.file_path,
            "duration_seconds": round(self.duration_seconds, 2) if self.duration_seconds else None
        }
