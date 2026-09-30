from datetime import date, time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.medical_appointment_service import (
    MedicalAppointmentService
)


router = APIRouter(
    prefix="/appointments",
    tags=["Medical Appointments"]
)


# ==========================================================
# SCHEMAS
# ==========================================================

class AppointmentCreate(BaseModel):
    patient_id: int
    doctor_id: int
    appointment_date: date
    appointment_time: time
    consultation_type: str


class AppointmentStatusUpdate(BaseModel):
    status: str
    changed_by: int
    reason: Optional[str] = None


class AppointmentCancel(BaseModel):
    user_id: int
    reason: Optional[str] = None


# ==========================================================
# CREAR CITA
# ==========================================================

@router.post("")
def create_appointment(
    data: AppointmentCreate,
    db: Session = Depends(get_db)
):

    # ------------------------------------------------------
    # Validar tipo de consulta
    # ------------------------------------------------------

    allowed_types = [
        "presencial",
        "video"
    ]

    if data.consultation_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Tipo de consulta inválido"
        )

    # ------------------------------------------------------
    # Crear cita
    # ------------------------------------------------------

    appointment = MedicalAppointmentService.create_appointment(
        db=db,
        patient_id=data.patient_id,
        doctor_id=data.doctor_id,
        appointment_date=data.appointment_date,
        appointment_time=data.appointment_time,
        consultation_type=data.consultation_type
    )

    # ------------------------------------------------------
    # Horario ocupado
    # ------------------------------------------------------

    if not appointment:
        raise HTTPException(
            status_code=409,
            detail="El horario seleccionado ya no está disponible"
        )

    return appointment


# ==========================================================
# CALENDARIO DEL MÉDICO
# ==========================================================

@router.get(
    "/doctor/{doctor_id}/calendar"
)
def get_doctor_calendar(
    doctor_id: int,
    year: int,
    month: int,
    consultation_type: str,
    db: Session = Depends(get_db)
):

    # ------------------------------------------------------
    # Validar mes
    # ------------------------------------------------------

    if month < 1 or month > 12:
        raise HTTPException(
            status_code=400,
            detail="Mes inválido"
        )

    # ------------------------------------------------------
    # Validar tipo
    # ------------------------------------------------------

    allowed_types = [
        "presencial",
        "video"
    ]

    if consultation_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Tipo de consulta inválido"
        )

    # ------------------------------------------------------
    # Obtener calendario
    # ------------------------------------------------------

    calendar = MedicalAppointmentService.get_doctor_calendar(
        db=db,
        doctor_id=doctor_id,
        year=year,
        month=month,
        consultation_type=consultation_type
    )

    if calendar is None:
        raise HTTPException(
            status_code=400,
            detail="No fue posible obtener el calendario"
        )

    return calendar


# ==========================================================
# OBTENER CITA
# ==========================================================

@router.get(
    "/{appointment_id}"
)
def get_appointment(
    appointment_id: int,
    db: Session = Depends(get_db)
):

    appointment = MedicalAppointmentService.get_appointment(
        db=db,
        appointment_id=appointment_id
    )

    if not appointment:
        raise HTTPException(
            status_code=404,
            detail="Cita no encontrada"
        )

    return appointment


# ==========================================================
# CITAS DEL PACIENTE
# ==========================================================

@router.get(
    "/patient/{patient_id}"
)
def get_patient_appointments(
    patient_id: int,
    db: Session = Depends(get_db)
):

    return MedicalAppointmentService.get_patient_appointments(
        db=db,
        patient_id=patient_id
    )


# ==========================================================
# CITAS DEL MÉDICO
# ==========================================================

@router.get(
    "/doctor/{doctor_id}"
)
def get_doctor_appointments(
    doctor_id: int,
    db: Session = Depends(get_db)
):

    return MedicalAppointmentService.get_doctor_appointments(
        db=db,
        doctor_id=doctor_id
    )


# ==========================================================
# ACTUALIZAR ESTADO
# ==========================================================

@router.patch(
    "/{appointment_id}/status"
)
def update_status(
    appointment_id: int,
    data: AppointmentStatusUpdate,
    db: Session = Depends(get_db)
):

    allowed_statuses = [
        "scheduled",
        "confirmed",
        "cancelled",
        "completed"
    ]

    if data.status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail="Estado de cita inválido"
        )

    appointment = MedicalAppointmentService.update_status(
        db=db,
        appointment_id=appointment_id,
        status=data.status,
        changed_by=data.changed_by,
        reason=data.reason
    )

    if not appointment:
        raise HTTPException(
            status_code=404,
            detail="Cita no encontrada"
        )

    return appointment


# ==========================================================
# CANCELAR CITA
# ==========================================================

@router.patch(
    "/{appointment_id}/cancel"
)
def cancel_appointment(
    appointment_id: int,
    data: AppointmentCancel,
    db: Session = Depends(get_db)
):

    appointment = MedicalAppointmentService.cancel_appointment(
        db=db,
        appointment_id=appointment_id,
        user_id=data.user_id,
        reason=data.reason
    )

    if not appointment:
        raise HTTPException(
            status_code=404,
            detail="Cita no encontrada o no puede ser cancelada"
        )

    return appointment


# ==========================================================
# HISTORIAL
# ==========================================================

@router.get(
    "/{appointment_id}/history"
)
def get_status_history(
    appointment_id: int,
    db: Session = Depends(get_db)
):

    return MedicalAppointmentService.get_status_history(
        db=db,
        appointment_id=appointment_id
    )