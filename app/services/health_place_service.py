import asyncio
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models.enums import HealthPlaceKind
from app.models.external_health_places import ExternalHealthPlace
from app.models.health_place_search_zones import HealthPlaceSearchZone
from app.models.patient_location import PatientLocation

# Multiple mirrors with fallback
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
_HEADERS = {"User-Agent": "vitalai-backend/1.0 (facundodanielbenitez@gmail.com)"}

NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"

_AMENITY_TO_KIND = {
    "hospital": HealthPlaceKind.hospital,
    "clinic": HealthPlaceKind.clinic,
    "pharmacy": HealthPlaceKind.pharmacy,
}


async def _fetch_overpass(query: str) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        tasks = {
            asyncio.create_task(client.post(url, data={"data": query}, headers=_HEADERS)): url
            for url in OVERPASS_ENDPOINTS
        }
        last_error: Exception | None = None
        pending = set(tasks)
        try:
            while pending:
                done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
                for task in done:
                    try:
                        resp = task.result()
                        resp.raise_for_status()
                        return resp.json()
                    except Exception as exc:  # noqa: BLE001
                        last_error = exc
            raise last_error
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()


def _address_from_osm_tags(tags: dict) -> str | None:
    street = tags.get("addr:street")
    number = tags.get("addr:housenumber")
    if street and number:
        return f"{street} {number}"
    return street


def _format_nominatim_address(data: dict) -> str | None:
    addr = data.get("address") or {}
    road = addr.get("road") or addr.get("pedestrian") or addr.get("footway")
    number = addr.get("house_number")
    if road and number:
        return f"{road} {number}"
    if road:
        return road
    display_name = data.get("display_name")
    if not display_name:
        return None
    parts = [p.strip() for p in display_name.split(",")]
    return ", ".join(parts[:2])


async def reverse_geocode(client: httpx.AsyncClient, lat: float, lng: float) -> str | None:
    try:
        resp = await client.get(
            NOMINATIM_REVERSE_URL,
            params={"format": "jsonv2", "lat": lat, "lon": lng, "addressdetails": 1, "zoom": 18},
            headers=_HEADERS,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:  # noqa: BLE001
        return None
    return _format_nominatim_address(data)


def _geo_filter(lat: float, lng: float, radius_km: float):
    point = func.ll_to_earth(lat, lng)
    place_point = func.ll_to_earth(ExternalHealthPlace.lat, ExternalHealthPlace.lng)
    radius_m = radius_km * 1000
    return (
        func.earth_box(point, radius_m).op("@>")(place_point),
        func.earth_distance(point, place_point) <= radius_m,
    )


def _ring_filter(lat: float, lng: float, inner_km: float, outer_km: float):
    point = func.ll_to_earth(lat, lng)
    place_point = func.ll_to_earth(ExternalHealthPlace.lat, ExternalHealthPlace.lng)
    outer_m = outer_km * 1000
    distance = func.earth_distance(point, place_point)
    conds = [func.earth_box(point, outer_m).op("@>")(place_point), distance <= outer_m]
    if inner_km > 0:
        conds.append(distance > inner_km * 1000)
    return conds


def get_cached_health_places(
    db: Session, lat: float, lng: float, radius_km: float
) -> list[ExternalHealthPlace]:
    """Fast path: ONLY what's already in the DB, never hits Overpass."""
    cond1, cond2 = _geo_filter(lat, lng, radius_km)
    return list(db.scalars(
        select(ExternalHealthPlace).where(cond1, cond2)
    ).all())


async def refresh_health_places_from_overpass(
    db: Session, lat: float, lng: float, radius_km: float
) -> list[ExternalHealthPlace]:
    """Slow path: ALWAYS hits Overpass, saves new places, returns full set."""
    cached = get_cached_health_places(db, lat, lng, radius_km)
    known_ids = {(p.source, p.external_id) for p in cached}

    amenity_pattern = "|".join(_AMENITY_TO_KIND)
    radius_m = round(radius_km * 1000)
    query = (
        "[out:json][timeout:25];"
        f'(node["amenity"~"^({amenity_pattern})$"](around:{radius_m},{lat},{lng});'
        f'way["amenity"~"^({amenity_pattern})$"](around:{radius_m},{lat},{lng}););'
        "out center 60;"
    )

    try:
        data = await _fetch_overpass(query)
    except Exception:  # noqa: BLE001
        return cached

    new_places: list[ExternalHealthPlace] = []
    for el in data.get("elements", []):
        tags = el.get("tags") or {}
        amenity = tags.get("amenity")
        kind = _AMENITY_TO_KIND.get(amenity)
        if kind is None:
            continue
        el_lat = el.get("lat") or (el.get("center") or {}).get("lat")
        el_lng = el.get("lon") or (el.get("center") or {}).get("lon")
        if el_lat is None or el_lng is None:
            continue
        external_id = f"{el['type']}/{el['id']}"
        if ("osm", external_id) in known_ids:
            continue
        known_ids.add(("osm", external_id))
        new_places.append(ExternalHealthPlace(
            source="osm",
            external_id=external_id,
            name=tags.get("name"),
            kind=kind,
            lat=el_lat,
            lng=el_lng,
            address=_address_from_osm_tags(tags),
        ))

    if new_places:
        db.add_all(new_places)
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise

    return cached + new_places


_PREFETCH_RINGS = ((0, 5), (5, 10), (10, 25), (25, 50))
_MIN_CACHED_PER_RING = 5
_ZONE_GRID_DEGREES = 0.05
_ZONE_RETRY_COOLDOWN = timedelta(days=30)


def _zone_bucket(lat: float, lng: float) -> tuple[float, float]:
    return (
        round(lat / _ZONE_GRID_DEGREES) * _ZONE_GRID_DEGREES,
        round(lng / _ZONE_GRID_DEGREES) * _ZONE_GRID_DEGREES,
    )


def _count_cached_in_ring(db: Session, lat: float, lng: float, inner_km: float, outer_km: float) -> int:
    conds = _ring_filter(lat, lng, inner_km, outer_km)
    return db.scalar(select(func.count()).select_from(ExternalHealthPlace).where(*conds))


def _get_zone_attempt(db: Session, zone_lat: float, zone_lng: float, outer_km: float) -> HealthPlaceSearchZone | None:
    return db.scalar(
        select(HealthPlaceSearchZone).where(
            HealthPlaceSearchZone.zone_lat == zone_lat,
            HealthPlaceSearchZone.zone_lng == zone_lng,
            HealthPlaceSearchZone.ring_outer_km == outer_km,
        )
    )


async def prefetch_health_places(db: Session, lat: float, lng: float) -> None:
    """Background warm-up: fired right after a patient logs in."""
    zone_lat, zone_lng = _zone_bucket(lat, lng)
    for inner_km, outer_km in _PREFETCH_RINGS:
        if _count_cached_in_ring(db, lat, lng, inner_km, outer_km) >= _MIN_CACHED_PER_RING:
            continue

        attempt = _get_zone_attempt(db, zone_lat, zone_lng, outer_km)
        now = datetime.now(timezone.utc)
        if attempt is not None and now - attempt.last_attempted_at < _ZONE_RETRY_COOLDOWN:
            continue

        await refresh_health_places_from_overpass(db, lat, lng, outer_km)

        if attempt is None:
            db.add(HealthPlaceSearchZone(
                zone_lat=zone_lat, zone_lng=zone_lng, ring_outer_km=outer_km, last_attempted_at=now,
            ))
        else:
            attempt.last_attempted_at = now
        try:
            db.commit()
        except Exception:
            db.rollback()


def save_patient_location(db: Session, user_id: int, lat: float, lng: float) -> None:
    """Guarda o actualiza las coordenadas del paciente en patient_locations.
    user_id es un int (la PK de la tabla users)."""
    now = datetime.now(timezone.utc)
    location = db.get(PatientLocation, user_id)
    if location is None:
        db.add(PatientLocation(
            user_id=user_id,
            last_lat=lat,
            last_lng=lng,
            last_location_at=now
        ))
    else:
        location.last_lat = lat
        location.last_lng = lng
        location.last_location_at = now
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
