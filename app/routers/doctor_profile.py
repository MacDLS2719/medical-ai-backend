from datetime import datetime
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    Form,
)
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.auth import get_current_user

from app.models.user import User
from app.models.doctor import Doctor
from app.models.doctor_education import DoctorEducation
from app.models.doctor_media import DoctorMedia
from app.models.specialty import Specialty
from app.models.doctor_specialty import DoctorSpecialty

from app.schemas.doctor_profile import (
    DoctorProfileResponse,
    DoctorProfileUpdate,
    DoctorEducationCreate,
    DoctorEducationUpdate,
    DoctorEducationResponse,
    DoctorMediaResponse,
    DoctorCreateRequest,
    DoctorFreeCreateRequest,
    SubscriptionPlanResponse,
)

from app.models.subscription_plan import SubscriptionPlan
from app.models.doctor_subscription import DoctorSubscription

from app.services.cloudinary_service import cloudinary_service


router = APIRouter(
    prefix="/doctor-profile",
    tags=["Doctor Profile"]
)


# ==========================================================
# SUBSCRIPTION PLANS - LIST ACTIVE PLANS
# ==========================================================


@router.get("/subscription-plans", response_model=list[SubscriptionPlanResponse])
def list_subscription_plans(db: Session = Depends(get_db)):
    """
    Retorna todos los planes de suscripción activos para mostrarlos
    al médico durante el proceso de registro.
    """
    plans = (
        db.query(SubscriptionPlan)
        .filter(SubscriptionPlan.is_active == True)
        .order_by(SubscriptionPlan.price)
        .all()
    )
    return plans


@router.post("/upgrade-subscription")
def upgrade_subscription(
    data: dict,
    db: Session = Depends(get_db),
):
    """
    Permite a un doctor existente cambiar (mejorar) su plan de suscripción.
    Recibe: { user_id: int, plan_id: int }
    """
    user_id = data.get("user_id")
    plan_id = data.get("plan_id")

    if not user_id or not plan_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id y plan_id son requeridos",
        )

    # Verificar que el plan existe y está activo
    plan = (
        db.query(SubscriptionPlan)
        .filter(SubscriptionPlan.id == plan_id, SubscriptionPlan.is_active == True)
        .first()
    )
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan de suscripción no encontrado o inactivo",
        )

    # Obtener el doctor asociado al user_id
    doctor = (
        db.query(Doctor)
        .filter(Doctor.user_id == user_id)
        .first()
    )
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor no encontrado",
        )

    # Actualizar suscripción activa o crear una nueva
    existing_sub = (
        db.query(DoctorSubscription)
        .filter(
            DoctorSubscription.doctor_id == doctor.id,
            DoctorSubscription.status == "active",
        )
        .first()
    )

    if existing_sub:
        existing_sub.subscription_plan_id = plan.id
        existing_sub.updated_at = datetime.utcnow()
    else:
        new_sub = DoctorSubscription(
            doctor_id=doctor.id,
            subscription_plan_id=plan.id,
            status="active",
        )
        db.add(new_sub)

    db.commit()
    return {"success": True, "message": f"Plan actualizado a '{plan.name}'", "plan_id": plan.id}


@router.post(
    "/register",
    response_model=DoctorProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_doctor(
    data: DoctorCreateRequest,
    db: Session = Depends(get_db),
):
    """
    Registra un nuevo médico en la plataforma.
    Crea el usuario, el perfil de doctor y su especialidad.
    """
    # 1. Validar si el correo ya existe
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un usuario registrado con este correo electrónico",
        )

    # 2. Validar si la licencia médica ya existe
    existing_license = db.query(Doctor).filter(Doctor.medical_license == data.medical_license).first()
    if existing_license:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un médico registrado con esta licencia médica",
        )

    # 3. Crear usuario
    new_user = User(
        email=data.email,
        password_hash=data.password or "nopass",
        role="doctor",
        language=data.language or "es",
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # 4. Crear doctor
    new_doctor = Doctor(
        user_id=new_user.id,
        first_name=data.first_name,
        last_name=data.last_name,
        date_of_birth=data.date_of_birth,
        residence_country=data.residence_country,
        medical_license=data.medical_license,
        professional_registration_number=data.professional_registration_number,
        professional_college=data.professional_college,
        college_country=data.college_country,
        specialty=data.specialty,
        phone=data.phone,
        experience=data.experience,
        years_of_experience=data.years_of_experience,
        address=data.address,
        city=data.city,
        country=data.country,
        postal_code=data.postal_code,
        latitude=data.latitude,
        longitude=data.longitude,
        website=data.website,
        professional_description=data.professional_description,
        consultation_phone=data.consultation_phone,
        data_policy_accepted=True,
        data_policy_accepted_at=datetime.utcnow(),
        is_active=True,
    )
    db.add(new_doctor)
    db.commit()
    db.refresh(new_doctor)

    # 5. Asociar o crear Especialidad
    try:
        specialty_record = db.query(Specialty).filter(Specialty.name.ilike(data.specialty.strip())).first()
        if not specialty_record:
            specialty_record = Specialty(
                name=data.specialty.strip(),
                description=f"Especialidad médica: {data.specialty.strip()}"
            )
            db.add(specialty_record)
            db.commit()
            db.refresh(specialty_record)

        doctor_spec = DoctorSpecialty(
            doctor_id=new_doctor.id,
            specialty_id=specialty_record.id,
            is_primary=True
        )
        db.add(doctor_spec)
        db.commit()
    except Exception as e:
        db.rollback()
        # Si falla la especialidad, el doctor ya se creó correctamente

    return get_doctor_profile(
        current_user=new_user,
        doctor=new_doctor,
    )


@router.post(
    "/register/free",
    response_model=DoctorProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_free_doctor(
    data: DoctorFreeCreateRequest,
    db: Session = Depends(get_db),
):
    """
    Registra un nuevo médico en la plataforma con el plan gratuito.
    """
    # 1. Validar si el correo ya existe
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un usuario registrado con este correo electrónico",
        )

    # 2. Validar si la licencia médica / colegiado ya existe
    # Usamos professional_registration_number como medical_license internamente
    existing_license = db.query(Doctor).filter(Doctor.medical_license == data.professional_registration_number).first()
    if existing_license:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un médico registrado con este número de colegiado",
        )

    # 3. Crear usuario
    new_user = User(
        email=data.email,
        password_hash=data.password or "nopass",
        role="doctor",
        language=data.language or "es",
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # 4. Crear doctor
    new_doctor = Doctor(
        user_id=new_user.id,
        first_name=data.first_name,
        last_name=data.last_name,
        residence_country=data.residence_country,
        professional_registration_number=data.professional_registration_number,
        medical_license=data.professional_registration_number,  # mapped from colegiado
        specialty=data.specialty,
        phone=data.phone,
        data_policy_accepted=True,
        data_policy_accepted_at=datetime.utcnow(),
        is_active=True,
    )
    db.add(new_doctor)
    db.commit()
    db.refresh(new_doctor)

    # 5. Asociar o crear Especialidad
    try:
        specialty_record = db.query(Specialty).filter(Specialty.name.ilike(data.specialty.strip())).first()
        if not specialty_record:
            specialty_record = Specialty(
                name=data.specialty.strip(),
                description=f"Especialidad médica: {data.specialty.strip()}"
            )
            db.add(specialty_record)
            db.commit()
            db.refresh(specialty_record)

        doctor_spec = DoctorSpecialty(
            doctor_id=new_doctor.id,
            specialty_id=specialty_record.id,
            is_primary=True
        )
        db.add(doctor_spec)
        db.commit()
    except Exception as e:
        db.rollback()

    # 6. Asignar suscripción al plan seleccionado (o al gratuito si no se indicó)
    selected_plan = None

    # Intentar usar el plan elegido por el médico
    if data.subscription_plan_id:
        selected_plan = (
            db.query(SubscriptionPlan)
            .filter(
                SubscriptionPlan.id == data.subscription_plan_id,
                SubscriptionPlan.is_active == True,
            )
            .first()
        )

    # Si no se encontró el plan elegido, usar el plan gratuito
    if not selected_plan:
        selected_plan = (
            db.query(SubscriptionPlan)
            .filter(SubscriptionPlan.is_free == True, SubscriptionPlan.is_active == True)
            .first()
        )

    # Si tampoco existe plan gratuito en la BD, crear uno de fallback
    if not selected_plan:
        selected_plan = SubscriptionPlan(
            name="Free Plan",
            slug="free-plan",
            description="Plan gratuito básico",
            price=0.00,
            currency="USD",
            billing_interval="month",
            is_free=True,
            is_active=True,
        )
        db.add(selected_plan)
        db.commit()
        db.refresh(selected_plan)

    new_subscription = DoctorSubscription(
        doctor_id=new_doctor.id,
        subscription_plan_id=selected_plan.id,
        status="active",
    )
    db.add(new_subscription)
    db.commit()

    return get_doctor_profile(
        current_user=new_user,
        doctor=new_doctor,
    )



# ==========================================================
# DEPENDENCIA - DOCTOR ACTUAL
# ==========================================================


def get_current_doctor(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Obtiene el perfil del doctor asociado al usuario autenticado.
    """

    if current_user.role != "doctor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors can access this endpoint",
        )

    doctor = (
        db.query(Doctor)
        .filter(Doctor.user_id == current_user.id)
        .first()
    )

    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor profile not found",
        )

    return doctor


# ==========================================================
# GET DOCTOR PROFILE
# ==========================================================


@router.get(
    "",
    response_model=DoctorProfileResponse,
)
def get_doctor_profile(
    current_user: User = Depends(get_current_user),
    doctor: Doctor = Depends(get_current_doctor),
):
    """
    Obtiene el perfil completo del doctor.
    """

    profile_data = {
        # --------------------------------------------------
        # USER
        # --------------------------------------------------

        "user_id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,

        # --------------------------------------------------
        # DATOS PERSONALES
        # --------------------------------------------------

        "first_name": doctor.first_name,
        "last_name": doctor.last_name,
        "date_of_birth": doctor.date_of_birth,
        "residence_country": doctor.residence_country,
        "phone": doctor.phone,

        # --------------------------------------------------
        # IDENTIFICACIÓN PROFESIONAL
        # --------------------------------------------------

        "medical_license": doctor.medical_license,
        "identity_document_url": doctor.identity_document_url,

        # --------------------------------------------------
        # COLEGIACIÓN
        # --------------------------------------------------

        "professional_registration_number": (
            doctor.professional_registration_number
        ),

        "professional_college": (
            doctor.professional_college
        ),

        "college_country": (
            doctor.college_country
        ),

        "professional_registration_certificate_url": (
            doctor.professional_registration_certificate_url
        ),

        # --------------------------------------------------
        # INFORMACIÓN PROFESIONAL
        # --------------------------------------------------

        "specialty": doctor.specialty,
        "bio": doctor.professional_description or doctor.experience,
        "experience": doctor.experience,
        "years_of_experience": doctor.years_of_experience,
        "professional_description": doctor.professional_description,

        # --------------------------------------------------
        # UBICACIÓN
        # --------------------------------------------------

        "address": doctor.address,
        "country": doctor.country,
        "city": doctor.city,
        "postal_code": doctor.postal_code,
        "latitude": doctor.latitude,
        "longitude": doctor.longitude,

        # --------------------------------------------------
        # INFORMACIÓN DE CONSULTA
        # --------------------------------------------------

        "consultation_phone": doctor.consultation_phone,
        "website": doctor.website,

        # --------------------------------------------------
        # POLÍTICA DE DATOS
        # --------------------------------------------------

        "data_policy_accepted": doctor.data_policy_accepted,
        "data_policy_accepted_at": doctor.data_policy_accepted_at,
        "verification_status": getattr(doctor, "verification_status", "pending"),


        # --------------------------------------------------
        # RELACIONES
        # --------------------------------------------------

        "educations": doctor.educations,
        "media": doctor.media,
    }

    return profile_data


# ==========================================================
# UPDATE DOCTOR PROFILE
# ==========================================================


@router.put(
    "",
    response_model=DoctorProfileResponse,
)
def update_doctor_profile(
    profile_update: DoctorProfileUpdate,
    current_user: User = Depends(get_current_user),
    doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    """
    Actualiza la información general del perfil del doctor.
    """

    update_data = profile_update.model_dump(
        exclude_unset=True
    )

    # ------------------------------------------------------
    # POLÍTICA DE DATOS
    # ------------------------------------------------------

    if "data_policy_accepted" in update_data:

        accepted = update_data["data_policy_accepted"]

        if accepted:
            doctor.data_policy_accepted = True

            # Si todavía no tiene fecha de aceptación,
            # registramos la fecha actual.
            if not doctor.data_policy_accepted_at:
                doctor.data_policy_accepted_at = datetime.utcnow()

        else:
            doctor.data_policy_accepted = False
            doctor.data_policy_accepted_at = None

        del update_data["data_policy_accepted"]

    # ------------------------------------------------------
    # CAMPOS DEL PERFIL
    # ------------------------------------------------------

    for key, value in update_data.items():

        if hasattr(doctor, key):
            setattr(
                doctor,
                key,
                value
            )

    db.commit()
    db.refresh(doctor)

    return get_doctor_profile(
        current_user=current_user,
        doctor=doctor,
    )


# ==========================================================
# ADD EDUCATION
# ==========================================================


@router.post(
    "/education",
    response_model=DoctorEducationResponse,
)
def add_education(
    education_data: DoctorEducationCreate,
    doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    """
    Agrega una formación académica al perfil del doctor.
    """

    # ------------------------------------------------------
    # VALIDACIÓN DE AÑOS
    # ------------------------------------------------------

    if (
        education_data.start_year is not None
        and education_data.end_year is not None
        and education_data.end_year < education_data.start_year
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End year cannot be earlier than start year",
        )

    # ------------------------------------------------------
    # CREAR EDUCACIÓN
    # ------------------------------------------------------

    new_education = DoctorEducation(
        doctor_id=doctor.id,
        **education_data.model_dump(),
    )

    db.add(new_education)
    db.commit()
    db.refresh(new_education)

    return new_education


# ==========================================================
# UPDATE EDUCATION
# ==========================================================


@router.put(
    "/education/{education_id}",
    response_model=DoctorEducationResponse,
)
def update_education(
    education_id: int,
    education_data: DoctorEducationUpdate,
    doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    """
    Actualiza una formación académica del doctor.
    """

    education = (
        db.query(DoctorEducation)
        .filter(
            DoctorEducation.id == education_id,
            DoctorEducation.doctor_id == doctor.id,
        )
        .first()
    )

    if not education:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Education record not found",
        )

    update_data = education_data.model_dump(
        exclude_unset=True
    )

    # ------------------------------------------------------
    # VALIDAR AÑOS
    # ------------------------------------------------------

    start_year = update_data.get(
        "start_year",
        education.start_year,
    )

    end_year = update_data.get(
        "end_year",
        education.end_year,
    )

    if (
        start_year is not None
        and end_year is not None
        and end_year < start_year
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End year cannot be earlier than start year",
        )

    # ------------------------------------------------------
    # ACTUALIZAR
    # ------------------------------------------------------

    for key, value in update_data.items():
        setattr(
            education,
            key,
            value,
        )

    db.commit()
    db.refresh(education)

    return education


# ==========================================================
# DELETE EDUCATION
# ==========================================================


@router.delete(
    "/education/{education_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_education(
    education_id: int,
    doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    """
    Elimina una formación académica.
    """

    education = (
        db.query(DoctorEducation)
        .filter(
            DoctorEducation.id == education_id,
            DoctorEducation.doctor_id == doctor.id,
        )
        .first()
    )

    if not education:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Education record not found",
        )

    db.delete(education)
    db.commit()

    return None


# ==========================================================
# UPLOAD MEDIA
# ==========================================================


@router.post(
    "/media",
    response_model=DoctorMediaResponse,
)
async def upload_media(
    media_type: str = Form(...),
    file: UploadFile = File(...),
    doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    """
    Sube archivos multimedia del perfil del doctor a Cloudinary.

    Ejemplos de media_type:

    profile_picture
    gallery
    certificate
    additional_document
    professional_image
    """

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File name is required",
        )

    directory_path = f"doctors/doctor_{doctor.id}"

    try:

        file_url = await cloudinary_service.upload_file(
            file,
            folder=directory_path,
        )

    except Exception as e:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file to Cloudinary: {str(e)}",
        )

    new_media = DoctorMedia(
        doctor_id=doctor.id,
        media_type=media_type,
        file_url=file_url,
        file_name=file.filename,
        mime_type=file.content_type,
    )

    db.add(new_media)
    db.commit()
    db.refresh(new_media)

    return new_media


# ==========================================================
# DELETE MEDIA
# ==========================================================


@router.delete(
    "/media/{media_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_media(
    media_id: int,
    doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    """
    Elimina un archivo multimedia del doctor de Cloudinary y de la base de datos.
    """

    media = (
        db.query(DoctorMedia)
        .filter(
            DoctorMedia.id == media_id,
            DoctorMedia.doctor_id == doctor.id,
        )
        .first()
    )

    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media record not found",
        )

    # ------------------------------------------------------
    # ELIMINAR DE CLOUDINARY
    # ------------------------------------------------------

    try:

        cloudinary_service.delete_file(
            media.file_url
        )

    except Exception:
        # No impedimos eliminar el registro de BD
        # si el archivo ya no existe en Cloudinary.
        pass

    # ------------------------------------------------------
    # ELIMINAR REGISTRO
    # ------------------------------------------------------

    db.delete(media)
    db.commit()

    return None
