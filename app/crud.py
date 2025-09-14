# app/crud.py
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
from app.models import Metric

def aggregate_metrics(
    db: Session,
    stat: str,
    sensors: Optional[List[int]],
    metrics: Optional[List[str]],
    start: Optional[datetime],
    end: Optional[datetime],
):
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
        q = q.where(Metric.sensor_id.in_(sensors))   # <-- filter applied

    if metrics:
        q = q.where(Metric.metric_type.in_(metrics))

    if start:
        q = q.where(Metric.timestamp >= start)
    if end:
        q = q.where(Metric.timestamp <= end)

    return db.execute(q).all()