# app/models.py
"""SQLAlchemy ORM models and indexes."""

from __future__ import annotations

from datetime import datetime
from typing import List

from sqlalchemy import (
    String,
    Integer,
    Float,
    DateTime,
    ForeignKey,
    Index,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Sensor(Base):
    """Weather sensor: uniquely named entity that emits metrics over time."""

    __tablename__ = "sensors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)

    # One-to-many
    metrics: Mapped[List["Metric"]] = relationship(
        "Metric",
        back_populates="sensor",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Metric(Base):
    """Single sensor observation (temperature, humidity, etc.)."""

    __tablename__ = "metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sensor_id: Mapped[int] = mapped_column(
        ForeignKey("sensors.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    # Stored as string for portability; schema enforces allowed values.
    metric_type: Mapped[str] = mapped_column(String(32), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
        nullable=False,
    )

    sensor: Mapped["Sensor"] = relationship("Sensor", back_populates="metrics")

    # Helpful composite indexes for query performance
    __table_args__ = (
        Index("ix_metric_sensor_time", "sensor_id", "timestamp"),
        Index("ix_metric_sensor_type_time", "sensor_id", "metric_type", "timestamp"),
    )