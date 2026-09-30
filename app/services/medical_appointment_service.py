from calendar import monthrange
from datetime import date, time, timedelta

from sqlalchemy.orm import Session

from app.models.medical_appointment import MedicalAppointment
from app.models.medical_appointment_status_history import (
    MedicalAppointmentStatusHistory
)
from app.services.doctor_availability import DoctorAvailabilityService


class MedicalAppointmentService:

    # ==========================================================
    # CREAR CITA
    # ==========================================================

    @staticmethod
    def create_appointment(
        db: Session,
        patient_id: int,
        doctor_id: int,
        appointment_date: date,
        appointment_time: time,
        consultation_type: str
    ):

        # ------------------------------------------------------
        # Validar tipo de consulta
        # ------------------------------------------------------

        allowed_types = [
            "presencial",
            "video"
        ]

        if consultation_type not in allowed_types:
            return None

        # ------------------------------------------------------
        # Obtener horarios del médico para ese día
        # ------------------------------------------------------

        available_slots = DoctorAvailabilityService.get_available_slots(
            db=db,
            doctor_id=doctor_id,
            appointment_date=appointment_date
        )

        # ------------------------------------------------------
        # Buscar exactamente el horario solicitado
        # ------------------------------------------------------

        requested_slot = next(
            (
                slot
                for slot in available_slots
                if (
                    slot["time"] == appointment_time
                    and slot["consultation_type"] == consultation_type
                    and slot["available"] is True
                )
            ),
            None
        )

        # ------------------------------------------------------
        # El horario no existe o ya está ocupado
        # ------------------------------------------------------

        if not requested_slot:
            return None

        # ------------------------------------------------------
        # SEGUNDA VALIDACIÓN CONTRA DOBLE RESERVA
        # ------------------------------------------------------
        #
        # Esto es importante porque dos pacientes podrían
        # intentar reservar exactamente el mismo horario.
        #
        # ------------------------------------------------------

        existing_appointment = db.query(
            MedicalAppointment
        ).filter(
            MedicalAppointment.doctor_id == doctor_id,
            MedicalAppointment.appointment_date == appointment_date,
            MedicalAppointment.appointment_time == appointment_time,
            MedicalAppointment.status.in_([
                "scheduled",
                "confirmed"
            ])
        ).first()

        if existing_appointment:
            return None

        # ------------------------------------------------------
        # Determinar ubicación
        # ------------------------------------------------------

        location = None

        if consultation_type == "presencial":
            slot_location = requested_slot.get("location")

            if isinstance(slot_location, dict):
                address = slot_location.get("address")
                latitude = slot_location.get("latitude")
                longitude = slot_location.get("longitude")
                location = address or (
                    f"{latitude}, {longitude}"
                    if latitude is not None and longitude is not None
                    else None
                )
            elif isinstance(slot_location, str):
                location = slot_location

        # Videoconsulta siempre queda sin ubicación física
        if consultation_type == "video":
            location = None

        # ------------------------------------------------------
        # Crear cita
        # ------------------------------------------------------

        appointment = MedicalAppointment(
            patient_id=patient_id,
            doctor_id=doctor_id,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            consultation_type=consultation_type,
            location=location,
            status="scheduled"
        )

        db.add(appointment)

        # Necesitamos el ID para el historial
        db.flush()

        # ------------------------------------------------------
        # Registrar historial
        # ------------------------------------------------------

        history = MedicalAppointmentStatusHistory(
            appointment_id=appointment.id,
            status="scheduled",
            changed_by=patient_id,
            reason="Cita creada"
        )

        db.add(history)

        # ------------------------------------------------------
        # Guardar
        # ------------------------------------------------------

        db.commit()

        db.refresh(appointment)

        return appointment

    # ==========================================================
    # OBTENER CITA
    # ==========================================================

    @staticmethod
    def get_appointment(
        db: Session,
        appointment_id: int
    ):

        return db.query(
            MedicalAppointment
        ).filter(
            MedicalAppointment.id == appointment_id
        ).first()

    # ==========================================================
    # CITAS DEL PACIENTE
    # ==========================================================

    @staticmethod
    def get_patient_appointments(
        db: Session,
        patient_id: int
    ):

        return db.query(
            MedicalAppointment
        ).filter(
            MedicalAppointment.patient_id == patient_id
        ).order_by(
            MedicalAppointment.appointment_date.desc(),
            MedicalAppointment.appointment_time.desc()
        ).all()

    # ==========================================================
    # CITAS DEL MÉDICO
    # ==========================================================

    @staticmethod
    def get_doctor_appointments(
        db: Session,
        doctor_id: int
    ):

        return db.query(
            MedicalAppointment
        ).filter(
            MedicalAppointment.doctor_id == doctor_id
        ).order_by(
            MedicalAppointment.appointment_date.asc(),
            MedicalAppointment.appointment_time.asc()
        ).all()

    # ==========================================================
    # CALENDARIO DEL MÉDICO
    # ==========================================================

    @staticmethod
    def get_doctor_calendar(
        db: Session,
        doctor_id: int,
        year: int,
        month: int,
        consultation_type: str
    ):

        # ------------------------------------------------------
        # Validar tipo
        # ------------------------------------------------------

        allowed_types = [
            "presencial",
            "video"
        ]

        if consultation_type not in allowed_types:
            return None

        # ------------------------------------------------------
        # Validar mes
        # ------------------------------------------------------

        if month < 1 or month > 12:
            return None

        # ------------------------------------------------------
        # Primer y último día del mes
        # ------------------------------------------------------

        first_day = date(
            year,
            month,
            1
        )

        last_day = date(
            year,
            month,
            monthrange(year, month)[1]
        )

        # ------------------------------------------------------
        # Construir calendario
        # ------------------------------------------------------

        days = []

        current_date = first_day

        while current_date <= last_day:

            # --------------------------------------------------
            # Obtener slots del día
            # --------------------------------------------------

            slots = DoctorAvailabilityService.get_available_slots(
                db=db,
                doctor_id=doctor_id,
                appointment_date=current_date
            )

            # --------------------------------------------------
            # Filtrar únicamente el tipo solicitado
            # --------------------------------------------------

            slots = [
                slot
                for slot in slots
                if slot["consultation_type"] == consultation_type
            ]

            # --------------------------------------------------
            # Determinar si el día tiene disponibilidad
            # --------------------------------------------------

            day_available = any(
                slot["available"] is True
                for slot in slots
            )

            # --------------------------------------------------
            # Agregar día
            # --------------------------------------------------

            days.append({
                "date": current_date,
                "day_of_week": current_date.weekday(),
                "available": day_available,
                "slots": slots
            })

            current_date += timedelta(days=1)

        # ------------------------------------------------------
        # Resultado
        # ------------------------------------------------------

        return {
            "doctor_id": doctor_id,
            "year": year,
            "month": month,
            "consultation_type": consultation_type,
            "days": days
        }

    # ==========================================================
    # CAMBIAR ESTADO
    # ==========================================================

    @staticmethod
    def update_status(
        db: Session,
        appointment_id: int,
        status: str,
        changed_by: int,
        reason: str = None
    ):

        appointment = db.query(
            MedicalAppointment
        ).filter(
            MedicalAppointment.id == appointment_id
        ).first()

        if not appointment:
            return None

        # ------------------------------------------------------
        # Actualizar estado
        # ------------------------------------------------------

        appointment.status = status

        # ------------------------------------------------------
        # Registrar historial
        # ------------------------------------------------------

        history = MedicalAppointmentStatusHistory(
            appointment_id=appointment.id,
            status=status,
            changed_by=changed_by,
            reason=reason
        )

        db.add(history)

        db.commit()

        db.refresh(appointment)

        return appointment

    # ==========================================================
    # CANCELAR CITA
    # ==========================================================

    @staticmethod
    def cancel_appointment(
        db: Session,
        appointment_id: int,
        user_id: int,
        reason: str = None
    ):

        appointment = db.query(
            MedicalAppointment
        ).filter(
            MedicalAppointment.id == appointment_id
        ).first()

        if not appointment:
            return None

        # ------------------------------------------------------
        # Verificar que el usuario participe en la cita
        # ------------------------------------------------------

        if (
            appointment.patient_id != user_id
            and appointment.doctor_id != user_id
        ):
            return None

        # ------------------------------------------------------
        # Verificar estado
        # ------------------------------------------------------

        if appointment.status in [
            "cancelled",
            "completed"
        ]:
            return None

        # ------------------------------------------------------
        # Cancelar
        # ------------------------------------------------------

        appointment.status = "cancelled"

        # ------------------------------------------------------
        # Historial
        # ------------------------------------------------------

        history = MedicalAppointmentStatusHistory(
            appointment_id=appointment.id,
            status="cancelled",
            changed_by=user_id,
            reason=reason
        )

        db.add(history)

        db.commit()

        db.refresh(appointment)

        return appointment

    # ==========================================================
    # HISTORIAL DE ESTADOS
    # ==========================================================

    @staticmethod
    def get_status_history(
        db: Session,
        appointment_id: int
    ):

        return db.query(
            MedicalAppointmentStatusHistory
        ).filter(
            MedicalAppointmentStatusHistory.appointment_id
            == appointment_id
        ).order_by(
            MedicalAppointmentStatusHistory.created_at.asc()
        ).all()