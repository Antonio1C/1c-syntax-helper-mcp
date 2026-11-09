"""Metrics endpoints."""

from fastapi import APIRouter, Depends

from src.core.metrics import get_metrics_collector

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("")
async def get_metrics(
    metrics=Depends(get_metrics_collector)
):
    """Получение метрик системы."""
    all_metrics = await metrics.get_all_metrics()
    performance_stats = metrics.performance_stats
    
    return {
        "metrics": all_metrics,
        "performance": {
            "total_requests": performance_stats.total_requests,
            "successful_requests": performance_stats.successful_requests,
            "failed_requests": performance_stats.failed_requests,
            "success_rate": (performance_stats.successful_requests / max(performance_stats.total_requests, 1)) * 100,
            "avg_response_time": performance_stats.avg_response_time,
            "max_response_time": performance_stats.max_response_time,
            "min_response_time": performance_stats.min_response_time if performance_stats.min_response_time != float('inf') else 0,
            "current_active_requests": performance_stats.current_active_requests
        }
    }
