import os
import sys
from datetime import date

# Add backend directory to sys path so we can import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal, engine
from app.core.database import Base
from app.models.user import User
from app.models.patient import Patient
from app.models.doctor import Doctor
from app.models.pathology import Pathology
from app.models.patient_pathology import PatientPathology
from app.models.specialty import Specialty
from app.models.doctor_specialty import DoctorSpecialty

def seed_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        print("Seeding pathologies and specialties...")
        # 1. Create a Pathology if none exists
        pathology = db.query(Pathology).filter_by(name="Diabetes").first()
        if not pathology:
            pathology = Pathology(name="Diabetes", description="Chronic condition affecting blood sugar.", code="E11")
            db.add(pathology)
            db.commit()
            db.refresh(pathology)

        # 2. Create a Specialty
        specialty = db.query(Specialty).filter_by(name="Endocrinology").first()
        if not specialty:
            specialty = Specialty(name="Endocrinology", description="Hormone and metabolism specialist.")
            db.add(specialty)
            db.commit()
            db.refresh(specialty)

        print("Seeding mock Patient...")
        # 3. Create mock Patient
        user_patient = db.query(User).filter_by(email="patient@mock.com").first()
        if not user_patient:
            user_patient = User(email="patient@mock.com", password_hash="nopass", role="patient", is_active=True)
            db.add(user_patient)
            db.commit()
            db.refresh(user_patient)

            patient = Patient(
                user_id=user_patient.id,
                first_name="John",
                last_name="Doe",
                document_type="ID",
                document_number="12345678",
                birth_date=date(1980, 1, 1),
                gender="Male"
            )
            db.add(patient)
            db.commit()
            db.refresh(patient)

            # Link patient to pathology
            pp = PatientPathology(patient_id=patient.id, pathology_id=pathology.id)
            db.add(pp)
            db.commit()

        print("Seeding mock Doctor...")
        # 4. Create mock Doctor
        user_doctor = db.query(User).filter_by(email="doctor@mock.com").first()
        if not user_doctor:
            user_doctor = User(email="doctor@mock.com", password_hash="nopass", role="doctor", is_active=True)
            db.add(user_doctor)
            db.commit()
            db.refresh(user_doctor)

            doctor = Doctor(
                user_id=user_doctor.id,
                first_name="Jane",
                last_name="Smith",
                medical_license="MED987654",
                specialty="Endocrinology"
            )
            db.add(doctor)
            db.commit()
            db.refresh(doctor)

            ds = DoctorSpecialty(doctor_id=doctor.id, specialty_id=specialty.id)
            db.add(ds)
            db.commit()

        print("Database seeding completed.")
        print(f"Mock Patient User ID: {user_patient.id}")
        print(f"Mock Doctor User ID: {user_doctor.id}")

    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
