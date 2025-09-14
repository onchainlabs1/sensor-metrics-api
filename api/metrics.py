# api/metrics.py
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/metrics", tags=["metrics"])

VALID_STATS = {"min": func.min, "max": func.max, "avg": func.avg, "sum": func.sum}


@router.post("/", response_model=schemas.Metric, status_code=201)
def create_metric(payload: schemas.MetricCreate, db: Session = Depends(get_db)):
    """Ingest a new metric data point."""
    # Ensure sensor exists
    sensor = db.query(models.Sensor).filter(models.Sensor.id == payload.sensor_id).first()
    if not sensor:
        raise HTTPException(status_code=404, detail=f"Sensor {payload.sensor_id} not found")

    # Validate metric_type (Enum)
    try:
        metric_type = models.MetricType(payload.metric_type)
    except ValueError:
        valid = [m.value for m in models.MetricType]
        raise HTTPException(
            status_code=422,
            detail=f"Invalid metric_type '{payload.metric_type}'. Valid: {valid}"
        )

    metric = models.Metric(
        sensor_id=payload.sensor_id,
        metric_type=metric_type,
        value=payload.value,
        timestamp=datetime.utcnow()
    )
    db.add(metric)
    db.commit()
    db.refresh(metric)
    return metric


@router.get("/query")
def query_metrics(
    sensors: Optional[List[int]] = Query(default=None, description="Sensor IDs to include"),
    metrics: Optional[List[str]] = Query(default=None, description="Metric types to include"),
    stat: str = Query(default="avg", pattern="^(min|max|avg|sum)$"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Query aggregated metrics.

    - sensors: one or more sensor IDs (if omitted, all sensors)
    - metrics: one or more metric types from {temperature, humidity, wind_speed}
               (if omitted, all metric types)
    - stat: one of {min, max, avg, sum}
    - date range: between 1 day and 1 month; if not provided, defaults to last 7 days
    """
    now = datetime.utcnow()
    if not start_date and not end_date:
        end_date = now
        start_date = now - timedelta(days=7)
    elif start_date and not end_date:
        end_date = start_date + timedelta(days=1)
    elif end_date and not start_date:
        start_date = end_date - timedelta(days=1)

    if end_date <= start_date:
        raise HTTPException(status_code=422, detail="end_date must be after start_date")
    if (end_date - start_date) < timedelta(days=1):
        raise HTTPException(status_code=422, detail="Range must be at least 1 day")
    if (end_date - start_date) > timedelta(days=31):
        raise HTTPException(status_code=422, detail="Range must be no more than 1 month")

    q = db.query(models.Metric).filter(
        models.Metric.timestamp >= start_date,
        models.Metric.timestamp <= end_date
    )

    if sensors:
        q = q.filter(models.Metric.sensor_id.in_(sensors))

    if metrics:
        try:
            metric_enums = [models.MetricType(m) for m in metrics]
        except ValueError:
            valid = [m.value for m in models.MetricType]
            raise HTTPException(status_code=422, detail=f"Invalid metric in {metrics}. Valid: {valid}")
        q = q.filter(models.Metric.metric_type.in_(metric_enums))
    else:
        metric_enums = list(models.MetricType)

    agg_func = VALID_STATS[stat]
    results: Dict[str, Dict[str, Optional[float]]] = {}

    for m in metric_enums:
        rows = (
            db.query(models.Metric.sensor_id, agg_func(models.Metric.value))
            .filter(
                models.Metric.metric_type == m,
                models.Metric.timestamp >= start_date,
                models.Metric.timestamp <= end_date,
            )
            .group_by(models.Metric.sensor_id)
            .all()
        )
        metric_key = m.value
        results[metric_key] = {str(sensor_id): (val if val is not None else None) for sensor_id, val in rows}

        if sensors:
            for s in sensors:
                results[metric_key].setdefault(str(s), None)

    return {
        "sensors": sensors if sensors else "all",
        "metrics": [m.value for m in metric_enums],
        "stat": stat,
        "start": start_date.isoformat(),
        "end": end_date.isoformat(),
        "results": results,
    }