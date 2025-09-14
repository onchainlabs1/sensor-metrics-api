# app/crud.py
from __future__ import annotations

from datetime import datetime
from typing import Iterable, List, Optional, Sequence, Tuple

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from .models import Metric, Sensor

# -----------------------------------------------------------------------------
# Sensor CRUD
# -----------------------------------------------------------------------------

def create_sensor(db: Session, name: str) -> Sensor:
    """Create a new sensor with a unique name."""
    sensor = Sensor(name=name)
    db.add(sensor)
    db.commit()
    db.refresh(sensor)
    return sensor


def get_sensor_by_id(db: Session, sensor_id: int) -> Optional[Sensor]:
    """Return a sensor by its id."""
    return db.get(Sensor, sensor_id)


def get_sensor_by_name(db: Session, name: str) -> Optional[Sensor]:
    """Return a sensor by its unique name."""
    stmt = select(Sensor).where(Sensor.name == name)
    return db.execute(stmt).scalar_one_or_none()


def list_sensors(db: Session, limit: int = 100, offset: int = 0) -> List[Sensor]:
    """List sensors with basic pagination."""
    stmt = select(Sensor).limit(limit).offset(offset)
    return list(db.execute(stmt).scalars().all())


# -----------------------------------------------------------------------------
# Metric CRUD
# -----------------------------------------------------------------------------

def create_metric(
    db: Session,
    *,
    sensor_id: int,
    metric_type: str,
    value: float,
    timestamp: Optional[datetime] = None,
) -> Metric:
    """Insert a metric value for a sensor.

    If `timestamp` is None, the DB default (server_now) will be used.
    """
    metric = Metric(
        sensor_id=sensor_id,
        metric_type=metric_type,
        value=value,
        timestamp=timestamp,
    )
    db.add(metric)
    db.commit()
    db.refresh(metric)
    return metric


def list_metrics_for_sensor(
    db: Session,
    sensor_id: int,
    *,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    metric_types: Optional[Sequence[str]] = None,
    limit: int = 1000,
    offset: int = 0,
) -> List[Metric]:
    """Return raw metric rows for a given sensor (for debugging/admin use)."""
    stmt = select(Metric).where(Metric.sensor_id == sensor_id)

    if metric_types:
        stmt = stmt.where(Metric.metric_type.in_(metric_types))
    if start:
        stmt = stmt.where(Metric.timestamp >= start)
    if end:
        stmt = stmt.where(Metric.timestamp <= end)

    stmt = stmt.order_by(Metric.timestamp.desc()).limit(limit).offset(offset)
    return list(db.execute(stmt).scalars().all())


# -----------------------------------------------------------------------------
# Aggregation Query
# -----------------------------------------------------------------------------

_VALID_STATS = {
    "avg": func.avg,
    "min": func.min,
    "max": func.max,
    "sum": func.sum,
}


def get_metrics_stats(
    db: Session,
    *,
    sensor_ids: Optional[Sequence[int]] = None,
    metric_types: Optional[Sequence[str]] = None,
    stat: str = "avg",
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> List[dict]:
    """Return aggregated metrics grouped by (sensor_id, metric_type).

    Args:
        sensor_ids: If provided, restricts to these sensors; otherwise includes all.
        metric_types: If provided, restricts to these metric types; otherwise includes all.
        stat: One of {"avg", "min", "max", "sum"}.
        start: Start datetime (inclusive).
        end: End datetime (inclusive).

    Returns:
        A list of dicts: {"sensor_id": int, "metric_type": str, "stat": float}
    """
    stat_key = stat.lower()
    if stat_key not in _VALID_STATS:
        raise ValueError(f"Unsupported statistic '{stat}'. Use one of {list(_VALID_STATS)}")

    agg_func = _VALID_STATS[stat_key]

    # Build base select with aggregation
    stmt = (
        select(
            Metric.sensor_id.label("sensor_id"),
            Metric.metric_type.label("metric_type"),
            agg_func(Metric.value).label("stat"),
        )
    )

    # Dynamic WHERE filters
    conditions = []
    if sensor_ids:
        conditions.append(Metric.sensor_id.in_(sensor_ids))
    if metric_types:
        conditions.append(Metric.metric_type.in_(metric_types))
    if start:
        conditions.append(Metric.timestamp >= start)
    if end:
        conditions.append(Metric.timestamp <= end)

    if conditions:
        stmt = stmt.where(and_(*conditions))

    # Group and order
    stmt = stmt.group_by(Metric.sensor_id, Metric.metric_type).order_by(
        Metric.sensor_id.asc(), Metric.metric_type.asc()
    )

    rows = db.execute(stmt).all()

    # Normalize to plain dicts for easy JSON serialization
    results = [
        {
            "sensor_id": r.sensor_id,
            "metric_type": r.metric_type,
            "stat": float(r.stat) if r.stat is not None else None,
        }
        for r in rows
    ]
    return results