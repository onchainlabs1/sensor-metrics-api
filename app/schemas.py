# app/schemas.py
from datetime import datetime
from enum import Enum as PyEnum
from typing import List
from pydantic import BaseModel, ConfigDict, Field


class MetricType(str, PyEnum):
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    WIND_SPEED = "wind_speed"
    PRESSURE = "pressure"  # optional, remove if not needed


# Shared properties
class MetricBase(BaseModel):
    metric_type: MetricType
    value: float


# Schema for creating a new metric
class MetricCreate(MetricBase):
    sensor_id: int


# Schema for returning metric data
class Metric(MetricBase):
    id: int
    sensor_id: int
    timestamp: datetime

    # Pydantic v2: replaces orm_mode=True
    model_config = ConfigDict(from_attributes=True)


# Sensor schemas
class SensorBase(BaseModel):
    name: str


class SensorCreate(SensorBase):
    pass


class Sensor(SensorBase):
    id: int
    metrics: List[Metric] = Field(default_factory=list)

    # Pydantic v2: replaces orm_mode=True
    model_config = ConfigDict(from_attributes=True)