# app/enums.py
"""Application enums for type safety and validation."""

from enum import Enum


class MetricType(str, Enum):
    """Supported metric types with their valid measurement ranges."""
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    WIND_SPEED = "wind_speed"
