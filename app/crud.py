# app/crud.py
import time
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
from loguru import logger
from app.models import Metric
from app.enums import MetricType

def aggregate_metrics(
    db: Session,
    stat: str,
    sensors: Optional[List[int]],
    metrics: Optional[List[MetricType]],
    start: Optional[datetime],
    end: Optional[datetime],
):
    """Execute aggregated metrics query with performance monitoring."""
    start_time = time.time()
    
    agg_map = {
        "avg": func.avg(Metric.value),
        "min": func.min(Metric.value),
        "max": func.max(Metric.value),
        "sum": func.sum(Metric.value),
    }
    if stat not in agg_map:
        raise ValueError("Unsupported stat")

    agg_func = agg_map[stat]

    q = (
        select(Metric.metric_type, Metric.sensor_id, agg_func.label("val"))
        .group_by(Metric.metric_type, Metric.sensor_id)
    )

    if sensors:
        q = q.where(Metric.sensor_id.in_(sensors))

    if metrics:
        q = q.where(Metric.metric_type.in_(metrics))

    if start:
        q = q.where(Metric.timestamp >= start)
    if end:
        q = q.where(Metric.timestamp <= end)

    try:
        result = db.execute(q).all()
        
        # Log slow queries (>500ms)
        execution_time = (time.time() - start_time) * 1000
        if execution_time > 500:
            logger.warning(f"Slow query detected", extra={
                "execution_time_ms": round(execution_time, 2),
                "stat": stat,
                "sensor_count": len(sensors) if sensors else "all",
                "metric_types": metrics if metrics else "all",
                "date_range": f"{start} to {end}" if start and end else "no_filter",
                "result_count": len(result)
            })
        else:
            logger.debug(f"Query completed", extra={
                "execution_time_ms": round(execution_time, 2),
                "stat": stat,
                "result_count": len(result)
            })
            
        return result
        
    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        logger.error(f"Query failed: {e}", extra={
            "execution_time_ms": round(execution_time, 2),
            "stat": stat,
            "sensors": sensors,
            "metrics": metrics
        })
        raise