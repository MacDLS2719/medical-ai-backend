from datetime import date, time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import nullslast
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.medical_doctor_availability import MedicalDoctorAvailability
from app.services.doctor_availability import DoctorAvailabilityService


router = APIRouter(
    prefix="/doctor-availability",
    tags=["Doctor Availability"]
)


# ==========================================================
# SCHEMAS
# ==========================================================

class AvailabilityCreate(BaseModel):
    doctor_id: int
    day_of_week: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    start_time: time
    end_time: time
    slot_duration: int = 30
    location: Optional[str] = None
    consultation_type: str = "presencial"


class ExceptionCreate(BaseModel):
    doctor_id: int
    exception_date: date
    type: str = "unavailable"
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    reason: Optional[str] = None
    consultation_type: Optional[str] = None


# ==========================================================
# DISPONIBILIDAD DEL MÉDICO
# ==========================================================

@router.post(
    ""
)
def create_availability(
    data: AvailabilityCreate,
    db: Session = Depends(get_db)
):

    if data.day_of_week is not None and (data.day_of_week < 0 or data.day_of_week > 6):
        raise HTTPException(
            status_code=400,
            detail="day_of_week debe estar entre 0 y 6"
        )

    if data.start_date and data.end_date and data.start_date > data.end_date:
        raise HTTPException(
            status_code=400,
            detail="La fecha de inicio debe ser menor o igual a la fecha de fin"
        )

    if data.day_of_week is None and (data.start_date is None or data.end_date is None):
        raise HTTPException(
            status_code=400,
            detail="Debe especificar day_of_week o un rango de fechas (start_date, end_date)"
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

    availability = DoctorAvailabilityService.create_availability(
        db=db,
        doctor_id=data.doctor_id,
        day_of_week=data.day_of_week,
        start_date=data.start_date,
        end_date=data.end_date,
        start_time=data.start_time,
        end_time=data.end_time,
        slot_duration=data.slot_duration,
        location=data.location,
        consultation_type=data.consultation_type
    )

    return availability


# ==========================================================
# LISTAR MÉDICOS CON DISPONIBILIDAD
# ==========================================================

@router.get(
    "/doctors"
)
def get_doctors_with_availability(
    db: Session = Depends(get_db)
):
    from app.models.doctor import Doctor
    from app.models.user import User

    doctors = db.query(Doctor).join(
        User, Doctor.user_id == User.id
    ).filter(
        Doctor.is_active == True,
        User.is_active == True
    ).order_by(Doctor.first_name).all()

    result = []
    for doctor in doctors:
        availabilities = db.query(
            MedicalDoctorAvailability
        ).filter(
            MedicalDoctorAvailability.doctor_id == doctor.user_id,
            MedicalDoctorAvailability.is_active == True
        ).order_by(
            nullslast(MedicalDoctorAvailability.start_date),
            nullslast(MedicalDoctorAvailability.day_of_week),
            MedicalDoctorAvailability.start_time
        ).all()

        avail_list = []
        for a in availabilities:
            avail_list.append({
                "id": a.id,
                "day_of_week": a.day_of_week,
                "start_date": str(a.start_date) if a.start_date else None,
                "end_date": str(a.end_date) if a.end_date else None,
                "start_time": str(a.start_time)[:5] if a.start_time else None,
                "end_time": str(a.end_time)[:5] if a.end_time else None,
                "slot_duration": a.slot_duration,
                "consultation_type": a.consultation_type,
            })

        result.append({
            "user_id": doctor.user_id,
            "first_name": doctor.first_name,
            "last_name": doctor.last_name,
            "specialty": doctor.specialty,
            "latitude": doctor.latitude,
            "longitude": doctor.longitude,
            "address": doctor.address,
            "availabilities": avail_list,
        })

    return result


# ==========================================================

@router.get(
    "/{doctor_id}"
)
def get_doctor_availability(
    doctor_id: int,
    db: Session = Depends(get_db)
):

    return DoctorAvailabilityService.get_doctor_availabilities(
        db=db,
        doctor_id=doctor_id
    )


# ==========================================================

@router.delete(
    "/{availability_id}"
)
def delete_availability(
    availability_id: int,
    doctor_id: int,
    db: Session = Depends(get_db)
):

    availability = DoctorAvailabilityService.delete_availability(
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
    "/exceptions"
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

    exception = DoctorAvailabilityService.create_exception(
        db=db,
        doctor_id=data.doctor_id,
        exception_date=data.exception_date,
        exception_type=data.type,
        start_time=data.start_time,
        end_time=data.end_time,
        reason=data.reason,
        consultation_type=data.consultation_type
    )

    return exception


# ==========================================================

@router.get(
    "/{doctor_id}/exceptions"
)
def get_exceptions(
    doctor_id: int,
    exception_date: Optional[date] = None,
    db: Session = Depends(get_db)
):

    return DoctorAvailabilityService.get_exceptions(
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

    slots = DoctorAvailabilityService.get_available_slots(
        db=db,
        doctor_id=doctor_id,
        appointment_date=appointment_date
    )

    return {
        "doctor_id": doctor_id,
        "date": appointment_date,
        "slots": slots
    }
