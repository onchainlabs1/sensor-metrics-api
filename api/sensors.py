# api/sensors.py
"""Sensor endpoints: create, list, retrieve."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from loguru import logger

from app.database import get_db
from app.models import Sensor as SensorModel
from app.schemas import SensorCreate, Sensor as SensorOut

router = APIRouter(prefix="/sensors", tags=["sensors"])


@router.post("/", response_model=SensorOut, status_code=status.HTTP_201_CREATED)
def create_sensor(payload: SensorCreate, db: Session = Depends(get_db)) -> SensorOut:
    """Create a new sensor with a unique name."""
    try:
        existing = db.query(SensorModel).filter(SensorModel.name == payload.name).first()
        if existing:
            logger.warning(f"Sensor creation failed: name '{payload.name}' already exists")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Sensor with name '{payload.name}' already exists.",
            )
        
        sensor = SensorModel(name=payload.name)
        db.add(sensor)
        db.commit()
        db.refresh(sensor)
        
        logger.info(f"Sensor created", extra={
            "sensor_id": sensor.id,
            "sensor_name": payload.name
        })
        
        return sensor  # FastAPI will serialize via Pydantic schema
        
    except HTTPException:
        # Re-raise HTTP exceptions (already logged above)
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating sensor: {e}", extra={
            "sensor_name": payload.name
        })
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/", response_model=list[SensorOut])
def list_sensors(db: Session = Depends(get_db)) -> list[SensorOut]:
    """Return all sensors."""
    return db.query(SensorModel).all()


@router.get("/{sensor_id}", response_model=SensorOut)
def get_sensor(sensor_id: int, db: Session = Depends(get_db)) -> SensorOut:
    """Return a single sensor by id."""
    sensor = db.query(SensorModel).filter(SensorModel.id == sensor_id).first()
    if not sensor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sensor not found")
    return sensor