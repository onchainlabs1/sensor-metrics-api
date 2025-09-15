"""API routers package marker.

Routers live in sibling modules (e.g., `api.sensors`, `api.metrics`).
Import them explicitly in `app.main` to avoid circular imports:
    from api import sensors as sensors_router
"""
__all__: list[str] = []