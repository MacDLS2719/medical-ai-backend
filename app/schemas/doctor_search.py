# app/schemas/doctor_search.py

from typing import Any, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DoctorSearchRequest(BaseModel):
    """Parámetros para buscar médicos o establecimientos sanitarios."""

    specialty: str | None = Field(
        default=None,
        max_length=150,
        description="Especialidad médica solicitada (única).",
    )
    specialties: List[str] | None = Field(
        default=None,
        description="Lista de especialidades médicas (filtro múltiple). Tiene prioridad sobre 'specialty'.",
    )
    city: str | None = Field(
        default=None,
        max_length=150,
        description="Ciudad donde se realizará la búsqueda.",
    )
    country: str | None = Field(
        default=None,
        max_length=150,
        description="País donde se realizará la búsqueda.",
    )

    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    radius_km: float = Field(default=15, gt=0, le=50)
    limit: int = Field(default=30, ge=1, le=100)
    search_mode: str = Field(
        default="database",
        description="'database' busca solo en BD (rápido). 'external' busca en Google/web con Mivor y guarda en BD.",
    )


class DoctorSearchImageResponse(BaseModel):
    """Imagen asociada a un perfil externo o guardado."""

    image_url: str | None = None
    image_path: str | None = None
    image_order: int | None = None


class DoctorSearchResult(BaseModel):
    """Resultado normalizado para mostrar en el mapa."""

    model_config = ConfigDict(from_attributes=True)

    source: str
    source_place_id: str | None = None

    # Identificadores para médicos de nuestra plataforma
    doctor_id: int | None = None
    user_id: int | None = None
    profile_id: UUID | None = None

    business_name: str
    first_name: str | None = None
    last_name: str | None = None
    google_category: str | None = None
    specialty: str | None = None

    phone_number: str | None = None
    formatted_address: str | None = None
    city: str | None = None
    country: str | None = None

    latitude: float | None = None
    longitude: float | None = None

    website_url: str | None = None
    booking_url: str | None = None
    google_maps_url: str | None = None

    google_rating: float | None = Field(default=None, ge=0, le=5)
    google_reviews_count: int | None = Field(default=None, ge=0)

    opening_hours: dict[str, Any] | None = None
    images: list[DoctorSearchImageResponse] = Field(default_factory=list)
    availabilities: list[dict[str, Any]] = Field(default_factory=list)

    is_our_doctor: bool = False
    is_verified: bool = False
    place_type: str | None = Field(default="doctor", description="'doctor' | 'clinic' | 'hospital'")
    is_clinic: bool = Field(default=False, description="True si es una clínica u hospital, False si es un médico/especialista")


class DoctorSearchResponse(BaseModel):
    """Respuesta general del endpoint."""

    success: bool = True
    total: int = 0
    search_mode: str = "database"
    center_latitude: float | None = None
    center_longitude: float | None = None
    results: list[DoctorSearchResult] = Field(default_factory=list)
    message: str = "Búsqueda completada."
    debug_steps: list[str] = Field(default_factory=list)
