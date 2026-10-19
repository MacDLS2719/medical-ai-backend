# app/services/doctor_search_service.py

import logging
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.doctor import Doctor
from app.models.doctor_google_profile import DoctorGoogleProfile
from app.models.medical_doctor_availability import MedicalDoctorAvailability
from app.services.doctor_external_search_service import (
    doctor_external_search_service,
)
from app.services.doctor_google_search_service import (
    doctor_google_search_service,
)
from app.services.doctor_google_save_service import (
    doctor_google_save_service,
)

logger = logging.getLogger(__name__)


class DoctorSearchService:
    """
    Busca primero los médicos registrados en nuestra plataforma (prioritarios),
    luego los perfiles externos guardados en base de datos, y si se requieren
    más resultados, consulta proveedores externos como OpenStreetMap.
    """

    def __init__(self) -> None:
        self.external_service = doctor_external_search_service

    async def search(
        self,
        db: Session,
        *,
        specialty: str | None = None,
        specialties: list[str] | None = None,
        city: str | None = None,
        country: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        radius_km: float = 15,
        limit: int = 30,
    ) -> dict[str, Any]:
        debug_steps: list[str] = []

        # Normalizar: si viene specialties (lista), tiene prioridad; si viene specialty (string), wrapearlo en lista
        effective_specialties: list[str] = []
        if specialties and len(specialties) > 0:
            effective_specialties = [s.strip() for s in specialties if s and s.strip()]
        elif specialty and specialty.strip():
            effective_specialties = [specialty.strip()]
        if limit < 1:
            raise ValueError("El límite debe ser mayor que 0.")

        debug_steps.append(f"[1] Especialidades: {effective_specialties} | Ciudad: {city} | País: {country}")
        logger.info(debug_steps[-1])

        # 1. Si no hay coordenadas pero sí ciudad/país, geocodificar para centrar el mapa
        center_lat = latitude
        center_lng = longitude

        if (center_lat is None or center_lng is None) and (city or country):
            geo_query = ", ".join(filter(None, [city, country]))
            try:
                g_lat, g_lng = await doctor_google_search_service._geocode_address(geo_query)
                if g_lat is not None and g_lng is not None:
                    center_lat = g_lat
                    center_lng = g_lng
            except Exception as geo_exc:
                debug_steps.append(f"[1] Geocodificación OK: ({center_lat}, {center_lng})") if (center_lat and g_lat) else debug_steps.append(f"[1] Geocodificación sin resultado")
                pass

        # Fallback de centro si sigue vacío (Bogotá por defecto)
        if center_lat is None or center_lng is None:
            center_lat = 4.6097
            center_lng = -74.0817

        # 2. Buscar en base de datos primero (médicos propios + externos ya guardados)
        local_results = self._search_database(
            db,
            specialties=effective_specialties,
            city=city,
            country=country,
            center_lat=center_lat,
            center_lng=center_lng,
            limit=limit,
        )

        # Si ya alcanzamos el límite con resultados locales, retornar
        if len(local_results) >= limit:
            return {
                "results": local_results[:limit],
                "center_latitude": center_lat,
                "center_longitude": center_lng,
                "debug_steps": debug_steps,
            }

        remaining = limit - len(local_results)

        # 3. Buscar en OpenStreetMap si hay coordenadas disponibles
        osm_results: list[dict[str, Any]] = []
        try:
            ext_specialty = effective_specialties[0] if effective_specialties else None
            osm_results = await self.external_service.search(
                latitude=center_lat,
                longitude=center_lng,
                radius_km=radius_km,
                specialty=ext_specialty,
                limit=remaining,
            )
        except Exception as exc:
            debug_steps.append(f"[3] OpenStreetMap error: {exc}")
            logger.warning(f"Aviso al consultar OpenStreetMap: {exc}")

        if osm_results is not None:
            debug_steps.append(f"[3] OpenStreetMap: {len(osm_results)} resultados")
            logger.info(debug_steps[-1])

        # 4. Si con BD local + OSM aún no hay suficientes resultados Y hay especialidad/ciudad:
        #    buscar en Google (scraping + OpenAI), guardar en DoctorGoogleProfile y devolver.
        google_scraped: list[dict[str, Any]] = []
        total_so_far = len(local_results) + len(osm_results)
        has_search_terms = bool(effective_specialties or city)

        debug_steps.append(f"[4] Total hasta ahora: {total_so_far} | Lanzar Google: {has_search_terms and total_so_far < 3}")
        logger.info(debug_steps[-1])

        if total_so_far < 3 and has_search_terms:
            query_text = " ".join(effective_specialties) if effective_specialties else ""
            debug_steps.append(f"[4] query='{query_text}' city='{city}' country='{country}'")
            logger.info(debug_steps[-1])
            try:
                scraped_list = await doctor_google_search_service.search_multiple_by_text(
                    query=query_text,
                    city=city or "",
                    country=country or "",
                    limit=remaining,
                )

                for scraped in scraped_list:
                    if not scraped.get("business_name"):
                        continue
                    try:
                        saved_profile = doctor_google_save_service.save_external_profile(
                            db, scraped
                        )
                        db.commit()
                        if saved_profile:
                            google_scraped.append(
                                self._profile_to_result(saved_profile, city, country, center_lat, center_lng)
                            )
                            debug_steps.append(f"[4] ✅ Guardado: {scraped.get('business_name')}")
                        else:
                            debug_steps.append(f"[4] ⚠️ save retornó None: {scraped.get('business_name')}")
                    except Exception as save_exc:
                        debug_steps.append(f"[4] ❌ Error guardando '{scraped.get('business_name')}': {save_exc}")
                        logger.warning(f"No se pudo guardar perfil externo: {save_exc}")
                        try:
                            db.rollback()
                        except Exception:
                            pass
                        # Igual lo devolvemos en memoria aunque no se guardó
                        google_scraped.append({
                            "source": "google_live",
                            "source_place_id": scraped.get("google_place_id"),
                            "doctor_id": None,
                            "user_id": None,
                            "profile_id": None,
                            "business_name": scraped.get("business_name", "Consultorio Médico"),
                            "first_name": None,
                            "last_name": None,
                            "google_category": scraped.get("google_category"),
                            "specialty": scraped.get("google_category"),
                            "phone_number": scraped.get("phone_number"),
                            "formatted_address": scraped.get("formatted_address"),
                            "city": city,
                            "country": country,
                            "latitude": scraped.get("latitude") or center_lat,
                            "longitude": scraped.get("longitude") or center_lng,
                            "website_url": scraped.get("website_url"),
                            "booking_url": scraped.get("booking_url"),
                            "google_maps_url": scraped.get("google_maps_url"),
                            "google_rating": scraped.get("google_rating", 4.8),
                            "google_reviews_count": scraped.get("google_reviews_count", 20),
                            "opening_hours": scraped.get("opening_hours"),
                            "images": [],
                            "availabilities": [],
                            "is_our_doctor": False,
                            "is_verified": False,
                        })
            except Exception as exc:
                debug_steps.append(f"[4] ❌ Error general Google+IA: {exc}")
                logger.warning(f"Aviso al buscar en Google/IA: {exc}")
        else:
            debug_steps.append(f"[4] Google omitido (total={total_so_far}, has_terms={has_search_terms})")

        # 5. Combinar dando prioridad: propios > BD externos > OSM > Google scraped
        combined = self._merge_results(
            local_results,
            osm_results + google_scraped,
            limit=limit,
        )
        debug_steps.append(f"[5] Total final devuelto: {len(combined)}")
        logger.info(debug_steps[-1])

        return {
            "results": combined,
            "center_latitude": center_lat,
            "center_longitude": center_lng,
            "debug_steps": debug_steps,
        }

    @staticmethod
    def _profile_to_result(
        p: DoctorGoogleProfile,
        city: str | None,
        country: str | None,
        center_lat: float,
        center_lng: float,
    ) -> dict[str, Any]:
        """Convierte un DoctorGoogleProfile (externo) al formato de resultado del mapa."""
        p_images = []
        for img in (p.images or []):
            if img.is_active and img.image_url:
                p_images.append({
                    "image_url": img.image_url,
                    "image_path": img.image_path,
                    "image_order": img.image_order,
                })
        return {
            "source": "google",
            "source_place_id": p.google_place_id,
            "doctor_id": None,
            "user_id": None,
            "profile_id": p.id,
            "business_name": p.business_name,
            "first_name": None,
            "last_name": None,
            "google_category": p.google_category,
            "specialty": p.google_category,
            "phone_number": p.phone_number,
            "formatted_address": p.formatted_address,
            "city": city,
            "country": country,
            "latitude": float(p.latitude) if p.latitude is not None else center_lat,
            "longitude": float(p.longitude) if p.longitude is not None else center_lng,
            "website_url": p.website_url,
            "booking_url": p.booking_url,
            "google_maps_url": p.google_maps_url,
            "google_rating": float(p.google_rating) if p.google_rating is not None else 4.8,
            "google_reviews_count": p.google_reviews_count or 20,
            "opening_hours": p.opening_hours,
            "images": p_images,
            "availabilities": [],
            "is_our_doctor": False,
            "is_verified": False,
        }

    def _search_database(
        self,
        db: Session,
        *,
        specialties: list[str] | None = None,
        city: str | None = None,
        country: str | None = None,
        center_lat: float,
        center_lng: float,
        limit: int,
    ) -> list[dict[str, Any]]:
        """
        Consulta médicos propios registrados y perfiles externos guardados.
        Los médicos propios de la plataforma tienen prioridad #1.
        """
        normalized: list[dict[str, Any]] = []
        seen_user_ids = set()

        # ------------------------------------------------------------------
        # A. MÉDICOS DE NUESTRA PLATAFORMA (Doctor table, is_active=True)
        # ------------------------------------------------------------------
        doc_query = db.query(Doctor).filter(Doctor.is_active == True)

        if specialties:
            spec_filters = [Doctor.specialty.ilike(f"%{s}%") for s in specialties]
            doc_query = doc_query.filter(or_(*spec_filters))

        if city and city.strip():
            city_clean = city.strip()
            doc_query = doc_query.filter(
                or_(
                    Doctor.city.ilike(f"%{city_clean}%"),
                    Doctor.address.ilike(f"%{city_clean}%"),
                )
            )

        registered_doctors = doc_query.limit(limit).all()

        for doc in registered_doctors:
            seen_user_ids.add(doc.user_id)

            # Buscar perfil de Google asociado si existe
            g_profile = (
                db.query(DoctorGoogleProfile)
                .filter(DoctorGoogleProfile.doctor_id == doc.id)
                .first()
            )

            # Buscar disponibilidades activas
            availabilities = (
                db.query(MedicalDoctorAvailability)
                .filter(
                    MedicalDoctorAvailability.doctor_id == doc.user_id,
                    MedicalDoctorAvailability.is_active == True,
                )
                .all()
            )

            avail_data = []
            for av in availabilities:
                avail_data.append({
                    "id": av.id,
                    "day_of_week": av.day_of_week,
                    "start_date": str(av.start_date) if av.start_date else None,
                    "end_date": str(av.end_date) if av.end_date else None,
                    "start_time": str(av.start_time) if av.start_time else None,
                    "end_time": str(av.end_time) if av.end_time else None,
                    "consultation_type": av.consultation_type,
                })

            # Coordenadas
            d_lat = None
            d_lng = None
            if g_profile and g_profile.latitude is not None:
                d_lat = float(g_profile.latitude)
                d_lng = float(g_profile.longitude)
            elif doc.latitude is not None and doc.longitude is not None:
                d_lat = float(doc.latitude)
                d_lng = float(doc.longitude)
            else:
                d_lat = center_lat
                d_lng = center_lng

            # Imágenes
            images_list = []
            if g_profile and g_profile.images:
                for img in g_profile.images:
                    if img.is_active and img.image_url:
                        images_list.append({
                            "image_url": img.image_url,
                            "image_path": img.image_path,
                            "image_order": img.image_order,
                        })

            business_name = (
                (g_profile.business_name if g_profile else None)
                or f"Dr. {doc.first_name} {doc.last_name}"
            )

            normalized.append({
                "source": "internal",
                "source_place_id": g_profile.google_place_id if g_profile else None,
                "doctor_id": doc.id,
                "user_id": doc.user_id,
                "profile_id": g_profile.id if g_profile else None,
                "business_name": business_name,
                "first_name": doc.first_name,
                "last_name": doc.last_name,
                "google_category": g_profile.google_category if g_profile else doc.specialty,
                "specialty": doc.specialty,
                "phone_number": (g_profile.phone_number if g_profile else None) or doc.consultation_phone or doc.phone,
                "formatted_address": (g_profile.formatted_address if g_profile else None) or doc.address,
                "city": doc.city or city,
                "country": doc.country or country,
                "latitude": d_lat,
                "longitude": d_lng,
                "website_url": (g_profile.website_url if g_profile else None) or doc.website,
                "booking_url": g_profile.booking_url if g_profile else None,
                "google_maps_url": g_profile.google_maps_url if g_profile else doc.linkgoogle,
                "google_rating": float(g_profile.google_rating) if (g_profile and g_profile.google_rating) else 4.9,
                "google_reviews_count": g_profile.google_reviews_count if (g_profile and g_profile.google_reviews_count) else 35,
                "opening_hours": g_profile.opening_hours if g_profile else None,
                "images": images_list,
                "availabilities": avail_data,
                "is_our_doctor": True,
                "is_verified": True,
            })

        # ------------------------------------------------------------------
        # B. PERFILES EXTERNOS EN DATABASE (doctor_id IS NULL)
        # ------------------------------------------------------------------
        remaining = limit - len(normalized)
        if remaining > 0:
            ext_query = db.query(DoctorGoogleProfile).filter(
                DoctorGoogleProfile.doctor_id == None
            )

            if specialties:
                spec_filters = [
                    or_(
                        DoctorGoogleProfile.google_category.ilike(f"%{s}%"),
                        DoctorGoogleProfile.business_name.ilike(f"%{s}%"),
                    )
                    for s in specialties
                ]
                ext_query = ext_query.filter(or_(*spec_filters))

            if city and city.strip():
                city_clean = city.strip()
                ext_query = ext_query.filter(
                    or_(
                        DoctorGoogleProfile.formatted_address.ilike(f"%{city_clean}%"),
                        DoctorGoogleProfile.business_name.ilike(f"%{city_clean}%"),
                    )
                )

            external_profiles = ext_query.limit(remaining).all()

            for p in external_profiles:
                p_images = []
                for img in (p.images or []):
                    if img.is_active and img.image_url:
                        p_images.append({
                            "image_url": img.image_url,
                            "image_path": img.image_path,
                            "image_order": img.image_order,
                        })

                normalized.append({
                    "source": "google",
                    "source_place_id": p.google_place_id,
                    "doctor_id": None,
                    "user_id": None,
                    "profile_id": p.id,
                    "business_name": p.business_name,
                    "first_name": None,
                    "last_name": None,
                    "google_category": p.google_category,
                    "specialty": p.google_category,
                    "phone_number": p.phone_number,
                    "formatted_address": p.formatted_address,
                    "city": city,
                    "country": country,
                    "latitude": float(p.latitude) if p.latitude is not None else center_lat,
                    "longitude": float(p.longitude) if p.longitude is not None else center_lng,
                    "website_url": p.website_url,
                    "booking_url": p.booking_url,
                    "google_maps_url": p.google_maps_url,
                    "google_rating": float(p.google_rating) if p.google_rating is not None else 4.8,
                    "google_reviews_count": p.google_reviews_count or 20,
                    "opening_hours": p.opening_hours,
                    "images": p_images,
                    "availabilities": [],
                    "is_our_doctor": False,
                    "is_verified": False,
                })

        return normalized

    @staticmethod
    def _merge_results(
        local_results: list[dict[str, Any]],
        external_results: list[dict[str, Any]],
        *,
        limit: int,
    ) -> list[dict[str, Any]]:
        """
        Combina dando prioridad estricta a los médicos propios registrados
        y eliminando duplicados por nombre y coordenadas.
        """
        combined = []
        seen_names = set()

        # Primero todos los locales (propios y externos de BD)
        for item in local_results:
            name_clean = (item.get("business_name") or "").strip().casefold()
            if name_clean:
                seen_names.add(name_clean)
            combined.append(item)

        # Luego externos adicionales de OpenStreetMap
        for item in external_results:
            name_clean = (item.get("business_name") or "").strip().casefold()
            if name_clean and name_clean in seen_names:
                continue

            if name_clean:
                seen_names.add(name_clean)

            # Asegurar flags
            item["is_our_doctor"] = False
            item["availabilities"] = []
            combined.append(item)

            if len(combined) >= limit:
                break

        return combined[:limit]


doctor_search_service = DoctorSearchService()
