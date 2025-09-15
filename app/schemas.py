# app/schemas.py
from pydantic import BaseModel, field_validator, ValidationError, ConfigDict, Field
from datetime import datetime
from typing import List, Optional, Dict, Union

from app.enums import MetricType


# -------------------------
# Metric Schemas
# -------------------------

class MetricBase(BaseModel):
    metric_type: MetricType
    value: float

    @field_validator('value')
    @classmethod
    def validate_value_range(cls, v: float, info) -> float:
        """Validate metric values are within realistic ranges for their type."""
        if 'metric_type' not in info.data:
            return v
        
        metric_type = info.data['metric_type']
        
        # Define realistic ranges for each metric type
        ranges = {
            MetricType.TEMPERATURE: (-50.0, 60.0, "°C"),
            MetricType.HUMIDITY: (0.0, 100.0, "%"),
            MetricType.WIND_SPEED: (0.0, 200.0, "km/h")
        }
        
        if metric_type in ranges:
            min_val, max_val, unit = ranges[metric_type]
            if not (min_val <= v <= max_val):
                raise ValueError(
                    f"{metric_type.value} must be between {min_val} and {max_val} {unit}, got {v}"
                )
        
        return v


class MetricCreate(MetricBase):
    sensor_id: int
    timestamp: Optional[datetime] = None


class Metric(MetricBase):
    id: int
    sensor_id: int
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


# -------------------------
# Sensor Schemas
# -------------------------

class SensorBase(BaseModel):
    name: str


class SensorCreate(SensorBase):
    pass


class Sensor(SensorBase):
    id: int
    metrics: List[Metric] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


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