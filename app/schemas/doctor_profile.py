from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict


# ==========================================================
# DOCTOR EDUCATION
# ==========================================================


class DoctorEducationBase(BaseModel):
    institution: str = Field(
        ...,
        min_length=1,
        max_length=255
    )

    degree: str = Field(
        ...,
        min_length=1,
        max_length=150
    )

    field_of_study: Optional[str] = Field(
        default=None,
        max_length=150
    )

    education_type: Optional[str] = Field(
        default=None,
        max_length=50
    )

    start_year: Optional[int] = Field(
        default=None,
        ge=1900,
        le=2100
    )

    end_year: Optional[int] = Field(
        default=None,
        ge=1900,
        le=2100
    )

    description: Optional[str] = None


class DoctorEducationCreate(DoctorEducationBase):
    pass


class DoctorEducationUpdate(BaseModel):
    institution: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=255
    )

    degree: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=150
    )

    field_of_study: Optional[str] = Field(
        default=None,
        max_length=150
    )

    education_type: Optional[str] = Field(
        default=None,
        max_length=50
    )

    start_year: Optional[int] = Field(
        default=None,
        ge=1900,
        le=2100
    )

    end_year: Optional[int] = Field(
        default=None,
        ge=1900,
        le=2100
    )

    description: Optional[str] = None


class DoctorEducationResponse(DoctorEducationBase):
    id: int
    doctor_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )


# ==========================================================
# DOCTOR MEDIA
# ==========================================================


class DoctorMediaResponse(BaseModel):
    id: int
    doctor_id: int

    media_type: str

    file_url: str

    file_name: Optional[str] = None

    mime_type: Optional[str] = None

    is_active: bool

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )


# ==========================================================
# DOCTOR PROFILE UPDATE
# ==========================================================


class DoctorProfileUpdate(BaseModel):

    # ------------------------------------------------------
    # DATOS PERSONALES
    # ------------------------------------------------------

    first_name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100
    )

    last_name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100
    )

    date_of_birth: Optional[date] = None

    residence_country: Optional[str] = Field(
        default=None,
        max_length=100
    )

    phone: Optional[str] = Field(
        default=None,
        max_length=30
    )

    # ------------------------------------------------------
    # IDENTIFICACIÓN
    # ------------------------------------------------------

    medical_license: Optional[str] = Field(
        default=None,
        max_length=100
    )

    identity_document_url: Optional[str] = Field(
        default=None,
        max_length=500
    )

    # ------------------------------------------------------
    # COLEGIACIÓN
    # ------------------------------------------------------

    professional_registration_number: Optional[str] = Field(
        default=None,
        max_length=100
    )

    professional_college: Optional[str] = Field(
        default=None,
        max_length=255
    )

    college_country: Optional[str] = Field(
        default=None,
        max_length=100
    )

    professional_registration_certificate_url: Optional[str] = Field(
        default=None,
        max_length=500
    )

    # ------------------------------------------------------
    # INFORMACIÓN PROFESIONAL
    # ------------------------------------------------------

    specialty: Optional[str] = Field(
        default=None,
        max_length=150
    )

    bio: Optional[str] = None

    experience: Optional[str] = None

    years_of_experience: Optional[int] = Field(
        default=None,
        ge=0,
        le=100
    )

    professional_description: Optional[str] = None

    # ------------------------------------------------------
    # UBICACIÓN
    # ------------------------------------------------------

    address: Optional[str] = Field(
        default=None,
        max_length=255
    )

    country: Optional[str] = Field(
        default=None,
        max_length=100
    )

    city: Optional[str] = Field(
        default=None,
        max_length=150
    )

    postal_code: Optional[str] = Field(
        default=None,
        max_length=20
    )

    latitude: Optional[float] = Field(
        default=None,
        ge=-90,
        le=90
    )

    longitude: Optional[float] = Field(
        default=None,
        ge=-180,
        le=180
    )

    # ------------------------------------------------------
    # INFORMACIÓN DE CONSULTA
    # ------------------------------------------------------

    consultation_phone: Optional[str] = Field(
        default=None,
        max_length=30
    )

    website: Optional[str] = Field(
        default=None,
        max_length=500
    )

    # ------------------------------------------------------
    # POLÍTICA DE DATOS
    # ------------------------------------------------------

    data_policy_accepted: Optional[bool] = None

    data_policy_accepted_at: Optional[datetime] = None


# ==========================================================
# DOCTOR PROFILE RESPONSE
# ==========================================================


class DoctorProfileResponse(BaseModel):

    # ------------------------------------------------------
    # USUARIO
    # ------------------------------------------------------

    user_id: int

    email: str

    role: str

    # ------------------------------------------------------
    # DATOS PERSONALES
    # ------------------------------------------------------

    first_name: str

    last_name: str

    date_of_birth: Optional[date] = None

    residence_country: Optional[str] = None

    phone: Optional[str] = None

    # ------------------------------------------------------
    # IDENTIFICACIÓN PROFESIONAL
    # ------------------------------------------------------

    medical_license: str

    identity_document_url: Optional[str] = None

    # ------------------------------------------------------
    # COLEGIACIÓN
    # ------------------------------------------------------

    professional_registration_number: Optional[str] = None

    professional_college: Optional[str] = None

    college_country: Optional[str] = None

    professional_registration_certificate_url: Optional[str] = None

    # ------------------------------------------------------
    # INFORMACIÓN PROFESIONAL
    # ------------------------------------------------------

    specialty: str

    bio: Optional[str] = None

    experience: Optional[str] = None

    years_of_experience: Optional[int] = None

    professional_description: Optional[str] = None

    # ------------------------------------------------------
    # UBICACIÓN
    # ------------------------------------------------------

    address: Optional[str] = None

    country: Optional[str] = None

    city: Optional[str] = None

    postal_code: Optional[str] = None

    latitude: Optional[float] = None

    longitude: Optional[float] = None

    # ------------------------------------------------------
    # INFORMACIÓN DE CONSULTA
    # ------------------------------------------------------

    consultation_phone: Optional[str] = None

    website: Optional[str] = None

    # ------------------------------------------------------
    # POLÍTICA DE DATOS
    # ------------------------------------------------------

    data_policy_accepted: bool

    data_policy_accepted_at: Optional[datetime] = None

    # ------------------------------------------------------
    # RELACIONES
    # ------------------------------------------------------

    educations: List[DoctorEducationResponse] = Field(
        default_factory=list
    )

    media: List[DoctorMediaResponse] = Field(
        default_factory=list
    )

    model_config = ConfigDict(
        from_attributes=True
    )


# ==========================================================
# DOCTOR CREATE / REGISTER
# ==========================================================


class DoctorCreateRequest(BaseModel):
    first_name: str = Field(
        ...,
        min_length=1,
        max_length=100
    )

    last_name: str = Field(
        ...,
        min_length=1,
        max_length=100
    )

    email: str = Field(
        ...,
        min_length=3,
        max_length=255
    )

    medical_license: str = Field(
        ...,
        min_length=1,
        max_length=100
    )

    specialty: str = Field(
        ...,
        min_length=1,
        max_length=150
    )

    phone: Optional[str] = Field(
        default=None,
        max_length=30
    )

    years_of_experience: Optional[int] = Field(
        default=None,
        ge=0,
        le=100
    )

    address: Optional[str] = Field(
        default=None,
        max_length=255
    )

    city: Optional[str] = Field(
        default=None,
        max_length=150
    )

    country: Optional[str] = Field(
        default=None,
        max_length=100
    )

    professional_description: Optional[str] = None

    experience: Optional[str] = None

    consultation_phone: Optional[str] = Field(
        default=None,
        max_length=30
    )

    date_of_birth: Optional[date] = None

    residence_country: Optional[str] = Field(
        default=None,
        max_length=100
    )

    professional_registration_number: Optional[str] = Field(
        default=None,
        max_length=100
    )

    professional_college: Optional[str] = Field(
        default=None,
        max_length=255
    )

    college_country: Optional[str] = Field(
        default=None,
        max_length=100
    )

    postal_code: Optional[str] = Field(
        default=None,
        max_length=20
    )

    website: Optional[str] = Field(
        default=None,
        max_length=500
    )

    language: Optional[str] = "es"

    password: Optional[str] = None