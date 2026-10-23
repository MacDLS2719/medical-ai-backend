from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional

from app.core.database import get_db
from app.models.doctor_review import DoctorReview
from app.models.patient import Patient
from app.models.doctor import Doctor
from app.models.user import User


router = APIRouter(
    prefix="/reviews",
    tags=["Doctor Reviews"]
)


class ReviewResponse(BaseModel):
    id: int
    rating: int
    comment: Optional[str] = None
    created_at: datetime
    patient_name: str
    patient_initials: str

    class Config:
        from_attributes = True


class ReviewsSummaryResponse(BaseModel):
    total_reviews: int
    average_rating: float
    reviews: List[ReviewResponse]


class CreateReviewRequest(BaseModel):
    doctor_id: int
    patient_id: int
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


class PatientReviewResponse(BaseModel):
    id: int
    rating: int
    comment: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/{doctor_id}", response_model=ReviewsSummaryResponse)
def get_doctor_reviews(
    doctor_id: int,
    db: Session = Depends(get_db)
):
    reviews_data = db.query(DoctorReview, Patient).join(
        Patient, DoctorReview.patient_id == Patient.id
    ).filter(
        DoctorReview.doctor_id == doctor_id,
        DoctorReview.is_verified == True
    ).order_by(DoctorReview.created_at.desc()).all()

    total_rating = 0
    formatted_reviews = []

    for review, patient in reviews_data:
        total_rating += review.rating
        
        # Calculate initials
        first_initial = patient.first_name[0].upper() if patient.first_name else ""
        last_initial = patient.last_name[0].upper() if patient.last_name else ""
        
        # Calculate display name (e.g. "Laura M.")
        patient_name = f"{patient.first_name} {last_initial}." if patient.first_name else "Paciente Anónimo"

        formatted_reviews.append({
            "id": review.id,
            "rating": review.rating,
            "comment": review.comment,
            "created_at": review.created_at,
            "patient_name": patient_name,
            "patient_initials": f"{first_initial}{last_initial}",
        })

    total_reviews = len(formatted_reviews)
    average_rating = round(total_rating / total_reviews, 1) if total_reviews > 0 else 0.0

    return {
        "total_reviews": total_reviews,
        "average_rating": average_rating,
        "reviews": formatted_reviews
    }


@router.post("/", response_model=PatientReviewResponse, status_code=201)
def create_or_update_review(
    body: CreateReviewRequest,
    db: Session = Depends(get_db)
):
    """Crea o actualiza la reseña que un paciente deja sobre un médico."""

    # Verificar que el doctor existe
    doctor = db.query(Doctor).filter(Doctor.id == body.doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Médico no encontrado")

    # Verificar que el paciente existe
    patient = db.query(Patient).filter(Patient.id == body.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    # ¿Ya existe una reseña de este paciente para este médico?
    existing = db.query(DoctorReview).filter(
        DoctorReview.doctor_id == body.doctor_id,
        DoctorReview.patient_id == body.patient_id,
    ).first()

    if existing:
        existing.rating = body.rating
        existing.comment = body.comment
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing
    else:
        review = DoctorReview(
            doctor_id=body.doctor_id,
            patient_id=body.patient_id,
            rating=body.rating,
            comment=body.comment,
            status="pending",
            is_verified=False,
        )
        db.add(review)
        db.commit()
        db.refresh(review)
        return review


@router.get("/patient/{patient_id}/doctor/{doctor_id}", response_model=Optional[PatientReviewResponse])
def get_patient_review_for_doctor(
    patient_id: int,
    doctor_id: int,
    db: Session = Depends(get_db)
):
    """Devuelve la reseña (si existe) que un paciente dejó para un médico."""
    review = db.query(DoctorReview).filter(
        DoctorReview.patient_id == patient_id,
        DoctorReview.doctor_id == doctor_id,
    ).first()
    return review
