from app.models.user import User
from app.models.doctor import Doctor
from app.models.patient import Patient

from app.models.specialty import Specialty
from app.models.doctor_specialty import DoctorSpecialty

from app.models.pathology import Pathology
from app.models.patient_pathology import PatientPathology

from app.models.medical_source import MedicalSource
from app.models.medical_document import MedicalDocument
from app.models.medical_query import MedicalQuery
from app.models.medical_query_pathology import MedicalQueryPathology
from app.models.medical_query_source import MedicalQuerySource
from app.models.medical_response import MedicalResponse


__all__ = [
    "User",
    "Doctor",
    "Patient",

    "Specialty",
    "DoctorSpecialty",
    "Pathology",
    "PatientPathology",

    "MedicalSource",
    "MedicalDocument",
    "MedicalQuery",
    "MedicalQueryPathology",
    "MedicalQuerySource",
    "MedicalResponse",
]