from datetime import datetime, date, time, timedelta

from sqlalchemy.orm import Session

from app.models.medical_doctor_availability import (
    MedicalDoctorAvailability
)
from app.models.medical_doctor_availability_exception import (
    MedicalDoctorAvailabilityException
)
from app.models.medical_appointment import (
    MedicalAppointment
)
from app.models.medical_appointment_status_history import (
    MedicalAppointmentStatusHistory
)


class MedicalAppointmentService:

    # ==========================================================
    # DISPONIBILIDAD DEL MÉDICO
    # ==========================================================

    @staticmethod
    def create_availability(
        db: Session,
        doctor_id: int,
        day_of_week: int,
        start_time: time,
        end_time: time,
        slot_duration: int = 30
    ):

        availability = MedicalDoctorAvailability(
            doctor_id=doctor_id,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            slot_duration=slot_duration,
            is_active=True
        )

        db.add(availability)
        db.commit()
        db.refresh(availability)

        return availability

    # ==========================================================

    @staticmethod
    def get_doctor_availabilities(
        db: Session,
        doctor_id: int
    ):

        return db.query(
            MedicalDoctorAvailability
        ).filter(
            MedicalDoctorAvailability.doctor_id == doctor_id,
            MedicalDoctorAvailability.is_active == True
        ).order_by(
            MedicalDoctorAvailability.day_of_week,
            MedicalDoctorAvailability.start_time
        ).all()

    # ==========================================================

    @staticmethod
    def delete_availability(
        db: Session,
        availability_id: int,
        doctor_id: int
    ):

        availability = db.query(
            MedicalDoctorAvailability
        ).filter(
            MedicalDoctorAvailability.id == availability_id,
            MedicalDoctorAvailability.doctor_id == doctor_id
        ).first()

        if not availability:
            return None

        availability.is_active = False

        db.commit()
        db.refresh(availability)

        return availability

    # ==========================================================
    # EXCEPCIONES
    # ==========================================================

    @staticmethod
    def create_exception(
        db: Session,
        doctor_id: int,
        exception_date: date,
        exception_type: str = "unavailable",
        start_time: time = None,
        end_time: time = None,
        reason: str = None
    ):

        exception = MedicalDoctorAvailabilityException(
            doctor_id=doctor_id,
            exception_date=exception_date,
            start_time=start_time,
            end_time=end_time,
            type=exception_type,
            reason=reason,
            is_active=True
        )

        db.add(exception)
        db.commit()
        db.refresh(exception)

        return exception

    # ==========================================================

    @staticmethod
    def get_exceptions(
        db: Session,
        doctor_id: int,
        exception_date: date = None
    ):

        query = db.query(
            MedicalDoctorAvailabilityException
        ).filter(
            MedicalDoctorAvailabilityException.doctor_id == doctor_id,
            MedicalDoctorAvailabilityException.is_active == True
        )

        if exception_date:
            query = query.filter(
                MedicalDoctorAvailabilityException.exception_date
                == exception_date
            )

        return query.order_by(
            MedicalDoctorAvailabilityException.exception_date
        ).all()

    # ==========================================================
    # HORARIOS DISPONIBLES
    # ==========================================================

    @staticmethod
    def get_available_slots(
        db: Session,
        doctor_id: int,
        appointment_date: date
    ):

        day_of_week = appointment_date.weekday()

        # ------------------------------------------------------
        # Buscar horarios normales del médico
        # ------------------------------------------------------

        availabilities = db.query(
            MedicalDoctorAvailability
        ).filter(
            MedicalDoctorAvailability.doctor_id == doctor_id,
            MedicalDoctorAvailability.day_of_week == day_of_week,
            MedicalDoctorAvailability.is_active == True
        ).order_by(
            MedicalDoctorAvailability.start_time
        ).all()

        if not availabilities:
            return []

        # ------------------------------------------------------
        # Buscar excepciones
        # ------------------------------------------------------

        exceptions = db.query(
            MedicalDoctorAvailabilityException
        ).filter(
            MedicalDoctorAvailabilityException.doctor_id == doctor_id,
            MedicalDoctorAvailabilityException.exception_date
            == appointment_date,
            MedicalDoctorAvailabilityException.is_active == True
        ).all()

        # ------------------------------------------------------
        # Buscar citas existentes
        # ------------------------------------------------------

        appointments = db.query(
            MedicalAppointment
        ).filter(
            MedicalAppointment.doctor_id == doctor_id,
            MedicalAppointment.appointment_date == appointment_date,
            MedicalAppointment.status.in_([
                "scheduled",
                "confirmed"
            ])
        ).all()

        occupied_times = {
            appointment.appointment_time
            for appointment in appointments
        }

        slots = []

        # ------------------------------------------------------
        # Generar slots
        # ------------------------------------------------------

        for availability in availabilities:

            current = datetime.combine(
                appointment_date,
                availability.start_time
            )

            end = datetime.combine(
                appointment_date,
                availability.end_time
            )

            duration = timedelta(
                minutes=availability.slot_duration
            )

            while current + duration <= end:

                slot_start = current.time()

                # ----------------------------------------------
                # Revisar excepciones
                # ----------------------------------------------

                blocked = False

                for exception in exceptions:

                    if exception.type == "unavailable":
                        blocked = True
                        break

                    if (
                        exception.type == "custom"
                        and exception.start_time
                        and exception.end_time
                    ):

                        if (
                            slot_start >= exception.start_time
                            and slot_start < exception.end_time
                        ):
                            blocked = True
                            break

                # ----------------------------------------------
                # Revisar citas ocupadas
                # ----------------------------------------------

                if (
                    not blocked
                    and slot_start not in occupied_times
                ):

                    slots.append({
                        "date": appointment_date,
                        "time": slot_start,
                        "available": True
                    })

                current += duration

        return slots

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
        location: str = None
    ):

        # ------------------------------------------------------
        # Verificar que el horario esté disponible
        # ------------------------------------------------------

        available_slots = MedicalAppointmentService.get_available_slots(
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
            location=location
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