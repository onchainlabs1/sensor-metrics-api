# tests/test_api.py
"""Comprehensive test suite with proper isolation and negative testing."""

import pytest
import tempfile
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import create_app
from app.database import Base, get_db


@pytest.fixture
def test_client():
    """Create isolated test client with fresh database for each test."""
    # Create temporary database file for isolation
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    test_database_url = f"sqlite:///{db_path}"
    
    # Create test engine and session
    test_engine = create_engine(
        test_database_url, 
        connect_args={"check_same_thread": False}
    )
    TestingSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
    
    # Create tables
    Base.metadata.create_all(bind=test_engine)
    
    # Override database dependency
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as client:
        yield client
    
    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)


# ================================
# Health Check Tests
# ================================

def test_health_check_returns_ok(test_client):
    """Health endpoint should return 200 with status ok."""
    response = test_client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_endpoint_returns_api_info(test_client):
    """Root endpoint should return API information."""
    response = test_client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Climate Stats API"}


# ================================
# Sensor Management Tests
# ================================

def test_create_sensor_success(test_client):
    """Creating sensor with valid name should return 201."""
    response = test_client.post("/sensors/", json={"name": "outdoor-sensor-01"})
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "outdoor-sensor-01"
    assert data["id"] == 1  # First sensor gets ID 1
    assert data["metrics"] == []


def test_create_sensor_duplicate_name_fails(test_client):
    """Creating sensor with duplicate name should return 409."""
    # Create first sensor
    test_client.post("/sensors/", json={"name": "duplicate-sensor"})
    
    # Attempt to create duplicate
    response = test_client.post("/sensors/", json={"name": "duplicate-sensor"})
    
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_list_sensors_empty_initially(test_client):
    """Listing sensors should return empty array initially."""
    response = test_client.get("/sensors/")
    
    assert response.status_code == 200
    assert response.json() == []


def test_list_sensors_after_creation(test_client):
    """Listing sensors should return created sensors."""
    # Create two sensors
    test_client.post("/sensors/", json={"name": "sensor-1"})
    test_client.post("/sensors/", json={"name": "sensor-2"})
    
    response = test_client.get("/sensors/")
    
    assert response.status_code == 200
    sensors = response.json()
    assert len(sensors) == 2
    assert sensors[0]["name"] == "sensor-1"
    assert sensors[1]["name"] == "sensor-2"


def test_get_sensor_by_id_success(test_client):
    """Getting sensor by valid ID should return sensor data."""
    # Create sensor
    create_response = test_client.post("/sensors/", json={"name": "test-sensor"})
    sensor_id = create_response.json()["id"]
    
    response = test_client.get(f"/sensors/{sensor_id}")
    
    assert response.status_code == 200
    assert response.json()["name"] == "test-sensor"


def test_get_sensor_by_invalid_id_fails(test_client):
    """Getting sensor by non-existent ID should return 404."""
    response = test_client.get("/sensors/999")
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ================================
# Metric Creation Tests
# ================================

def test_create_metric_valid_temperature(test_client):
    """Creating metric with valid temperature should succeed."""
    # Setup: create sensor
    sensor_response = test_client.post("/sensors/", json={"name": "temp-sensor"})
    sensor_id = sensor_response.json()["id"]
    
    response = test_client.post("/metrics/", json={
        "sensor_id": sensor_id,
        "metric_type": "temperature",
        "value": 23.5
    })
    
    assert response.status_code == 201
    data = response.json()
    assert data["metric_type"] == "temperature"
    assert data["value"] == 23.5
    assert data["sensor_id"] == sensor_id
    assert "timestamp" in data


def test_create_metric_valid_humidity(test_client):
    """Creating metric with valid humidity should succeed."""
    # Setup: create sensor
    sensor_response = test_client.post("/sensors/", json={"name": "humidity-sensor"})
    sensor_id = sensor_response.json()["id"]
    
    response = test_client.post("/metrics/", json={
        "sensor_id": sensor_id,
        "metric_type": "humidity",
        "value": 65.0
    })
    
    assert response.status_code == 201
    assert response.json()["metric_type"] == "humidity"
    assert response.json()["value"] == 65.0


def test_create_metric_valid_wind_speed(test_client):
    """Creating metric with valid wind speed should succeed."""
    # Setup: create sensor
    sensor_response = test_client.post("/sensors/", json={"name": "wind-sensor"})
    sensor_id = sensor_response.json()["id"]
    
    response = test_client.post("/metrics/", json={
        "sensor_id": sensor_id,
        "metric_type": "wind_speed",
        "value": 15.2
    })
    
    assert response.status_code == 201
    assert response.json()["metric_type"] == "wind_speed"
    assert response.json()["value"] == 15.2


def test_create_metric_nonexistent_sensor_fails(test_client):
    """Creating metric for non-existent sensor should return 404."""
    response = test_client.post("/metrics/", json={
        "sensor_id": 999,
        "metric_type": "temperature",
        "value": 25.0
    })
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ================================
# Metric Validation - Negative Tests
# ================================

def test_create_metric_invalid_metric_type_fails(test_client):
    """Creating metric with invalid type should return 422."""
    # Setup: create sensor
    sensor_response = test_client.post("/sensors/", json={"name": "test-sensor"})
    sensor_id = sensor_response.json()["id"]
    
    response = test_client.post("/metrics/", json={
        "sensor_id": sensor_id,
        "metric_type": "pressure",  # Not in enum
        "value": 25.0
    })
    
    assert response.status_code == 422


def test_create_metric_temperature_too_high_fails(test_client):
    """Temperature above 60°C should be rejected."""
    # Setup: create sensor
    sensor_response = test_client.post("/sensors/", json={"name": "test-sensor"})
    sensor_id = sensor_response.json()["id"]
    
    response = test_client.post("/metrics/", json={
        "sensor_id": sensor_id,
        "metric_type": "temperature",
        "value": 100.0  # Above 60°C limit
    })
    
    assert response.status_code == 422
    error_detail = str(response.json())
    assert "temperature must be between -50.0 and 60.0" in error_detail


def test_create_metric_temperature_too_low_fails(test_client):
    """Temperature below -50°C should be rejected."""
    # Setup: create sensor
    sensor_response = test_client.post("/sensors/", json={"name": "test-sensor"})
    sensor_id = sensor_response.json()["id"]
    
    response = test_client.post("/metrics/", json={
        "sensor_id": sensor_id,
        "metric_type": "temperature",
        "value": -60.0  # Below -50°C limit
    })
    
    assert response.status_code == 422
    error_detail = str(response.json())
    assert "temperature must be between -50.0 and 60.0" in error_detail


def test_create_metric_humidity_negative_fails(test_client):
    """Negative humidity should be rejected."""
    # Setup: create sensor
    sensor_response = test_client.post("/sensors/", json={"name": "test-sensor"})
    sensor_id = sensor_response.json()["id"]
    
    response = test_client.post("/metrics/", json={
        "sensor_id": sensor_id,
        "metric_type": "humidity",
        "value": -10.0
    })
    
    assert response.status_code == 422
    error_detail = str(response.json())
    assert "humidity must be between 0.0 and 100.0" in error_detail


def test_create_metric_humidity_over_100_fails(test_client):
    """Humidity over 100% should be rejected."""
    # Setup: create sensor
    sensor_response = test_client.post("/sensors/", json={"name": "test-sensor"})
    sensor_id = sensor_response.json()["id"]
    
    response = test_client.post("/metrics/", json={
        "sensor_id": sensor_id,
        "metric_type": "humidity",
        "value": 150.0
    })
    
    assert response.status_code == 422
    error_detail = str(response.json())
    assert "humidity must be between 0.0 and 100.0" in error_detail


def test_create_metric_wind_speed_negative_fails(test_client):
    """Negative wind speed should be rejected."""
    # Setup: create sensor
    sensor_response = test_client.post("/sensors/", json={"name": "test-sensor"})
    sensor_id = sensor_response.json()["id"]
    
    response = test_client.post("/metrics/", json={
        "sensor_id": sensor_id,
        "metric_type": "wind_speed",
        "value": -5.0
    })
    
    assert response.status_code == 422
    error_detail = str(response.json())
    assert "wind_speed must be between 0.0 and 200.0" in error_detail


def test_create_metric_wind_speed_too_high_fails(test_client):
    """Wind speed over 200 km/h should be rejected."""
    # Setup: create sensor
    sensor_response = test_client.post("/sensors/", json={"name": "test-sensor"})
    sensor_id = sensor_response.json()["id"]
    
    response = test_client.post("/metrics/", json={
        "sensor_id": sensor_id,
        "metric_type": "wind_speed",
        "value": 250.0
    })
    
    assert response.status_code == 422
    error_detail = str(response.json())
    assert "wind_speed must be between 0.0 and 200.0" in error_detail


# ================================
# Query Endpoint Tests
# ================================

def test_query_metrics_basic_aggregation(test_client):
    """Basic metric query should return aggregated results."""
    # Setup: create sensor and metrics
    sensor_response = test_client.post("/sensors/", json={"name": "query-sensor"})
    sensor_id = sensor_response.json()["id"]
    
    # Add some test data
    test_client.post("/metrics/", json={
        "sensor_id": sensor_id, "metric_type": "temperature", "value": 20.0
    })
    test_client.post("/metrics/", json={
        "sensor_id": sensor_id, "metric_type": "temperature", "value": 25.0
    })
    
    response = test_client.get(f"/metrics/query?stat=avg&sensors={sensor_id}&metrics=temperature")
    
    assert response.status_code == 200
    data = response.json()
    assert "temperature" in data["results"]
    assert str(sensor_id) in data["results"]["temperature"]  # API returns sensor IDs as strings


def test_query_metrics_all_stats_work(test_client):
    """All stat types (avg, min, max, sum) should work."""
    # Setup: create sensor and metric
    sensor_response = test_client.post("/sensors/", json={"name": "stats-sensor"})
    sensor_id = sensor_response.json()["id"]
    test_client.post("/metrics/", json={
        "sensor_id": sensor_id, "metric_type": "temperature", "value": 25.0
    })
    
    stats = ["avg", "min", "max", "sum"]
    for stat in stats:
        response = test_client.get(f"/metrics/query?stat={stat}&sensors={sensor_id}&metrics=temperature")
        assert response.status_code == 200, f"Stat '{stat}' failed"


# ================================
# Date Range Validation Tests
# ================================

def test_query_date_range_too_short_fails(test_client):
    """Date range less than 1 day should return 400."""
    response = test_client.get(
        "/metrics/query?stat=avg&start=2024-01-01T00:00:00Z&end=2024-01-01T12:00:00Z"
    )
    
    assert response.status_code == 400
    assert "Date range must be at least 1 day" in response.json()["detail"]


def test_query_date_range_too_long_fails(test_client):
    """Date range longer than 31 days should return 400."""
    response = test_client.get(
        "/metrics/query?stat=avg&start=2024-01-01T00:00:00Z&end=2024-02-15T00:00:00Z"
    )
    
    assert response.status_code == 400
    assert "Date range cannot exceed 31 days" in response.json()["detail"]


def test_query_end_before_start_fails(test_client):
    """End date before start date should return 400."""
    response = test_client.get(
        "/metrics/query?stat=avg&start=2024-01-15T00:00:00Z&end=2024-01-10T00:00:00Z"
    )
    
    assert response.status_code == 400
    assert "End date must be after start date" in response.json()["detail"]


def test_query_valid_date_ranges_succeed(test_client):
    """Valid date ranges (1-31 days) should be accepted."""
    # Test 1 day exactly
    response = test_client.get(
        "/metrics/query?stat=avg&start=2024-01-01T00:00:00Z&end=2024-01-02T00:00:00Z"
    )
    assert response.status_code == 200
    
    # Test 31 days exactly
    response = test_client.get(
        "/metrics/query?stat=avg&start=2024-01-01T00:00:00Z&end=2024-02-01T00:00:00Z"
    )
    assert response.status_code == 200
    
    # Test 7 days (typical use case)
    response = test_client.get(
        "/metrics/query?stat=avg&start=2024-01-01T00:00:00Z&end=2024-01-08T00:00:00Z"
    )
    assert response.status_code == 200


def test_query_single_date_parameters_work(test_client):
    """Providing only start OR end date should work within 31-day window."""
    from datetime import datetime, timezone, timedelta
    
    # Only start date - use recent date within 31 days (format: YYYY-MM-DDTHH:MM:SSZ)
    recent_start = (datetime.now(timezone.utc) - timedelta(days=15)).strftime("%Y-%m-%dT%H:%M:%SZ")
    response = test_client.get(f"/metrics/query?stat=avg&start={recent_start}")
    assert response.status_code == 200
    
    # Only end date - use recent date within 31 days
    recent_end = (datetime.now(timezone.utc) + timedelta(days=15)).strftime("%Y-%m-%dT%H:%M:%SZ")
    response = test_client.get(f"/metrics/query?stat=avg&end={recent_end}")
    assert response.status_code == 200


def test_query_single_date_outside_window_fails(test_client):
    """Single date parameters outside 31-day window should fail."""
    # Start date too far in the past
    response = test_client.get("/metrics/query?stat=avg&start=2020-01-01T00:00:00Z")
    assert response.status_code == 400
    assert "more than 31 days in the past" in response.json()["detail"]
    
    # End date too far in the future
    response = test_client.get("/metrics/query?stat=avg&end=2030-01-01T00:00:00Z")
    assert response.status_code == 400
    assert "more than 31 days in the future" in response.json()["detail"]


def test_query_malformed_datetime_fails(test_client):
    """Malformed datetime input should return 422."""
    response = test_client.get(
        "/metrics/query?stat=avg&start=not-a-date&end=2024-01-08T00:00:00Z"
    )
    assert response.status_code == 422


def test_query_invalid_stat_parameter_fails(test_client):
    """Invalid stat parameter should return 422."""
    response = test_client.get("/metrics/query?stat=median")  # Not supported
    assert response.status_code == 422


def test_query_missing_stat_parameter_fails(test_client):
    """Missing required stat parameter should return 422."""
    response = test_client.get("/metrics/query")  # No stat parameter
    assert response.status_code == 422


# ================================
# Integration Tests
# ================================

def test_complete_workflow_temperature_sensor(test_client):
    """Complete workflow: create sensor, add metrics, query aggregations."""
    # Create sensor
    sensor_response = test_client.post("/sensors/", json={"name": "integration-temp-sensor"})
    sensor_id = sensor_response.json()["id"]
    
    # Add temperature readings
    temperatures = [20.0, 22.5, 25.0, 21.5, 23.0]
    for temp in temperatures:
        response = test_client.post("/metrics/", json={
            "sensor_id": sensor_id,
            "metric_type": "temperature", 
            "value": temp
        })
        assert response.status_code == 201
    
    # Query average
    response = test_client.get(f"/metrics/query?stat=avg&sensors={sensor_id}&metrics=temperature")
    assert response.status_code == 200
    
    # Verify result structure
    data = response.json()
    assert data["stat"] == "avg"
    assert data["sensors"] == [sensor_id]
    assert data["metrics"] == ["temperature"]
    assert "temperature" in data["results"]
    assert str(sensor_id) in data["results"]["temperature"]  # API returns sensor IDs as strings


def test_multi_sensor_multi_metric_query(test_client):
    """Test querying multiple sensors and metric types."""
    # Create two sensors
    sensor1_response = test_client.post("/sensors/", json={"name": "outdoor-station"})
    sensor2_response = test_client.post("/sensors/", json={"name": "indoor-station"})
    sensor1_id = sensor1_response.json()["id"]
    sensor2_id = sensor2_response.json()["id"]
    
    # Add metrics to both sensors
    test_client.post("/metrics/", json={"sensor_id": sensor1_id, "metric_type": "temperature", "value": 15.0})
    test_client.post("/metrics/", json={"sensor_id": sensor1_id, "metric_type": "humidity", "value": 80.0})
    test_client.post("/metrics/", json={"sensor_id": sensor2_id, "metric_type": "temperature", "value": 22.0})
    test_client.post("/metrics/", json={"sensor_id": sensor2_id, "metric_type": "humidity", "value": 45.0})
    
    # Query both sensors, both metrics
    response = test_client.get(
        f"/metrics/query?stat=avg&sensors={sensor1_id},{sensor2_id}&metrics=temperature&metrics=humidity"
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "temperature" in data["results"]
    assert "humidity" in data["results"]
    assert str(sensor1_id) in data["results"]["temperature"]  # API returns sensor IDs as strings
    assert str(sensor2_id) in data["results"]["temperature"]