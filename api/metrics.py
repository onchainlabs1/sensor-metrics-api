# api/metrics.py
"""API routes for metrics ingestion and querying."""

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from loguru import logger

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
    try:
        sensor = db.query(models.Sensor).filter(models.Sensor.id == payload.sensor_id).first()
        if not sensor:
            logger.warning(f"Metric creation failed: sensor {payload.sensor_id} not found")
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
        
        logger.info(f"Metric created", extra={
            "sensor_id": payload.sensor_id,
            "metric_type": payload.metric_type.value,
            "value": payload.value,
            "metric_id": metric.id
        })
        
        return metric
        
    except HTTPException:
        # Re-raise HTTP exceptions (already logged above)
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating metric: {e}", extra={
            "sensor_id": payload.sensor_id,
            "metric_type": payload.metric_type.value if hasattr(payload.metric_type, 'value') else str(payload.metric_type),
            "value": payload.value
        })
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")


def _validate_date_range(start: Optional[datetime], end: Optional[datetime]) -> None:
    """Validate that date range is between 1 day and 31 days."""
    if start and end:
        if end <= start:
            raise HTTPException(
                status_code=400,
                detail="End date must be after start date"
            )
        
        date_diff = end - start
        if date_diff < timedelta(days=1):
            raise HTTPException(
                status_code=400,
                detail="Date range must be at least 1 day"
            )
        
        if date_diff > timedelta(days=31):
            raise HTTPException(
                status_code=400,
                detail="Date range cannot exceed 31 days"
            )


@router.get("/query", response_model=schemas.MetricQueryOut)
def query_metrics(
    stat: str = Query(..., pattern="^(avg|min|max|sum)$", description="Aggregation: avg|min|max|sum"),
    sensors: Optional[str] = Query(
        None, description="Comma-separated sensor IDs, e.g. '1,2'"
    ),
    metrics: Optional[List[str]] = Query(
        None, description="List of metric types (temperature, humidity, wind_speed)"
    ),
    start: Optional[datetime] = Query(None, description="Start datetime (ISO format)"),
    end: Optional[datetime] = Query(None, description="End datetime (ISO format)"),
    db: Session = Depends(get_db),
):
    """
    Query aggregated statistics over metrics with date range validation.
    
    - `sensors`: comma-separated IDs ("1,2") or omitted for all
    - `metrics`: metric types to include (temperature, humidity, wind_speed)
    - `stat`: aggregation function (avg, min, max, sum)
    - `start`/`end`: datetime range (must be 1-31 days if both provided)
    
    Date range constraints:
    - If both start and end are provided, range must be 1-31 days
    - End date must be after start date
    - Malformed datetime inputs return 422 validation errors
    """
    # Validate date range constraints
    _validate_date_range(start, end)
    
    # Parse sensors string "1,2" -> [1,2]
    sensor_ids = None
    if sensors:
        try:
            sensor_ids = [int(s.strip()) for s in sensors.split(",") if s.strip()]
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail="Invalid sensor list format. Use comma-separated integers like '1,2,3'"
            )

    # Execute aggregation query via CRUD
    rows = aggregate_metrics(
        db, stat=stat, sensors=sensor_ids, metrics=metrics, start=start, end=end
    )

    # Reshape rows into {metric_type: {sensor_id: value}}
    results = {}
    found_metrics = set()
    for row in rows:
        metric_type, sensor_id, value = row
        results.setdefault(metric_type, {})[sensor_id] = value
        found_metrics.add(metric_type)

    return {
        "sensors": sensor_ids if sensor_ids is not None else "all",
        "metrics": metrics if metrics is not None else list(found_metrics),
        "stat": stat,
        "start": start or datetime.utcnow(),
        "end": end or datetime.utcnow(),
        "results": results,
    }