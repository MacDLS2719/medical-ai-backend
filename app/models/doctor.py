from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Doctor(Base):
    __tablename__ = "doctors"

    __table_args__ = (
        CheckConstraint(
            "latitude IS NULL OR (latitude >= -90 AND latitude <= 90)",
            name="ck_doctors_latitude_range"
        ),
        CheckConstraint(
            "longitude IS NULL OR (longitude >= -180 AND longitude <= 180)",
            name="ck_doctors_longitude_range"
        ),
    )

    # ==========================================================
    # IDENTIFICACIÓN
    # ==========================================================

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )

    # ==========================================================
    # DATOS PERSONALES
    # ==========================================================

    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    date_of_birth: Mapped[date | None] = mapped_column(
        Date,
        nullable=True
    )

    residence_country: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    phone: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True
    )

    # ==========================================================
    # IDENTIFICACIÓN PROFESIONAL
    # ==========================================================

    medical_license: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True
    )

    # Documento de identidad
    identity_document_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )

    # ==========================================================
    # COLEGIACIÓN PROFESIONAL
    # ==========================================================

    professional_registration_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    professional_college: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    college_country: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    # Certificación de colegiación
    professional_registration_certificate_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )

    # ==========================================================
    # INFORMACIÓN PROFESIONAL
    # ==========================================================

    # ----------------------------------------------------------
    # LEGACY
    # ----------------------------------------------------------
    # Se mantiene temporalmente para compatibilidad con
    # información existente.
    #
    # La especialidad oficial se maneja mediante:
    #
    # doctor_specialties
    #       ↓
    # specialties
    #       ↓
    # is_primary
    # ----------------------------------------------------------

    specialty: Mapped[str] = mapped_column(
        String(150),
        nullable=False
    )

    # Información anterior de experiencia.
    # Se mantiene temporalmente por compatibilidad.
    experience: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    # Años de experiencia estructurados
    years_of_experience: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    # Descripción profesional
    professional_description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    # ==========================================================
    # UBICACIÓN DE ATENCIÓN
    # ==========================================================

    address: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    country: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    city: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True
    )

    postal_code: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True
    )

    latitude: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    longitude: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    # ==========================================================
    # INFORMACIÓN DE CONSULTA
    # ==========================================================

    consultation_phone: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True
    )

    website: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )

    # ==========================================================
    # POLÍTICA DE TRATAMIENTO DE DATOS
    # ==========================================================

    data_policy_accepted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    data_policy_accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    # ==========================================================
    # ESTADO
    # ==========================================================

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    # ==========================================================
    # FECHAS
    # ==========================================================

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # ==========================================================
    # RELACIÓN CON USER
    # ==========================================================

    user: Mapped["User"] = relationship(
        "User",
        back_populates="doctor"
    )

    # ==========================================================
    # ESPECIALIDADES
    # ==========================================================

    doctor_specialties: Mapped[list["DoctorSpecialty"]] = relationship(
        "DoctorSpecialty",
        back_populates="doctor",
        cascade="all, delete-orphan"
    )

    # ==========================================================
    # EDUCACIÓN
    # ==========================================================

    educations: Mapped[list["DoctorEducation"]] = relationship(
        "DoctorEducation",
        back_populates="doctor",
        cascade="all, delete-orphan"
    )

    # ==========================================================
    # ARCHIVOS / MULTIMEDIA
    # ==========================================================

    media: Mapped[list["DoctorMedia"]] = relationship(
        "DoctorMedia",
        back_populates="doctor",
        cascade="all, delete-orphan"
    )