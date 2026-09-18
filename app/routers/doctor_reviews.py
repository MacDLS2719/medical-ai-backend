from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

from app.core.database import get_db
from app.models.doctor_review import DoctorReview
from app.models.patient import Patient
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


@router.get("/{doctor_id}", response_model=ReviewsSummaryResponse)
def get_doctor_reviews(
    doctor_id: int,
    db: Session = Depends(get_db)
):
    reviews_data = db.query(DoctorReview, Patient).join(
        Patient, DoctorReview.patient_id == Patient.id
    ).filter(
        DoctorReview.doctor_id == doctor_id,
        DoctorReview.is_published == True
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
