from datetime import datetime, date, time, timedelta

from sqlalchemy.orm import Session

from app.models.doctor import Doctor
from app.models.medical_doctor_availability import (
    MedicalDoctorAvailability
)
from app.models.medical_doctor_availability_exception import (
    MedicalDoctorAvailabilityException
)
from app.models.medical_appointment import (
    MedicalAppointment
)


class DoctorAvailabilityService:

    # ==========================================================
    # OBTENER UBICACIÓN DEL MÉDICO
    # ==========================================================

    @staticmethod
    def get_doctor_location(
        db: Session,
        doctor_id: int,
        consultation_type: str
    ):
        """
        Obtiene la ubicación que corresponde a una disponibilidad.

        PRESENCIAL:
            1. Si existen latitude y longitude, se usan las coordenadas.
            2. Si no existen coordenadas, se utiliza la dirección.

        VIDEO:
            No tiene ubicación.
        """

        if consultation_type == "video":
            return None

        doctor = db.query(
            Doctor
        ).filter(
            Doctor.user_id == doctor_id
        ).first()

        if not doctor:
            return None

        # ------------------------------------------------------
        # Si tiene coordenadas, son la ubicación principal
        # ------------------------------------------------------

        if doctor.latitude is not None and doctor.longitude is not None:
            return {
                "address": doctor.address,
                "latitude": doctor.latitude,
                "longitude": doctor.longitude,
            }

        # ------------------------------------------------------
        # Si no tiene coordenadas, utilizar dirección
        # ------------------------------------------------------

        return {
            "address": doctor.address,
            "latitude": None,
            "longitude": None,
        }

    # ==========================================================
    # CREAR DISPONIBILIDAD
    # ==========================================================

    @staticmethod
    def create_availability(
        db: Session,
        doctor_id: int,
        day_of_week: int = None,
        start_date: date = None,
        end_date: date = None,
        start_time: time = None,
        end_time: time = None,
        slot_duration: int = 30,
        consultation_type: str = "presencial"
    ):

        # ------------------------------------------------------
        # Validar médico
        # ------------------------------------------------------

        doctor = db.query(
            Doctor
        ).filter(
            Doctor.user_id == doctor_id,
            Doctor.is_active == True
        ).first()

        if not doctor:
            return None

        # ------------------------------------------------------
        # Validar tipo de consulta
        # ------------------------------------------------------

        if consultation_type not in [
            "presencial",
            "video"
        ]:
            raise ValueError(
                "El tipo de consulta debe ser presencial o video"
            )

        # ------------------------------------------------------
        # Validar ubicación para consulta presencial
        # ------------------------------------------------------

        if consultation_type == "presencial":

            if (
                doctor.latitude is None
                and doctor.longitude is None
                and not doctor.address
            ):
                raise ValueError(
                    "El médico no tiene una dirección ni coordenadas "
                    "registradas para consultas presenciales"
                )

        # ------------------------------------------------------
        # Para video no guardamos dirección
        # ------------------------------------------------------

        location = None

        if consultation_type == "presencial":

            if (
                doctor.latitude is not None
                and doctor.longitude is not None
            ):
                location = doctor.address

            else:
                location = doctor.address

        # ------------------------------------------------------
        # Crear disponibilidad
        # ------------------------------------------------------

        availability = MedicalDoctorAvailability(
            doctor_id=doctor_id,
            day_of_week=day_of_week,
            start_date=start_date,
            end_date=end_date,
            start_time=start_time,
            end_time=end_time,
            slot_duration=slot_duration,
            address=location,
            consultation_type=consultation_type,
            is_active=True
        )

        db.add(availability)
        db.commit()
        db.refresh(availability)

        return availability

    # ==========================================================
    # LISTAR DISPONIBILIDADES
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
    # ELIMINAR DISPONIBILIDAD
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
        reason: str = None,
        consultation_type: str = None
    ):

        exception = MedicalDoctorAvailabilityException(
            doctor_id=doctor_id,
            exception_date=exception_date,
            start_time=start_time,
            end_time=end_time,
            type=exception_type,
            reason=reason,
            consultation_type=consultation_type,
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
        # Buscar horarios normales
        # ------------------------------------------------------

        availabilities = db.query(
            MedicalDoctorAvailability
        ).filter(
            MedicalDoctorAvailability.doctor_id == doctor_id,
            MedicalDoctorAvailability.is_active == True,
            (
                MedicalDoctorAvailability.day_of_week == day_of_week
            ) | (
                (MedicalDoctorAvailability.start_date <= appointment_date) &
                (MedicalDoctorAvailability.end_date >= appointment_date)
            )
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

                    # ------------------------------------------
                    # Ubicación
                    # ------------------------------------------

                    location = (
                        None
                        if availability.consultation_type == "video"
                        else self_get_location_from_doctor(
                            db,
                            doctor_id
                        )
                    )

                    slots.append({
                        "date": appointment_date,
                        "time": slot_start,
                        "available": True,
                        "location": location,
                        "consultation_type": availability.consultation_type
                    })

                current += duration

        return slots


def self_get_location_from_doctor(
    db: Session,
    doctor_id: int
):
    """
    Obtiene la ubicación actual del médico.

    Se utiliza para que los slots no dependan de una
    dirección antigua almacenada en la disponibilidad.
    """

    doctor = db.query(
        Doctor
    ).filter(
        Doctor.user_id == doctor_id
    ).first()

    if not doctor:
        return None

    if (
        doctor.latitude is not None
        and doctor.longitude is not None
    ):
        return {
            "address": doctor.address,
            "latitude": doctor.latitude,
            "longitude": doctor.longitude,
        }

    return {
        "address": doctor.address,
        "latitude": None,
        "longitude": None,
    }