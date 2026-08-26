from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.patient import Patient
from app.models.doctor import Doctor
from app.schemas.profile import ProfileResponse, ProfileUpdate

router = APIRouter(prefix="/profile", tags=["Profile"])

@router.get("", response_model=ProfileResponse)
def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile_data = {
        "user_id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
    }

    if current_user.role == "patient":
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if patient:
            profile_data.update({
                "first_name": patient.first_name,
                "last_name": patient.last_name,
                "document_number": patient.document_number,
                "gender": patient.gender,
                "birth_date": patient.birth_date,
                "address": patient.address,
                "latitude": patient.latitude,
                "longitude": patient.longitude,
            })
    elif current_user.role == "doctor":
        doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if doctor:
            profile_data.update({
                "first_name": doctor.first_name,
                "last_name": doctor.last_name,
                "medical_license": doctor.medical_license,
                "specialty": doctor.specialty,
                "address": doctor.address,
                "latitude": doctor.latitude,
                "longitude": doctor.longitude,
            })
    
    if "first_name" not in profile_data:
        raise HTTPException(status_code=404, detail="Profile details not found for this user.")

    return profile_data


@router.put("", response_model=ProfileResponse)
def update_profile(
    profile_update: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role == "patient":
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient profile not found.")
        
        if profile_update.first_name is not None:
            patient.first_name = profile_update.first_name
        if profile_update.last_name is not None:
            patient.last_name = profile_update.last_name
        if profile_update.gender is not None:
            patient.gender = profile_update.gender
        if profile_update.birth_date is not None:
            patient.birth_date = profile_update.birth_date
        if profile_update.address is not None:
            patient.address = profile_update.address
        if profile_update.latitude is not None:
            patient.latitude = profile_update.latitude
        if profile_update.longitude is not None:
            patient.longitude = profile_update.longitude

    elif current_user.role == "doctor":
        doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor profile not found.")
        
        if profile_update.first_name is not None:
            doctor.first_name = profile_update.first_name
        if profile_update.last_name is not None:
            doctor.last_name = profile_update.last_name
        if profile_update.specialty is not None:
            doctor.specialty = profile_update.specialty
        if profile_update.address is not None:
            doctor.address = profile_update.address
        if profile_update.latitude is not None:
            doctor.latitude = profile_update.latitude
        if profile_update.longitude is not None:
            doctor.longitude = profile_update.longitude
            
    db.commit()
    
    # Return updated profile by calling get_profile logic or just fetching again
    return get_profile(current_user=current_user, db=db)
