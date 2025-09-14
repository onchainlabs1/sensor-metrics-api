# api/metrics.py
"""API routes for metrics ingestion and querying."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.crud import aggregate_metrics

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.post("/", response_model=schemas.Metric, status_code=status.HTTP_201_CREATED)
def create_metric(payload: schemas.MetricCreate, db: Session = Depends(get_db)):
    """
    Ingest a new metric for a given sensor.
    If timestamp is omitted, the current UTC time is used (handled by DB default).
    """
    sensor = db.query(models.Sensor).filter(models.Sensor.id == payload.sensor_id).first()
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")

    metric = models.Metric(
        sensor_id=payload.sensor_id,
        metric_type=payload.metric_type,
        value=payload.value,
        timestamp=payload.timestamp or datetime.utcnow(),
    )
    db.add(metric)
    db.commit()
    db.refresh(metric)
    return metric


@router.get("/query", response_model=schemas.MetricQueryOut)
def query_metrics(
    stat: str = Query(..., description="Aggregation: avg|min|max|sum"),
    sensors: Optional[str] = Query(
        None, description="Comma-separated sensor IDs, e.g. '1,2'"
    ),
    metrics: Optional[List[str]] = Query(
        None, description="List of metric types (temperature, humidity, ...)"
    ),
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    db: Session = Depends(get_db),
):
    """
    Query aggregated statistics over metrics.
    - `sensors`: comma-separated IDs ("1,2") or omitted for all.
    - `metrics`: which metric types to include (temperature, humidity, etc.).
    - `stat`: one of avg|min|max|sum.
    - `start`/`end`: optional datetime filters.
    """
    # Parse sensors string "1,2" -> [1,2]
    sensor_ids = None
    if sensors:
        try:
            sensor_ids = [int(s.strip()) for s in sensors.split(",") if s.strip()]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid sensor list format")

    # Execute aggregation query via CRUD
    rows = aggregate_metrics(
        db, stat=stat, sensors=sensor_ids, metrics=metrics, start=start, end=end
    )

    # Reshape rows into {metric_type: {sensor_id: value}}
    results = {}
    for row in rows:
        metric_type, sensor_id, value = row
        results.setdefault(metric_type, {})[sensor_id] = value

    return {
        "sensors": sensor_ids or "all",
        "metrics": metrics or "all",
        "stat": stat,
        "start": start or (datetime.utcnow()),
        "end": end or (datetime.utcnow()),
        "results": results,
    }