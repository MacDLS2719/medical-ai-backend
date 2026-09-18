from datetime import datetime, date, time, timedelta

from sqlalchemy.orm import Session

from app.models.medical_appointment import (
    MedicalAppointment
)
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
        appointment_time: time
    ):

        # ------------------------------------------------------
        # Verificar que el horario esté disponible
        # ------------------------------------------------------

        available_slots = DoctorAvailabilityService.get_available_slots(
            db=db,
            doctor_id=doctor_id,
            appointment_date=appointment_date
        )

        requested_slot = next(
            (
                slot
                for slot in available_slots
                if slot["time"] == appointment_time
            ),
            None
        )

        if not requested_slot:
            return None

        # ------------------------------------------------------
        # Crear cita
        # ------------------------------------------------------

        appointment = MedicalAppointment(
            patient_id=patient_id,
            doctor_id=doctor_id,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            status="scheduled",
            location=requested_slot.get("location")
        )

        db.add(appointment)
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

        appointment.status = status

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
        # Validar que el usuario participe en la cita
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

        appointment.status = "cancelled"

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
