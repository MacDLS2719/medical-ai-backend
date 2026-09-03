from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.models.doctor import Doctor
from app.models.user import User

router = APIRouter(
    prefix="/doctor-verification",
    tags=["Doctor Verification"]
)

class VerificationStatusUpdate(BaseModel):
    verification_status: str  # "verified", "rejected", "pending"

class DoctorVerificationDetailResponse(BaseModel):
    id: int
    user_id: int
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    residence_country: Optional[str] = None
    medical_license: str
    professional_registration_number: Optional[str] = None
    professional_college: Optional[str] = None
    college_country: Optional[str] = None
    specialty: str
    years_of_experience: Optional[int] = None
    professional_description: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    verification_status: str
    is_active: bool
    created_at: datetime
    identity_document_url: Optional[str] = None
    professional_registration_certificate_url: Optional[str] = None

    class Config:
        from_attributes = True

from sqlalchemy import or_

@router.get("/doctors", response_model=List[DoctorVerificationDetailResponse])
def get_all_doctors_for_verification(
    include_all: bool = False,
    db: Session = Depends(get_db)
):
    """
    Obtiene la lista de médicos para verificación.
    Por defecto trae los que están pendientes, vacíos o no verificados/rechazados.
    Si include_all=True, trae todos los médicos.
    """
    try:
        query = db.query(Doctor).join(User)
        if not include_all:
            query = query.filter(
                or_(
                    Doctor.verification_status == None,
                    Doctor.verification_status == "",
                    Doctor.verification_status == "pending",
                    Doctor.verification_status.notin_(["verified", "rejected"])
                )
            )
        doctors = query.all()
        results = []
        for doc in doctors:
            results.append(DoctorVerificationDetailResponse(
                id=doc.id,
                user_id=doc.user_id,
                first_name=doc.first_name,
                last_name=doc.last_name,
                email=doc.user.email if doc.user else "",
                phone=doc.phone,
                residence_country=doc.residence_country,
                medical_license=doc.medical_license,
                professional_registration_number=doc.professional_registration_number,
                professional_college=doc.professional_college,
                college_country=doc.college_country,
                specialty=doc.specialty,
                years_of_experience=doc.years_of_experience,
                professional_description=doc.professional_description,
                address=doc.address,
                city=doc.city,
                country=doc.country,
                verification_status=doc.verification_status or "pending",
                is_active=doc.is_active,
                created_at=doc.created_at,
                identity_document_url=doc.identity_document_url,
                professional_registration_certificate_url=doc.professional_registration_certificate_url
            ))
        return results
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al consultar la base de datos: {str(e)}"
        )

@router.get("/doctors/{doctor_id}", response_model=DoctorVerificationDetailResponse)
def get_doctor_for_verification(doctor_id: int, db: Session = Depends(get_db)):
    """
    Obtiene el detalle de un médico por su ID.
    """
    doc = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Médico no encontrado")
    
    return DoctorVerificationDetailResponse(
        id=doc.id,
        user_id=doc.user_id,
        first_name=doc.first_name,
        last_name=doc.last_name,
        email=doc.user.email if doc.user else "",
        phone=doc.phone,
        residence_country=doc.residence_country,
        medical_license=doc.medical_license,
        professional_registration_number=doc.professional_registration_number,
        professional_college=doc.professional_college,
        college_country=doc.college_country,
        specialty=doc.specialty,
        years_of_experience=doc.years_of_experience,
        professional_description=doc.professional_description,
        address=doc.address,
        city=doc.city,
        country=doc.country,
        verification_status=doc.verification_status or "pending",
        is_active=doc.is_active,
        created_at=doc.created_at,
        identity_document_url=doc.identity_document_url,
        professional_registration_certificate_url=doc.professional_registration_certificate_url
    )

@router.patch("/doctors/{doctor_id}/status")
def update_doctor_verification_status(
    doctor_id: int,
    payload: VerificationStatusUpdate,
    db: Session = Depends(get_db)
):
    """
    Actualiza el estado de verificación del médico (verified, rejected, pending).
    """
    valid_statuses = ["pending", "verified", "rejected"]
    if payload.verification_status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Estado inválido. Debe ser uno de: {', '.join(valid_statuses)}"
        )
    
    doc = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Médico no encontrado")

    doc.verification_status = payload.verification_status
    doc.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(doc)

    return {
        "message": f"Estado de verificación actualizado a '{doc.verification_status}'",
        "doctor_id": doc.id,
        "verification_status": doc.verification_status
    }
