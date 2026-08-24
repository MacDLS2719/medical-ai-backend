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

class AvailabilityCreate(BaseModel):
    doctor_id: int
    day_of_week: int
    start_time: time
    end_time: time
    slot_duration: int = 30


class ExceptionCreate(BaseModel):
    doctor_id: int
    exception_date: date
    type: str = "unavailable"
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    reason: Optional[str] = None


class AppointmentCreate(BaseModel):
    patient_id: int
    doctor_id: int
    appointment_date: date
    appointment_time: time
    location: Optional[str] = None


class AppointmentStatusUpdate(BaseModel):
    status: str
    changed_by: int
    reason: Optional[str] = None


class AppointmentCancel(BaseModel):
    user_id: int
    reason: Optional[str] = None


# ==========================================================
# DISPONIBILIDAD DEL MÉDICO
# ==========================================================

@router.post(
    "/availability"
)
def create_availability(
    data: AvailabilityCreate,
    db: Session = Depends(get_db)
):

    if data.day_of_week < 0 or data.day_of_week > 6:
        raise HTTPException(
            status_code=400,
            detail="day_of_week debe estar entre 0 y 6"
        )

    if data.start_time >= data.end_time:
        raise HTTPException(
            status_code=400,
            detail="La hora de inicio debe ser menor que la hora de finalización"
        )

    if data.slot_duration <= 0:
        raise HTTPException(
            status_code=400,
            detail="La duración del turno debe ser mayor que 0"
        )

    availability = MedicalAppointmentService.create_availability(
        db=db,
        doctor_id=data.doctor_id,
        day_of_week=data.day_of_week,
        start_time=data.start_time,
        end_time=data.end_time,
        slot_duration=data.slot_duration
    )

    return availability


# ==========================================================

@router.get(
    "/availability/{doctor_id}"
)
def get_doctor_availability(
    doctor_id: int,
    db: Session = Depends(get_db)
):

    return MedicalAppointmentService.get_doctor_availabilities(
        db=db,
        doctor_id=doctor_id
    )


# ==========================================================

@router.delete(
    "/availability/{availability_id}"
)
def delete_availability(
    availability_id: int,
    doctor_id: int,
    db: Session = Depends(get_db)
):

    availability = MedicalAppointmentService.delete_availability(
        db=db,
        availability_id=availability_id,
        doctor_id=doctor_id
    )

    if not availability:
        raise HTTPException(
            status_code=404,
            detail="Disponibilidad no encontrada"
        )

    return {
        "message": "Disponibilidad eliminada correctamente"
    }


# ==========================================================
# EXCEPCIONES
# ==========================================================

@router.post(
    "/availability/exceptions"
)
def create_exception(
    data: ExceptionCreate,
    db: Session = Depends(get_db)
):

    if data.type not in [
        "unavailable",
        "custom"
    ]:
        raise HTTPException(
            status_code=400,
            detail="Tipo de excepción inválido"
        )

    if data.type == "custom":

        if not data.start_time or not data.end_time:
            raise HTTPException(
                status_code=400,
                detail="Las excepciones custom requieren start_time y end_time"
            )

        if data.start_time >= data.end_time:
            raise HTTPException(
                status_code=400,
                detail="La hora de inicio debe ser menor que la hora final"
            )

    exception = MedicalAppointmentService.create_exception(
        db=db,
        doctor_id=data.doctor_id,
        exception_date=data.exception_date,
        exception_type=data.type,
        start_time=data.start_time,
        end_time=data.end_time,
        reason=data.reason
    )

    return exception


# ==========================================================

@router.get(
    "/availability/{doctor_id}/exceptions"
)
def get_exceptions(
    doctor_id: int,
    exception_date: Optional[date] = None,
    db: Session = Depends(get_db)
):

    return MedicalAppointmentService.get_exceptions(
        db=db,
        doctor_id=doctor_id,
        exception_date=exception_date
    )


# ==========================================================
# HORARIOS DISPONIBLES
# ==========================================================

@router.get(
    "/available-slots/{doctor_id}"
)
def get_available_slots(
    doctor_id: int,
    appointment_date: date,
    db: Session = Depends(get_db)
):

    slots = MedicalAppointmentService.get_available_slots(
        db=db,
        doctor_id=doctor_id,
        appointment_date=appointment_date
    )

    return {
        "doctor_id": doctor_id,
        "date": appointment_date,
        "slots": slots
    }


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
        appointment_time=data.appointment_time,
        location=data.location
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