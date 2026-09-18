from datetime import date, time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import nullslast
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

@router.post(
    ""
)
def create_appointment(
    data: AppointmentCreate,
    db: Session = Depends(get_db)
):

    appointment = MedicalAppointmentService.create_appointment(
        db=db,
        patient_id=data.patient_id,
        doctor_id=data.doctor_id,
        appointment_date=data.appointment_date,
        appointment_time=data.appointment_time
    )

    if not appointment:
        raise HTTPException(
            status_code=409,
            detail="El horario seleccionado no está disponible"
        )

    return appointment


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
