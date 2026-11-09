"""Request performance metrics middleware."""

import time

from fastapi import Request

from src.core.metrics import get_metrics_collector


async def metrics_middleware(request: Request, call_next):
    metrics = get_metrics_collector()
    start_time = time.time()
    response = await call_next(request)
    response_time = time.time() - start_time

    await metrics.record_timer(
        "request.duration",
        response_time,
        {"method": request.method, "path": request.url.path}
    )
    await metrics.update_performance_stats(
        success=200 <= response.status_code < 400,
        response_time=response_time
    )

    return response