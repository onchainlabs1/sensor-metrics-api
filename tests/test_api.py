# tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.database import Base, engine

# Recria o banco de dados antes dos testes
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

client = TestClient(create_app())

def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_create_sensor():
    response = client.post("/sensors", json={"name": "sensor-test"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "sensor-test"
    assert "id" in data

def test_list_sensors():
    response = client.get("/sensors")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1

def test_create_metric():
    # Primeiro, garante que temos um sensor
    sensors = client.get("/sensors").json()
    sensor_id = sensors[0]["id"]

    response = client.post(
        "/metrics/",
        json={"sensor_id": sensor_id, "metric_type": "temperature", "value": 25.5}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["metric_type"] == "temperature"
    assert data["value"] == 25.5
    assert data["sensor_id"] == sensor_id

def test_query_metrics_avg():
    sensors = client.get("/sensors").json()
    sensor_id = sensors[0]["id"]

    response = client.get(
        f"/metrics/query?stat=avg&sensors={sensor_id}&metrics=temperature"
    )
    assert response.status_code == 200
    data = response.json()
    assert "temperature" in data["results"]