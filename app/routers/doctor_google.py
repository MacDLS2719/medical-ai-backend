from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import get_db
from app.models.doctor import Doctor
from app.models.doctor_google_profile import DoctorGoogleProfile
from app.models.doctor_google_image import DoctorGoogleImage

from app.schemas.doctor_google import (
    DoctorGoogleSearchRequest,
    DoctorGoogleSearchResponse,
    DoctorGoogleSaveRequest,
    DoctorGoogleProfileData,
    DoctorGoogleProfileResponse,
)

from app.services.doctor_google_search_service import (
    doctor_google_search_service,
)
from app.services.doctor_google_save_service import (
    doctor_google_save_service,
)

from app.core.auth import get_current_user


router = APIRouter(
    prefix="/doctors/google-profile",
    tags=["Doctor Google Profile"],
)


def _get_doctor_id(current_user, db: Session, target_user_id: int | None = None) -> int:
    """
    Obtiene el médico asociado al usuario autenticado o al target_user_id enviado por el cliente.
    Si estamos en desarrollo o el usuario es demo/fallback, resuelve el doctor correspondiente.
    """
    uid = target_user_id or getattr(current_user, "id", None)
    if uid is not None:
        doctor = db.query(Doctor).filter(Doctor.user_id == uid).first()
        if doctor is not None:
            return doctor.id

    if current_user and getattr(current_user, "id", None):
        doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if doctor is not None:
            return doctor.id

    # Fallback si el usuario no tiene doctor asociado aún (ej: pruebas en dev)
    first_doc = db.query(Doctor).first()
    if first_doc is not None:
        return first_doc.id

    # Si la base de datos está totalmente vacía de doctores, crear uno de soporte
    fallback_uid = uid or (current_user.id if current_user else 1)
    temp_doc = Doctor(
        user_id=fallback_uid,
        first_name="Doctor",
        last_name="General",
        specialty="Medicina General",
        is_active=True,
    )
    db.add(temp_doc)
    db.commit()
    db.refresh(temp_doc)
    return temp_doc.id



@router.post(
    "/search",
    response_model=DoctorGoogleSearchResponse,
)
async def search_google_profile(
    payload: DoctorGoogleSearchRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Busca el negocio y devuelve los datos normalizados para vista previa/edición.
    No requiere guardar de inmediato si el usuario sólo quiere previsualizar.
    """
    try:
        data = await doctor_google_search_service.search(
            google_maps_url=str(payload.google_maps_url),
        )

        try:
            profile_data = DoctorGoogleProfileData.model_validate(data)
        except ValidationError:
            # Si hay campos que no pasan validacion, limpiarlos y reintentar
            safe_data = {
                k: v for k, v in data.items()
                if k not in ("google_rating", "google_reviews_count", "latitude", "longitude")
            }
            # Convertir numericos de forma segura
            for num_field in ("google_rating", "google_reviews_count", "latitude", "longitude"):
                try:
                    val = data.get(num_field)
                    if val is not None:
                        safe_data[num_field] = float(val) if num_field in ("google_rating", "latitude", "longitude") else int(float(val))
                except (ValueError, TypeError):
                    pass
            profile_data = DoctorGoogleProfileData.model_validate(safe_data)

        return DoctorGoogleSearchResponse(
            success=True,
            message="Informacion del perfil de Google obtenida correctamente.",
            profile=profile_data,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"No fue posible consultar el negocio: {str(exc)}",
        ) from exc


@router.post(
    "",
    response_model=DoctorGoogleProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
def save_google_profile(
    payload: DoctorGoogleSaveRequest,
    user_id: int | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Guarda o actualiza el perfil del médico autenticado y actualiza su linkgoogle."""
    doctor_id = _get_doctor_id(current_user, db, user_id)

    try:
        profile = doctor_google_save_service.save_profile(
            db=db,
            doctor_id=doctor_id,
            data=payload.model_dump(mode="python"),
        )

        # También sincronizar campos en la tabla doctors
        doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
        if doctor:
            if payload.google_maps_url:
                doctor.linkgoogle = payload.google_maps_url
            if payload.formatted_address:
                doctor.address = payload.formatted_address
            if payload.phone_number:
                doctor.consultation_phone = payload.phone_number
                if not doctor.phone:
                    doctor.phone = payload.phone_number
            if payload.website_url:
                doctor.website = payload.website_url
            if payload.latitude is not None:
                try:
                    doctor.latitude = float(payload.latitude)
                except (ValueError, TypeError):
                    pass
            if payload.longitude is not None:
                try:
                    doctor.longitude = float(payload.longitude)
                except (ValueError, TypeError):
                    pass

        db.commit()
        db.refresh(profile)

        return DoctorGoogleProfileResponse.model_validate(profile)

    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"No fue posible guardar el perfil de Google: {str(exc)}",
        ) from exc


@router.get(
    "/me",
    response_model=DoctorGoogleProfileResponse,
)
def get_my_google_profile(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Consulta el perfil de Google guardado del médico autenticado."""
    doctor_id = _get_doctor_id(current_user, db)

    profile = doctor_google_save_service.get_profile(db=db, doctor_id=doctor_id)

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todavía no tienes un perfil de Google registrado.",
        )

    return DoctorGoogleProfileResponse.model_validate(profile)
