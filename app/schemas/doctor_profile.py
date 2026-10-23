from datetime import date, datetime
from typing import Any, List, Optional, Union

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

    identity_document_url: Optional[str] = Field(
        default=None,
        max_length=500
    )

    college_country: Optional[str] = Field(
        default=None,
        max_length=100
    )

    professional_registration_certificate_url: Optional[str] = Field(
        default=None,
        max_length=500
    )

    linkgoogle: Optional[str] = Field(
        default=None,
        max_length=1000
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

    languages: Optional[Union[List[str], str]] = None
    insurance_company: Optional[str] = None

    # ------------------------------------------------------
    # POLÍTICA DE DATOS
    # ------------------------------------------------------

    data_policy_accepted: Optional[bool] = None

    data_policy_accepted_at: Optional[datetime] = None

    # ------------------------------------------------------
    # PERFIL DE GOOGLE ASOCIADO
    # ------------------------------------------------------

    google_profile_data: Optional[dict[str, Any]] = None



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

    identity_document_url: Optional[str] = None

    college_country: Optional[str] = None

    professional_registration_certificate_url: Optional[str] = None

    linkgoogle: Optional[str] = None

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
    languages: Optional[Union[List[str], str]] = None
    insurance_company: Optional[str] = None

    # ------------------------------------------------------
    # ESTADO Y VERIFICACIÓN
    # ------------------------------------------------------

    verification_status: Optional[str] = "pending"

    # ------------------------------------------------------
    # POLÍTICA DE DATOS
    # ------------------------------------------------------


    data_policy_accepted: bool

    data_policy_accepted_at: Optional[datetime] = None

    google_profile_data: Optional[dict[str, Any]] = None


    # ------------------------------------------------------
    # RELACIONES
    # ------------------------------------------------------

    educations: List[DoctorEducationResponse] = Field(
        default_factory=list
    )

    media: List[DoctorMediaResponse] = Field(
        default_factory=list
    )

    subscription: Optional[dict] = None

    model_config = ConfigDict(
        from_attributes=True
    )


# ==========================================================
# SUBSCRIPTION PLAN
# ==========================================================


class SubscriptionPlanResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str] = None
    price: float
    currency: str
    billing_interval: str
    is_free: bool
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )


# ==========================================================
# DOCTOR CREATE / REGISTER
# ==========================================================


class DoctorFreeCreateRequest(BaseModel):
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

    linkgoogle: Optional[str] = Field(
        default=None,
        max_length=1000
    )

    specialty: str = Field(
        ...,
        min_length=1,
        max_length=150
    )

    residence_country: str = Field(
        ...,
        min_length=1,
        max_length=100
    )

    phone: str = Field(
        ...,
        min_length=1,
        max_length=30
    )

    email: str = Field(
        ...,
        min_length=3,
        max_length=255
    )

    password: Optional[str] = None
    language: Optional[str] = "es"
    subscription_plan_id: Optional[int] = None
    google_profile_data: Optional[dict[str, Any]] = None
    certificate_base64: Optional[str] = None
    certificate_filename: Optional[str] = None
    certificate_mime_type: Optional[str] = None
    languages: Optional[Union[List[str], str]] = None
    insurance_company: Optional[str] = None



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

    college_country: Optional[str] = Field(
        default=None,
        max_length=100
    )

    linkgoogle: Optional[str] = Field(
        default=None,
        max_length=1000
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

    website: Optional[str] = Field(
        default=None,
        max_length=500
    )

    language: Optional[str] = "es"
    languages: Optional[Union[List[str], str]] = None
    insurance_company: Optional[str] = None

    password: Optional[str] = None

    # Plan de suscripción seleccionado por el médico en el registro
    subscription_plan_id: Optional[int] = Field(
        default=None,
        description="ID del plan de suscripción elegido. Si es None se asigna el plan gratuito."
    )
    google_profile_data: Optional[dict[str, Any]] = None
