
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)


class DoctorGoogleSearchRequest(BaseModel):
    """Datos enviados por React para buscar un negocio."""

    google_maps_url: HttpUrl

    @field_validator("google_maps_url")
    @classmethod
    def validate_google_maps_url(cls, value: HttpUrl) -> HttpUrl:
        host = (value.host or "").lower().rstrip(".")

        allowed_hosts = {
            "google.com",
            "www.google.com",
            "maps.google.com",
            "maps.app.goo.gl",
            "goo.gl",
        }

        if value.scheme != "https" or not (
            host in allowed_hosts or host.endswith(".google.com")
        ):
            raise ValueError(
                "Debes proporcionar un enlace HTTPS válido de Google Maps."
            )

        return value


class DoctorGoogleImageResponse(BaseModel):
    """Imagen asociada al perfil."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    image_url: str | None = None
    image_path: str | None = None
    image_order: int
    is_active: bool


class DoctorGoogleProfileData(BaseModel):
    """Datos normalizados obtenidos durante la búsqueda."""

    google_place_id: str | None = None
    business_name: str = Field(min_length=1, max_length=255)
    google_category: str | None = None
    google_rating: Decimal | None = Field(default=None, ge=0, le=5)
    google_reviews_count: int | None = Field(default=None, ge=0)
    phone_number: str | None = None
    formatted_address: str | None = None
    latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)
    opening_hours: dict[str, Any] | None = None
    booking_url: str | None = None
    google_maps_url: str | None = None
    website_url: str | None = None
    photos: list[str] = Field(default_factory=list, max_length=3)

    @model_validator(mode="after")
    def sanitize_urls(self):
        """Silently clear URL fields that are not valid http/https URLs."""
        for field_name in ("booking_url", "google_maps_url", "website_url"):
            value = getattr(self, field_name)
            if value is not None and not (value.startswith("https://") or value.startswith("http://")):
                setattr(self, field_name, None)
        return self


class DoctorGoogleSearchResponse(BaseModel):
    """Resultado de búsqueda que React puede mostrar antes de guardar."""

    success: bool = True
    message: str
    profile: DoctorGoogleProfileData


class DoctorGoogleSaveRequest(DoctorGoogleProfileData):
    """Datos confirmados que React envía para guardar."""

    pass


class DoctorGoogleProfileResponse(BaseModel):
    """Perfil persistido en PostgreSQL."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    doctor_id: int
    google_place_id: str | None = None
    business_name: str
    google_category: str | None = None
    google_rating: Decimal | None = None
    google_reviews_count: int | None = None
    phone_number: str | None = None
    formatted_address: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    opening_hours: dict[str, Any] | None = None
    booking_url: str | None = None
    google_maps_url: str | None = None
    website_url: str | None = None
    is_verified: bool
    last_synced_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    images: list[DoctorGoogleImageResponse] = Field(default_factory=list)


class DoctorGoogleMessageResponse(BaseModel):
    success: bool
    message: str
