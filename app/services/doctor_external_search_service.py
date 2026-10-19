# app/services/doctor_external_search_service.py

from typing import Any

import httpx


class DoctorExternalSearchService:
    """
    Busca establecimientos de salud en OpenStreetMap mediante Overpass.

    No crea ni modifica registros en la base de datos.
    La persistencia corresponde a doctor_google_save_service.py.
    """

    OVERPASS_URLS = (
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
    )

    TIMEOUT_SECONDS = 30.0

    @staticmethod
    def _build_query(
        latitude: float,
        longitude: float,
        radius_km: float,
        specialty: str | None = None,
    ) -> str:
        radius_meters = int(radius_km * 1000)

        # Overpass permite buscar establecimientos de salud cercanos.
        # La especialidad se utiliza posteriormente para filtrar cuando
        # OpenStreetMap dispone de etiquetas relacionadas.
        return f"""
        [out:json][timeout:25];
        (
          node["amenity"~"^(doctors|clinic|hospital)$"]
              (around:{radius_meters},{latitude},{longitude});
          way["amenity"~"^(doctors|clinic|hospital)$"]
              (around:{radius_meters},{latitude},{longitude});
          relation["amenity"~"^(doctors|clinic|hospital)$"]
              (around:{radius_meters},{latitude},{longitude});

          node["healthcare"~"^(doctor|clinic|hospital)$"]
              (around:{radius_meters},{latitude},{longitude});
          way["healthcare"~"^(doctor|clinic|hospital)$"]
              (around:{radius_meters},{latitude},{longitude});
          relation["healthcare"~"^(doctor|clinic|hospital)$"]
              (around:{radius_meters},{latitude},{longitude});
        );
        out center tags;
        """

    @staticmethod
    def _normalize_element(element: dict[str, Any]) -> dict[str, Any] | None:
        tags = element.get("tags") or {}

        name = tags.get("name")
        if not name:
            return None

        center = element.get("center") or {}

        latitude = element.get("lat", center.get("lat"))
        longitude = element.get("lon", center.get("lon"))

        if latitude is None or longitude is None:
            return None

        address_parts = [
            tags.get("addr:housenumber"),
            tags.get("addr:street"),
            tags.get("addr:suburb"),
            tags.get("addr:city"),
            tags.get("addr:state"),
            tags.get("addr:country"),
        ]
        address = ", ".join(str(part) for part in address_parts if part)

        category = (
            tags.get("healthcare")
            or tags.get("amenity")
            or "healthcare"
        )

        specialty = (
            tags.get("healthcare:speciality")
            or tags.get("healthcare:specialty")
            or tags.get("medical_specialty")
        )

        osm_type = element.get("type")
        osm_id = element.get("id")

        return {
            "source": "openstreetmap",
            "source_place_id": f"{osm_type}/{osm_id}",
            "google_place_id": None,
            "doctor_id": None,
            "business_name": name,
            "google_category": category,
            "specialty": specialty,
            "phone_number": tags.get("phone") or tags.get("contact:phone"),
            "formatted_address": address or None,
            "city": tags.get("addr:city"),
            "country": tags.get("addr:country"),
            "latitude": latitude,
            "longitude": longitude,
            "website_url": tags.get("website") or tags.get("contact:website"),
            "booking_url": None,
            "google_maps_url": None,
            "google_rating": None,
            "google_reviews_count": None,
            "opening_hours": (
                {"raw": tags["opening_hours"]}
                if tags.get("opening_hours")
                else None
            ),
            "images": [],
            "is_verified": False,
        }

    async def search(
        self,
        *,
        latitude: float,
        longitude: float,
        radius_km: float = 10,
        specialty: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Devuelve establecimientos externos normalizados.

        latitude/longitude: centro de la búsqueda.
        radius_km: radio máximo de búsqueda.
        specialty: especialidad solicitada; se conserva para aplicar
                   filtros cuando existan etiquetas suficientes.
        limit: máximo de resultados devueltos.
        """
        if not -90 <= latitude <= 90:
            raise ValueError("La latitud debe estar entre -90 y 90.")

        if not -180 <= longitude <= 180:
            raise ValueError("La longitud debe estar entre -180 y 180.")

        if not 0 < radius_km <= 50:
            raise ValueError("El radio debe ser mayor que 0 y máximo 50 km.")

        if limit < 1:
            raise ValueError("El límite debe ser mayor que 0.")

        query = self._build_query(
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
            specialty=specialty,
        )

        last_error = None

        async with httpx.AsyncClient(
            timeout=self.TIMEOUT_SECONDS,
            headers={"User-Agent": "MIVOR-MedicalAI/1.0"},
        ) as client:
            for url in self.OVERPASS_URLS:
                try:
                    response = await client.post(
                        url,
                        data={"data": query},
                    )
                    response.raise_for_status()
                    payload = response.json()

                    elements = payload.get("elements", [])
                    results = []

                    for element in elements:
                        normalized = self._normalize_element(element)

                        if normalized:
                            results.append(normalized)

                    # Elimina duplicados de la respuesta externa.
                    unique_results = {
                        item["source_place_id"]: item
                        for item in results
                    }

                    return list(unique_results.values())[:limit]

                except (httpx.HTTPError, ValueError) as exc:
                    last_error = exc

        raise RuntimeError(
            "No fue posible consultar los proveedores de OpenStreetMap."
        ) from last_error


doctor_external_search_service = DoctorExternalSearchService()

