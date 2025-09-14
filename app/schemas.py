# app/schemas.py
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional, Dict, Union


# -------------------------
# Metric Schemas
# -------------------------

class MetricBase(BaseModel):
    metric_type: str
    value: float


class MetricCreate(MetricBase):
    sensor_id: int
    timestamp: Optional[datetime] = None


class Metric(MetricBase):
    id: int
    sensor_id: int
    timestamp: datetime

    class Config:
        from_attributes = True  # Pydantic v2 replacement for orm_mode


# -------------------------
# Sensor Schemas
# -------------------------

class SensorBase(BaseModel):
    name: str


class SensorCreate(SensorBase):
    pass


class Sensor(SensorBase):
    id: int
    metrics: List[Metric] = []

    class Config:
        from_attributes = True


# -------------------------
# Metric Query Schemas
# -------------------------

class MetricQueryOut(BaseModel):
    sensors: Union[List[int], str]
    metrics: List[str]
    stat: str
    start: datetime
    end: datetime
    results: Dict[str, Dict[Union[int, str], Optional[float]]]