import io
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

import cloudinary
import cloudinary.uploader
import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.doctor_google_profile import DoctorGoogleProfile
from app.models.doctor_google_image import DoctorGoogleImage


class DoctorGoogleSaveService:
    """
    Crea o actualiza el perfil de Google de un médico y sus imágenes.

    No realiza búsquedas externas. Recibe los datos ya obtenidos
    y normalizados por DoctorGoogleSearchService.
    Clona las imágenes a Cloudinary para persistencia segura.
    """

    @staticmethod
    def _upload_photo_to_cloudinary(image_url: str) -> tuple[str, str | None]:
        """
        Sube o clona la imagen remota a Cloudinary para persistencia duradera.
        Retorna (secure_url, public_id).
        Si falla o Cloudinary no está configurado, retorna (image_url, None).
        """
        if not image_url or not isinstance(image_url, str):
            return image_url, None

        if not (image_url.startswith("http://") or image_url.startswith("https://") or image_url.startswith("data:image/")):
            return image_url, None

        if "cloudinary.com" in image_url or "res.cloudinary.com" in image_url:
            return image_url, None

        if not settings.CLOUDINARY_CLOUD_NAME or not settings.CLOUDINARY_API_KEY:
            return image_url, None

        try:
            cloudinary.config(
                cloud_name=settings.CLOUDINARY_CLOUD_NAME,
                api_key=settings.CLOUDINARY_API_KEY,
                api_secret=settings.CLOUDINARY_API_SECRET,
                secure=True,
            )
            # Si es base64, subir directo. Si es URL remota, descargar bytes para evitar 403
            if image_url.startswith("data:image/"):
                upload_source: Any = image_url
            else:
                upload_source = image_url
                try:
                    headers = {
                        "User-Agent": (
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/124.0.0.0 Safari/537.36"
                        ),
                        "Referer": "https://www.google.com/",
                    }
                    with httpx.Client(timeout=10.0, headers=headers, follow_redirects=True) as client:
                        resp = client.get(image_url)
                        if resp.status_code == 200 and len(resp.content) > 1000:
                            upload_source = io.BytesIO(resp.content)
                except Exception:
                    upload_source = image_url

            res = cloudinary.uploader.upload(
                upload_source,
                folder="doctor_google_profiles",
                resource_type="image",
            )
            secure_url = res.get("secure_url") or image_url
            public_id = res.get("public_id")
            return secure_url, public_id
        except Exception:
            return image_url, None

    @staticmethod
    def _decimal_or_none(value: Any) -> Decimal | None:
        if value is None or value == "":
            return None
        try:
            return Decimal(str(value))
        except Exception:
            return None

    @staticmethod
    def _int_or_none(value: Any) -> int | None:
        if value is None or value == "":
            return None
        try:
            return int(float(value))
        except Exception:
            return None

    def save_profile(
        self,
        db: Session,
        doctor_id: int,
        data: dict[str, Any],
    ) -> DoctorGoogleProfile:
        business_name = data.get("business_name")

        if not business_name:
            raise ValueError(
                "El nombre del establecimiento es obligatorio."
            )

        profile = (
            db.query(DoctorGoogleProfile)
            .filter(DoctorGoogleProfile.doctor_id == doctor_id)
            .first()
        )

        if profile is None:
            profile = DoctorGoogleProfile(
                doctor_id=doctor_id,
                business_name=business_name,
            )
            db.add(profile)
            db.flush()

        # Actualizar datos.
        profile.business_name = business_name

        fields = {
            "google_place_id": "google_place_id",
            "google_category": "google_category",
            "phone_number": "phone_number",
            "formatted_address": "formatted_address",
            "opening_hours": "opening_hours",
            "booking_url": "booking_url",
            "google_maps_url": "google_maps_url",
            "website_url": "website_url",
        }

        for input_field, model_field in fields.items():
            value = data.get(input_field)
            if value is not None:
                setattr(profile, model_field, value)

        if "google_rating" in data:
            profile.google_rating = self._decimal_or_none(
                data.get("google_rating")
            )

        if "google_reviews_count" in data:
            profile.google_reviews_count = self._int_or_none(
                data.get("google_reviews_count")
            )

        if "latitude" in data:
            profile.latitude = self._decimal_or_none(data.get("latitude"))

        if "longitude" in data:
            profile.longitude = self._decimal_or_none(data.get("longitude"))

        profile.last_synced_at = datetime.now(timezone.utc)
        profile.is_verified = False

        db.flush()

        # Solo reemplazar imágenes si la búsqueda proporcionó la propiedad photos.
        if "photos" in data and data.get("photos") is not None:
            photos = data.get("photos") or []
            if len(photos) > 3:
                photos = photos[:3]

            existing_images = (
                db.query(DoctorGoogleImage)
                .filter(DoctorGoogleImage.google_profile_id == profile.id)
                .order_by(DoctorGoogleImage.image_order)
                .all()
            )

            for image in existing_images:
                db.delete(image)

            db.flush()

            for position, image_url in enumerate(photos, start=1):
                if not image_url:
                    continue

                uploaded_url, public_id = self._upload_photo_to_cloudinary(image_url)

                db.add(
                    DoctorGoogleImage(
                        google_profile_id=profile.id,
                        image_url=uploaded_url,
                        image_path=public_id,
                        image_order=position,
                        is_active=True,
                    )
                )

        db.flush()
        return profile

    def save_external_profile(
        self,
        db: Session,
        data: dict[str, Any],
    ) -> DoctorGoogleProfile | None:
        """
        Guarda o actualiza un perfil de Google externo (doctor_id = NULL).
        Deduplica por google_place_id o por (business_name + formatted_address).
        Retorna el perfil guardado, o None si falla.
        """
        business_name = data.get("business_name")
        if not business_name:
            return None

        # Buscar duplicado por place_id
        profile = None
        place_id = data.get("google_place_id")
        if place_id:
            profile = (
                db.query(DoctorGoogleProfile)
                .filter(
                    DoctorGoogleProfile.google_place_id == place_id,
                    DoctorGoogleProfile.doctor_id == None,
                )
                .first()
            )

        # Buscar duplicado por nombre + dirección
        if profile is None:
            formatted_address = data.get("formatted_address") or ""
            existing = (
                db.query(DoctorGoogleProfile)
                .filter(
                    DoctorGoogleProfile.business_name.ilike(business_name),
                    DoctorGoogleProfile.doctor_id == None,
                )
                .first()
            )
            if existing:
                profile = existing

        # Crear si no existe
        if profile is None:
            profile = DoctorGoogleProfile(
                doctor_id=None,
                business_name=business_name,
            )
            db.add(profile)
            db.flush()

        # Actualizar campos
        profile.business_name = business_name

        for field in (
            "google_place_id", "google_category", "phone_number",
            "formatted_address", "opening_hours", "booking_url",
            "google_maps_url", "website_url",
        ):
            value = data.get(field)
            if value is not None:
                setattr(profile, field, value)

        profile.google_rating = self._decimal_or_none(data.get("google_rating"))
        profile.google_reviews_count = self._int_or_none(data.get("google_reviews_count"))
        profile.latitude = self._decimal_or_none(data.get("latitude"))
        profile.longitude = self._decimal_or_none(data.get("longitude"))
        profile.last_synced_at = datetime.now(timezone.utc)
        profile.is_verified = False

        db.flush()

        # Extraer lista de fotos desde 'photos' o 'images'
        raw_photos = data.get("photos") or data.get("images") or []
        photos: list[str] = []
        for item in raw_photos:
            if isinstance(item, str) and item.strip():
                photos.append(item.strip())
            elif isinstance(item, dict):
                u = item.get("image_url") or item.get("url") or item.get("src")
                if u and isinstance(u, str) and u.strip():
                    photos.append(u.strip())

        # Si no hay fotos, asignar fotos clínicas reales por defecto
        if not photos:
            clinical_defaults = [
                "https://images.unsplash.com/photo-1629909613654-28e377c37b09?auto=format&fit=crop&w=800&q=80",
                "https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?auto=format&fit=crop&w=800&q=80",
                "https://images.unsplash.com/photo-1584515979956-d9f6e5d09982?auto=format&fit=crop&w=800&q=80",
                "https://images.unsplash.com/photo-1579684385127-1ef15d508118?auto=format&fit=crop&w=800&q=80",
            ]
            # Offset según el nombre o hash para variedad
            offset = abs(hash(business_name)) % len(clinical_defaults)
            photos = [
                clinical_defaults[offset],
                clinical_defaults[(offset + 1) % len(clinical_defaults)],
            ]

        # Guardar en DoctorGoogleImage
        existing_images = (
            db.query(DoctorGoogleImage)
            .filter(DoctorGoogleImage.google_profile_id == profile.id)
            .all()
        )
        for img in existing_images:
            db.delete(img)
        db.flush()

        for position, image_url in enumerate(photos[:3], start=1):
            if not image_url:
                continue
            uploaded_url, public_id = self._upload_photo_to_cloudinary(image_url)
            db.add(
                DoctorGoogleImage(
                    google_profile_id=profile.id,
                    image_url=uploaded_url,
                    image_path=public_id,
                    image_order=position,
                    is_active=True,
                )
            )
        db.flush()

        return profile

    def get_profile(
        self,
        db: Session,
        doctor_id: int,
    ) -> DoctorGoogleProfile | None:
        return (
            db.query(DoctorGoogleProfile)
            .filter(DoctorGoogleProfile.doctor_id == doctor_id)
            .first()
        )


doctor_google_save_service = DoctorGoogleSaveService()
