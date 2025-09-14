# app/api/sensors.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models import Sensor
from app.schemas import SensorCreate, Sensor as SensorOut

router = APIRouter(prefix="/sensors", tags=["sensors"])


@router.post("", response_model=SensorOut, status_code=status.HTTP_201_CREATED)
def create_sensor(payload: SensorCreate, db: Session = Depends(get_db)) -> SensorOut:
    """
    Create a new sensor.
    Name is unique; return 409 if already exists.
    """
    sensor = Sensor(name=payload.name)
    db.add(sensor)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Sensor with name '{payload.name}' already exists.",
        )
    db.refresh(sensor)
    return sensor


@router.get("", response_model=list[SensorOut])
def list_sensors(db: Session = Depends(get_db)) -> list[SensorOut]:
    """Return all sensors."""
    return db.query(Sensor).order_by(Sensor.id).all()


@router.get("/{sensor_id}", response_model=SensorOut)
def get_sensor(sensor_id: int, db: Session = Depends(get_db)) -> SensorOut:
    """Return a single sensor by id."""
    sensor = db.query(Sensor).get(sensor_id)
    if not sensor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sensor not found.")
    return sensor