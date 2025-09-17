# Climate Stats API

[![CI](https://github.com/onchainlabs1/sensor-metrics-api/actions/workflows/ci.yml/badge.svg)](https://github.com/onchainlabs1/sensor-metrics-api/actions/workflows/ci.yml)

A FastAPI service for sensor data collection and analysis. Receives metrics like temperature, humidity, and wind speed from sensors, then provides aggregated statistics.

**Live Demo:** https://sensor-metrics-api.onrender.com/docs

## What it does

- Collect sensor data via REST API
- Store metrics with timestamps
- Query aggregated statistics (avg, min, max, sum)
- Filter by sensor, metric type, and date ranges
- Validate realistic value ranges for each metric type
- Timezone-aware timestamps for global deployment
- Structured JSON logging for production observability


## Architecture Overview

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Client    │    │  FastAPI    │    │  Database   │
│             │    │             │    │             │
│   Requests  ├───→│ Validation  ├───→│  SQLite     │
│   /metrics  │    │ Business    │    │ Aggregation │
│   /sensors  │    │ Logging     │    │ Persistence │
└─────────────┘    └─────────────┘    └─────────────┘
```

**Request Flow:** Client → API Router → Validation → Business Logic → Database  
**Observability:** Structured logging tracks all operations with timing and context
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

**Local:** http://localhost:8000/docs  
**Live Demo:** https://sensor-metrics-api.onrender.com/docs

## Usage Examples

### Create Sensors
```bash
# Create sensors
curl -X POST "https://sensor-metrics-api.onrender.com/sensors/" \
  -H "Content-Type: application/json" \
  -d '{"name": "outdoor-sensor-01"}'

curl -X POST "https://sensor-metrics-api.onrender.com/sensors/" \
  -H "Content-Type: application/json" \
  -d '{"name": "indoor-sensor-02"}'
```

### Ingest Metrics
```bash
# Add temperature reading
curl -X POST "https://sensor-metrics-api.onrender.com/metrics/" \
  -H "Content-Type: application/json" \
  -d '{"sensor_id": 1, "metric_type": "temperature", "value": 23.5}'

# Add humidity reading
curl -X POST "https://sensor-metrics-api.onrender.com/metrics/" \
  -H "Content-Type: application/json" \
  -d '{"sensor_id": 1, "metric_type": "humidity", "value": 65.0}'
```

### Query Aggregated Data
```bash
# Get average temperature for sensor 1 (last 24 hours by default)
curl "https://sensor-metrics-api.onrender.com/metrics/query?stat=avg&sensors=1&metrics=temperature"

# Get min humidity across all sensors in date range
curl "https://sensor-metrics-api.onrender.com/metrics/query?stat=min&metrics=humidity&start=2024-01-01T00:00:00Z&end=2024-01-31T23:59:59Z"

# Multiple sensors and metrics
curl "https://sensor-metrics-api.onrender.com/metrics/query?stat=avg&sensors=1,2&metrics=temperature&metrics=humidity"
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
│   ├── enums.py          # Type-safe metric definitions
│   ├── logging_config.py # Structured logging setup
│   └── schemas.py        # Pydantic request/response models
├── tests/                # Test suite
└── requirements.txt      # Python dependencies
```

## Database

Uses SQLite by default (perfect for development and small deployments). For production, set:

```bash
DATABASE_URL="postgresql://user:pass@host:5432/dbname"
```

## Deployment

**Live on Render:** https://sensor-metrics-api.onrender.com

CI runs on GitHub Actions using the workflow in `.github/workflows/ci.yml` and executes the pytest suite on every push/PR.

For your own deployment:

```bash
# Using Docker
docker build -t climate-api .
docker run -p 8000:8000 climate-api

# Or deploy to Render/Heroku/Railway
# Just connect your GitHub repo and it works
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | API info |
| `GET` | `/healthz` | Health check |
| `POST` | `/sensors/` | Create sensor |
| `GET` | `/sensors/` | List sensors |
| `GET` | `/sensors/{id}` | Get sensor |
| `POST` | `/metrics/` | Add metric |
| `GET` | `/metrics/query` | Query statistics |