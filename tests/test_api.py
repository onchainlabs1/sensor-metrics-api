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

def test_metric_validation_invalid_temperature():
    """Test that invalid temperature values are rejected with 422."""
    sensors = client.get("/sensors").json()
    sensor_id = sensors[0]["id"]
    
    # Test temperature too high
    response = client.post(
        "/metrics/",
        json={"sensor_id": sensor_id, "metric_type": "temperature", "value": 100.0}
    )
    assert response.status_code == 422
    assert "temperature must be between -50.0 and 60.0" in str(response.json())

def test_metric_validation_invalid_humidity():
    """Test that invalid humidity values are rejected with 422."""
    sensors = client.get("/sensors").json()
    sensor_id = sensors[0]["id"]
    
    # Test negative humidity
    response = client.post(
        "/metrics/",
        json={"sensor_id": sensor_id, "metric_type": "humidity", "value": -10.0}
    )
    assert response.status_code == 422
    assert "humidity must be between 0.0 and 100.0" in str(response.json())

def test_metric_validation_invalid_metric_type():
    """Test that invalid metric types are rejected with 422."""
    sensors = client.get("/sensors").json()
    sensor_id = sensors[0]["id"]
    
    # Test invalid metric type
    response = client.post(
        "/metrics/",
        json={"sensor_id": sensor_id, "metric_type": "invalid_type", "value": 25.0}
    )
    assert response.status_code == 422

def test_metric_validation_valid_values():
    """Test that valid metric values are accepted."""
    sensors = client.get("/sensors").json()
    sensor_id = sensors[0]["id"]
    
    # Valid temperature
    response = client.post(
        "/metrics/",
        json={"sensor_id": sensor_id, "metric_type": "temperature", "value": 25.0}
    )
    assert response.status_code == 201
    
    # Valid humidity
    response = client.post(
        "/metrics/",
        json={"sensor_id": sensor_id, "metric_type": "humidity", "value": 65.0}
    )
    assert response.status_code == 201
    
    # Valid wind_speed
    response = client.post(
        "/metrics/",
        json={"sensor_id": sensor_id, "metric_type": "wind_speed", "value": 50.0}
    )
    assert response.status_code == 201

def test_query_date_range_validation_too_short():
    """Test that date ranges less than 1 day are rejected."""
    response = client.get(
        "/metrics/query?stat=avg&start=2024-01-01T00:00:00Z&end=2024-01-01T12:00:00Z"
    )
    assert response.status_code == 400
    assert "Date range must be at least 1 day" in response.json()["detail"]

def test_query_date_range_validation_too_long():
    """Test that date ranges longer than 31 days are rejected."""
    response = client.get(
        "/metrics/query?stat=avg&start=2024-01-01T00:00:00Z&end=2024-02-15T00:00:00Z"
    )
    assert response.status_code == 400
    assert "Date range cannot exceed 31 days" in response.json()["detail"]

def test_query_date_range_validation_end_before_start():
    """Test that end date before start date is rejected."""
    response = client.get(
        "/metrics/query?stat=avg&start=2024-01-15T00:00:00Z&end=2024-01-10T00:00:00Z"
    )
    assert response.status_code == 400
    assert "End date must be after start date" in response.json()["detail"]

def test_query_date_range_validation_valid_range():
    """Test that valid date ranges (1-31 days) are accepted."""
    # 7 day range should work
    response = client.get(
        "/metrics/query?stat=avg&start=2024-01-01T00:00:00Z&end=2024-01-08T00:00:00Z"
    )
    assert response.status_code == 200
    
    # 31 day range should work
    response = client.get(
        "/metrics/query?stat=avg&start=2024-01-01T00:00:00Z&end=2024-02-01T00:00:00Z"
    )
    assert response.status_code == 200

def test_query_malformed_datetime():
    """Test that malformed datetime inputs return 422 validation error."""
    response = client.get(
        "/metrics/query?stat=avg&start=invalid-date&end=2024-01-08T00:00:00Z"
    )
    assert response.status_code == 422  # FastAPI validation error

def test_query_invalid_stat_parameter():
    """Test that invalid stat parameter is rejected."""
    response = client.get(
        "/metrics/query?stat=invalid_stat"
    )
    assert response.status_code == 422  # FastAPI validation error

def test_query_single_date_parameter():
    """Test that providing only start or end date works (no range validation)."""
    # Only start date
    response = client.get(
        "/metrics/query?stat=avg&start=2024-01-01T00:00:00Z"
    )
    assert response.status_code == 200
    
    # Only end date
    response = client.get(
        "/metrics/query?stat=avg&end=2024-01-08T00:00:00Z"
    )
    assert response.status_code == 200