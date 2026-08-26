"""
Seed de 20 médicos de prueba para Medical AI.

Distribución
------------

Colombia: 10
    Eje Cafetero: 6
        - Manizales: 2
        - Pereira: 2
        - Armenia: 2

    Resto de Colombia: 4
        - Bogotá: 1
        - Medellín: 1
        - Cali: 1
        - Barranquilla: 1

Estados Unidos: 4
    - Miami
    - New York
    - Houston
    - Los Angeles

Europa: 6
    - España: 3
        - Madrid: 2
        - Barcelona: 1
    - Francia: 1
    - Alemania: 1
    - Italia: 1

Ejecutar desde:

    backend/

con:

    python scripts/seed_doctors.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError


# ==========================================================
# AGREGAR BACKEND AL PATH
# ==========================================================

BACKEND_DIR = Path(__file__).resolve().parents[1]

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ==========================================================
# IMPORTS DEL PROYECTO
# ==========================================================

from app.core.database import SessionLocal
from app.models.user import User
from app.models.doctor import Doctor


# ==========================================================
# CONFIGURACIÓN
# ==========================================================

DEFAULT_PASSWORD_HASH = (
    "$2b$12$LQv3c1yqBWJ2h6K"
    "QkR8O0e9J4k2Qh5m8vY0u"
    "Q0d5z0h7Jw3mX6n9pK4sO"
)

DOCTOR_ROLE = "doctor"

DEFAULT_LANGUAGE = "es"


# ==========================================================
# MÉDICOS
# ==========================================================

DOCTORS = [

    # ======================================================
    # COLOMBIA - EJE CAFETERO
    # ======================================================

    {
        "first_name": "Carlos",
        "last_name": "Ramírez",
        "email": "carlos.ramirez.medicalai@example.com",
        "medical_license": "COL-CAF-0001",
        "specialty": "Cardiología",
        "country": "Colombia",
        "city": "Manizales",
        "address": "Carrera 23 # 48-12, Manizales, Caldas",
        "latitude": 5.0689,
        "longitude": -75.5174,
    },

    {
        "first_name": "Laura",
        "last_name": "Gómez",
        "email": "laura.gomez.medicalai@example.com",
        "medical_license": "COL-CAF-0002",
        "specialty": "Endocrinología",
        "country": "Colombia",
        "city": "Manizales",
        "address": "Carrera 25 # 52-30, Manizales, Caldas",
        "latitude": 5.0703,
        "longitude": -75.5131,
    },

    {
        "first_name": "Andrés",
        "last_name": "Martínez",
        "email": "andres.martinez.medicalai@example.com",
        "medical_license": "COL-CAF-0003",
        "specialty": "Neurología",
        "country": "Colombia",
        "city": "Pereira",
        "address": "Carrera 7 # 22-45, Pereira, Risaralda",
        "latitude": 4.8143,
        "longitude": -75.6946,
    },

    {
        "first_name": "Valentina",
        "last_name": "Torres",
        "email": "valentina.torres.medicalai@example.com",
        "medical_license": "COL-CAF-0004",
        "specialty": "Pediatría",
        "country": "Colombia",
        "city": "Pereira",
        "address": "Avenida Circunvalar # 8-25, Pereira, Risaralda",
        "latitude": 4.8133,
        "longitude": -75.6875,
    },

    {
        "first_name": "Juan",
        "last_name": "Herrera",
        "email": "juan.herrera.medicalai@example.com",
        "medical_license": "COL-CAF-0005",
        "specialty": "Oncología",
        "country": "Colombia",
        "city": "Armenia",
        "address": "Carrera 14 # 9-35, Armenia, Quindío",
        "latitude": 4.5339,
        "longitude": -75.6811,
    },

    {
        "first_name": "Natalia",
        "last_name": "Morales",
        "email": "natalia.morales.medicalai@example.com",
        "medical_license": "COL-CAF-0006",
        "specialty": "Dermatología",
        "country": "Colombia",
        "city": "Armenia",
        "address": "Avenida Bolívar # 18-42, Armenia, Quindío",
        "latitude": 4.5389,
        "longitude": -75.6728,
    },

    # ======================================================
    # COLOMBIA - RESTO DEL PAÍS
    # ======================================================

    {
        "first_name": "Sebastián",
        "last_name": "Castro",
        "email": "sebastian.castro.medicalai@example.com",
        "medical_license": "COL-0007",
        "specialty": "Medicina Interna",
        "country": "Colombia",
        "city": "Bogotá",
        "address": "Carrera 13 # 85-20, Bogotá",
        "latitude": 4.7110,
        "longitude": -74.0721,
    },

    {
        "first_name": "Camila",
        "last_name": "Rodríguez",
        "email": "camila.rodriguez.medicalai@example.com",
        "medical_license": "COL-0008",
        "specialty": "Ginecología",
        "country": "Colombia",
        "city": "Medellín",
        "address": "Carrera 43A # 10-15, Medellín",
        "latitude": 6.2442,
        "longitude": -75.5812,
    },

    {
        "first_name": "Daniel",
        "last_name": "Vargas",
        "email": "daniel.vargas.medicalai@example.com",
        "medical_license": "COL-0009",
        "specialty": "Ortopedia",
        "country": "Colombia",
        "city": "Cali",
        "address": "Calle 5 # 38-20, Cali",
        "latitude": 3.4516,
        "longitude": -76.5320,
    },

    {
        "first_name": "Mariana",
        "last_name": "López",
        "email": "mariana.lopez.medicalai@example.com",
        "medical_license": "COL-0010",
        "specialty": "Neumología",
        "country": "Colombia",
        "city": "Barranquilla",
        "address": "Carrera 51B # 80-90, Barranquilla",
        "latitude": 10.9878,
        "longitude": -74.7889,
    },

    # ======================================================
    # ESTADOS UNIDOS
    # ======================================================

    {
        "first_name": "James",
        "last_name": "Anderson",
        "email": "james.anderson.medicalai@example.com",
        "medical_license": "USA-0001",
        "specialty": "Cardiology",
        "country": "United States",
        "city": "Miami",
        "address": "Brickell Avenue, Miami, FL",
        "latitude": 25.7617,
        "longitude": -80.1918,
    },

    {
        "first_name": "Emily",
        "last_name": "Johnson",
        "email": "emily.johnson.medicalai@example.com",
        "medical_license": "USA-0002",
        "specialty": "Neurology",
        "country": "United States",
        "city": "New York",
        "address": "Manhattan, New York, NY",
        "latitude": 40.7128,
        "longitude": -74.0060,
    },

    {
        "first_name": "Michael",
        "last_name": "Brown",
        "email": "michael.brown.medicalai@example.com",
        "medical_license": "USA-0003",
        "specialty": "Oncology",
        "country": "United States",
        "city": "Houston",
        "address": "Texas Medical Center, Houston, TX",
        "latitude": 29.7604,
        "longitude": -95.3698,
    },

    {
        "first_name": "Sophia",
        "last_name": "Williams",
        "email": "sophia.williams.medicalai@example.com",
        "medical_license": "USA-0004",
        "specialty": "Pediatrics",
        "country": "United States",
        "city": "Los Angeles",
        "address": "Downtown Los Angeles, CA",
        "latitude": 34.0522,
        "longitude": -118.2437,
    },

    # ======================================================
    # ESPAÑA
    # ======================================================

    {
        "first_name": "Alejandro",
        "last_name": "Fernández",
        "email": "alejandro.fernandez.medicalai@example.com",
        "medical_license": "ESP-0001",
        "specialty": "Cardiología",
        "country": "Spain",
        "city": "Madrid",
        "address": "Calle de Alcalá, Madrid",
        "latitude": 40.4168,
        "longitude": -3.7038,
    },

    {
        "first_name": "Lucía",
        "last_name": "Martínez",
        "email": "lucia.martinez.medicalai@example.com",
        "medical_license": "ESP-0002",
        "specialty": "Endocrinología",
        "country": "Spain",
        "city": "Madrid",
        "address": "Paseo de la Castellana, Madrid",
        "latitude": 40.4520,
        "longitude": -3.6880,
    },

    {
        "first_name": "Pablo",
        "last_name": "Sánchez",
        "email": "pablo.sanchez.medicalai@example.com",
        "medical_license": "ESP-0003",
        "specialty": "Neurología",
        "country": "Spain",
        "city": "Barcelona",
        "address": "Eixample, Barcelona",
        "latitude": 41.3874,
        "longitude": 2.1686,
    },

    # ======================================================
    # FRANCIA
    # ======================================================

    {
        "first_name": "Pierre",
        "last_name": "Dubois",
        "email": "pierre.dubois.medicalai@example.com",
        "medical_license": "FRA-0001",
        "specialty": "Cardiologie",
        "country": "France",
        "city": "Paris",
        "address": "Avenue des Champs-Élysées, Paris",
        "latitude": 48.8566,
        "longitude": 2.3522,
    },

    # ======================================================
    # ALEMANIA
    # ======================================================

    {
        "first_name": "Anna",
        "last_name": "Schmidt",
        "email": "anna.schmidt.medicalai@example.com",
        "medical_license": "DEU-0001",
        "specialty": "Dermatologie",
        "country": "Germany",
        "city": "Berlin",
        "address": "Mitte, Berlin",
        "latitude": 52.5200,
        "longitude": 13.4050,
    },

    # ======================================================
    # ITALIA
    # ======================================================

    {
        "first_name": "Marco",
        "last_name": "Rossi",
        "email": "marco.rossi.medicalai@example.com",
        "medical_license": "ITA-0001",
        "specialty": "Oncologia",
        "country": "Italy",
        "city": "Rome",
        "address": "Centro Storico, Rome",
        "latitude": 41.9028,
        "longitude": 12.4964,
    },
]


# ==========================================================
# CREAR / OBTENER USER
# ==========================================================

def get_or_create_user(
    db,
    doctor_data: dict,
) -> tuple[User, bool]:

    email = doctor_data["email"].lower().strip()

    user = db.execute(
        select(User).where(
            User.email == email
        )
    ).scalar_one_or_none()

    if user:
        return user, False

    user = User(
        email=email,
        password_hash=DEFAULT_PASSWORD_HASH,
        role=DOCTOR_ROLE,
        language=DEFAULT_LANGUAGE,
        is_active=True,
    )

    db.add(user)
    db.flush()

    return user, True


# ==========================================================
# CREAR / ACTUALIZAR DOCTOR
# ==========================================================

def get_or_create_doctor(
    db,
    doctor_data: dict,
    user: User,
) -> tuple[Doctor, bool]:

    doctor = db.execute(
        select(Doctor).where(
            Doctor.medical_license
            == doctor_data["medical_license"]
        )
    ).scalar_one_or_none()

    if doctor:

        doctor.user_id = user.id
        doctor.first_name = doctor_data["first_name"]
        doctor.last_name = doctor_data["last_name"]
        doctor.specialty = doctor_data["specialty"]
        doctor.address = doctor_data["address"]
        doctor.latitude = doctor_data["latitude"]
        doctor.longitude = doctor_data["longitude"]
        doctor.is_active = True

        return doctor, False

    doctor = Doctor(
        user_id=user.id,
        first_name=doctor_data["first_name"],
        last_name=doctor_data["last_name"],
        medical_license=doctor_data["medical_license"],
        specialty=doctor_data["specialty"],
        address=doctor_data["address"],
        latitude=doctor_data["latitude"],
        longitude=doctor_data["longitude"],
        is_active=True,
    )

    db.add(doctor)
    db.flush()

    return doctor, True


# ==========================================================
# MAIN
# ==========================================================

def main():

    print()
    print("=" * 70)
    print("MEDICAL AI - SEED DE MÉDICOS")
    print("=" * 70)
    print()

    print(
        f"Total de médicos a procesar: {len(DOCTORS)}"
    )
    print()

    db = SessionLocal()

    created_users = 0
    existing_users = 0

    created_doctors = 0
    updated_doctors = 0

    errors = []

    try:

        for index, doctor_data in enumerate(
            DOCTORS,
            start=1,
        ):

            full_name = (
                f"{doctor_data['first_name']} "
                f"{doctor_data['last_name']}"
            )

            print(
                f"[{index:02d}/{len(DOCTORS)}] "
                f"{full_name} - "
                f"{doctor_data['city']}, "
                f"{doctor_data['country']}"
            )

            try:

                # --------------------------------------------------
                # USER
                # --------------------------------------------------

                user, user_created = (
                    get_or_create_user(
                        db,
                        doctor_data,
                    )
                )

                if user_created:

                    created_users += 1

                    print(
                        f"    Usuario creado: ID {user.id}"
                    )

                else:

                    existing_users += 1

                    print(
                        f"    Usuario existente: ID {user.id}"
                    )

                # --------------------------------------------------
                # DOCTOR
                # --------------------------------------------------

                doctor, doctor_created = (
                    get_or_create_doctor(
                        db,
                        doctor_data,
                        user,
                    )
                )

                if doctor_created:

                    created_doctors += 1

                    print(
                        f"    Médico creado: ID {doctor.id}"
                    )

                else:

                    updated_doctors += 1

                    print(
                        f"    Médico actualizado: ID {doctor.id}"
                    )

                print(
                    f"    Especialidad: "
                    f"{doctor.specialty}"
                )

                print(
                    f"    Coordenadas: "
                    f"{doctor.latitude}, "
                    f"{doctor.longitude}"
                )

                print(
                    f"    Rol: {user.role}"
                )

                print()

            except IntegrityError as exc:

                db.rollback()

                error_message = str(exc.orig)

                errors.append({
                    "doctor": full_name,
                    "error": error_message,
                })

                print(
                    f"    ERROR DE INTEGRIDAD: "
                    f"{error_message}"
                )

                print()

            except Exception as exc:

                db.rollback()

                errors.append({
                    "doctor": full_name,
                    "error": str(exc),
                })

                print(
                    f"    ERROR: {exc}"
                )

                print()

        # ======================================================
        # COMMIT
        # ======================================================

        db.commit()

        print()
        print("=" * 70)
        print("PROCESO TERMINADO")
        print("=" * 70)
        print()

        print(
            f"Usuarios creados:       {created_users}"
        )

        print(
            f"Usuarios existentes:    {existing_users}"
        )

        print(
            f"Médicos creados:        {created_doctors}"
        )

        print(
            f"Médicos actualizados:   {updated_doctors}"
        )

        print(
            f"Errores:                {len(errors)}"
        )

        print()

        # ======================================================
        # ERRORES
        # ======================================================

        if errors:

            print("=" * 70)
            print("DETALLE DE ERRORES")
            print("=" * 70)

            for error in errors:

                print(
                    f"- {error['doctor']}: "
                    f"{error['error']}"
                )

            print()

        else:

            print(
                "Todos los médicos fueron procesados "
                "correctamente."
            )

        print()

    except Exception:

        db.rollback()

        raise

    finally:

        db.close()


# ==========================================================
# EJECUTAR
# ==========================================================

if __name__ == "__main__":
    main()