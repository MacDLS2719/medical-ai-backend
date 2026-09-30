from fastapi import APIRouter, Depends, Query, status, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.health_place import HealthPlacePrefetch, HealthPlaceRead
from app.services.health_place_service import (
    get_cached_health_places,
    prefetch_health_places,
    refresh_health_places_from_overpass,
    save_patient_location,
)

router = APIRouter(prefix="/api", tags=["health-places"])


@router.get("/health-places", response_model=list[HealthPlaceRead])
async def list_cached_health_places(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(..., gt=0, le=50),
    db: Session = Depends(get_db),
):
    """Fast path: only what's already cached in the DB, never waits on Overpass."""
    return get_cached_health_places(db, lat, lng, radius_km)


@router.get("/health-places/refresh", response_model=list[HealthPlaceRead])
async def refresh_health_places(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(..., gt=0, le=50),
    db: Session = Depends(get_db),
):
    """Slow path: hits Overpass, persists new results, and returns the full set."""
    return await refresh_health_places_from_overpass(db, lat, lng, radius_km)


@router.post("/health-places/prefetch", status_code=status.HTTP_204_NO_CONTENT)
async def prefetch_health_places_route(
    payload: HealthPlacePrefetch,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Guarda la ubicación del paciente y lanza el prefetch en segundo plano."""
    # Save location immediately (sync, fast)
    save_patient_location(db, payload.user_id, payload.lat, payload.lng)
    # Run Overpass prefetch in background (async, slow)
    background_tasks.add_task(prefetch_health_places, db, payload.lat, payload.lng)
