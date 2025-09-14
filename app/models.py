# app/models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, func
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class MetricType(str, enum.Enum):
    temperature = "temperature"
    humidity = "humidity"
    wind_speed = "wind_speed"


class Sensor(Base):
    __tablename__ = "sensors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)

    metrics = relationship("Metric", back_populates="sensor", cascade="all, delete-orphan")


class Metric(Base):
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(Integer, ForeignKey("sensors.id"), index=True, nullable=False)
    metric_type = Column(Enum(MetricType), index=True, nullable=False)
    value = Column(Float, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    sensor = relationship("Sensor", back_populates="metrics")