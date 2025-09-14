# Climate Stats API

A FastAPI service for ingesting sensor metrics (temperature, humidity, wind speed) and querying aggregated statistics across time windows and sensor groups.

## Features

- **Metric Ingestion**: REST endpoints for sensor data collection
- **Aggregated Queries**: Average, min, max, sum statistics with flexible filtering
- **Time-based Filtering**: Query metrics within configurable date ranges
- **Multi-sensor Support**: Aggregate data across single or multiple sensors
- **Production Ready**: Environment-based configuration, health checks, CORS support

## Quick Start

### Prerequisites
- Python 3.11+
- pip/virtualenv

### Setup
```bash
# Clone and setup environment
git clone <repository-url>
cd climate-stats-api
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start development server
uvicorn app.main:create_app --factory --reload --host 0.0.0.0 --port 8000
```

API documentation available at: http://localhost:8000/docs

## Usage Examples

### Create Sensors
```bash
curl -X POST "http://localhost:8000/sensors/" \
  -H "Content-Type: application/json" \
  -d '{"name": "outdoor-sensor-01"}'

curl -X POST "http://localhost:8000/sensors/" \
  -H "Content-Type: application/json" \
  -d '{"name": "indoor-sensor-02"}'
```

### Ingest Metrics
```bash
# Temperature reading
curl -X POST "http://localhost:8000/metrics/" \
  -H "Content-Type: application/json" \
  -d '{"sensor_id": 1, "metric_type": "temperature", "value": 23.5}'

# Humidity reading with custom timestamp
curl -X POST "http://localhost:8000/metrics/" \
  -H "Content-Type: application/json" \
  -d '{"sensor_id": 1, "metric_type": "humidity", "value": 65.0, "timestamp": "2024-01-15T10:30:00Z"}'
```

### Query Aggregated Data
```bash
# Average temperature for sensor 1
curl "http://localhost:8000/metrics/query?stat=avg&sensors=1&metrics=temperature"

# Min/max humidity across all sensors in date range
curl "http://localhost:8000/metrics/query?stat=min&metrics=humidity&start=2024-01-01T00:00:00Z&end=2024-01-31T23:59:59Z"

# Multiple sensors and metrics
curl "http://localhost:8000/metrics/query?stat=avg&sensors=1,2&metrics=temperature&metrics=humidity"
```

## Testing

```bash
# Run test suite
pytest

# Run with coverage
pytest --cov=app --cov=api

# Run specific test file
pytest tests/test_api.py -v
```

## Project Structure

```
├── api/                    # API route handlers
│   ├── metrics.py         # Metric ingestion and querying
│   └── sensors.py         # Sensor CRUD operations
├── app/                   # Core application logic
│   ├── crud.py           # Database operations
│   ├── database.py       # SQLAlchemy configuration
│   ├── main.py           # FastAPI app factory
│   ├── models.py         # SQLAlchemy ORM models
│   └── schemas.py        # Pydantic request/response models
├── tests/                # Test suite
└── requirements.txt      # Python dependencies
```

## Configuration

Environment variables:
- `DATABASE_URL`: Database connection string (default: `sqlite:///./weather.db`)

### PostgreSQL Example
```bash
export DATABASE_URL="postgresql+psycopg2://user:pass@localhost:5432/climate_db"
```

## Production Considerations

### Database Migrations
```bash
# Initialize Alembic
pip install alembic
alembic init migrations

# Generate migration
alembic revision --autogenerate -m "Initial schema"

# Apply migrations
alembic upgrade head
```

### Recommended Enhancements
- **Structured Logging**: Implement JSON logging with correlation IDs
- **Monitoring**: Add Prometheus metrics and health check endpoints
- **Input Validation**: Enforce metric type enums and value ranges
- **Rate Limiting**: Implement request throttling for ingestion endpoints
- **Authentication**: Add API key or JWT-based authentication
- **Data Retention**: Implement automated cleanup for old metrics
- **Caching**: Redis for frequently accessed aggregations

### Docker Deployment
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | API metadata |
| `GET` | `/healthz` | Health check |
| `POST` | `/sensors/` | Create sensor |
| `GET` | `/sensors/` | List all sensors |
| `GET` | `/sensors/{id}` | Get sensor by ID |
| `POST` | `/metrics/` | Ingest metric data |
| `GET` | `/metrics/query` | Query aggregated statistics |

## License

MIT License