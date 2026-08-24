from fastapi import APIRouter, HTTPException, Depends, Header
from sqlalchemy.orm import Session

from app.schemas.medical import (
    MedicalSearchRequest,
    MedicalSearchResponse,
)

from app.services.medical_search_service import MedicalSearchService
from app.services.pubmed_service import PubMedService
from app.services.clinical_trials_service import ClinicalTrialsService
from app.services.cochrane_service import CochraneService

from app.core.database import get_db
from app.models.user import User
from app.models.patient import Patient
from app.models.doctor import Doctor

from app.core.i18n import normalize_language


router = APIRouter(
    prefix="/api/medical",
    tags=["Medical Search"]
)


# ==========================================================
# SERVICE
# ==========================================================

def get_medical_search_service() -> MedicalSearchService:

    return MedicalSearchService(
        pubmed_service=PubMedService(),
        clinical_trials_service=ClinicalTrialsService(),
        cochrane_service=CochraneService(),
    )


# ==========================================================
# MEDICAL SEARCH
# ==========================================================

@router.post(
    "/search",
    response_model=MedicalSearchResponse
)
async def medical_search(
    request: MedicalSearchRequest,
    accept_language: str | None = Header(default=None),
    db: Session = Depends(get_db)
):

    # ======================================================
    # 1. BUSCAR USUARIO
    # ======================================================

    user = db.query(User).filter(
        User.id == request.user_id
    ).first()

    if not user:

        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # ======================================================
    # 2. DETERMINAR IDIOMA
    # ======================================================

    # PRIORIDAD:
    #
    # 1. users.language
    # 2. Accept-Language
    # 3. español

    target_lang = normalize_language(
        user.language or accept_language
    )

    print(
        "=========================================="
    )

    print(
        "MEDICAL SEARCH REQUEST"
    )

    print(
        f"USER ID: {user.id}"
    )

    print(
        f"ROLE: {user.role}"
    )

    print(
        f"USER LANGUAGE: {user.language}"
    )

    print(
        f"HEADER LANGUAGE: {accept_language}"
    )

    print(
        f"TARGET LANGUAGE: {target_lang}"
    )

    print(
        "=========================================="
    )

    # ======================================================
    # 3. CONSULTA
    # ======================================================

    query = request.query

    # ======================================================
    # 4. PACIENTE
    # ======================================================

    if user.role == "patient":

        patient = db.query(
            Patient
        ).filter(
            Patient.user_id == user.id
        ).first()

        if (
            patient
            and patient.patient_pathologies
        ):

            pathologies = [
                pp.pathology.name
                for pp in patient.patient_pathologies
                if pp.pathology
            ]

            if pathologies:

                pathology_str = " OR ".join(
                    pathologies
                )

                if query:

                    query = (
                        f"({query}) "
                        f"AND "
                        f"({pathology_str})"
                    )

                else:

                    query = pathology_str

            else:

                raise HTTPException(
                    status_code=403,
                    detail=(
                        "Patient has no registered "
                        "pathologies to search."
                    )
                )

        else:

            raise HTTPException(
                status_code=403,
                detail=(
                    "Patient has no registered "
                    "pathologies."
                )
            )

    # ======================================================
    # 5. MÉDICO
    # ======================================================

    elif user.role == "doctor":

        doctor = db.query(
            Doctor
        ).filter(
            Doctor.user_id == user.id
        ).first()

        if doctor and doctor.specialty:

            specialty_str = doctor.specialty

            if query:

                query = (
                    f"({query}) "
                    f"AND "
                    f"({specialty_str})"
                )

            else:

                query = specialty_str

        else:

            if not query:

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Doctor has no specialty "
                        "and query is empty."
                    )
                )

    # ======================================================
    # 6. OTROS USUARIOS
    # ======================================================

    else:

        if not query:

            raise HTTPException(
                status_code=400,
                detail="Query cannot be empty."
            )

    # ======================================================
    # 7. EJECUTAR BÚSQUEDA
    # ======================================================

    try:

        service = get_medical_search_service()

        result = await service.search(

            query=query,

            max_results=request.max_results,

            target_lang=target_lang

        )

        return result

    except Exception as e:

        print(
            "=========================================="
        )

        print(
            f"ERROR EN MEDICAL SEARCH: {e}"
        )

        print(
            "=========================================="
        )

        raise HTTPException(

            status_code=500,

            detail=(
                "No fue posible realizar "
                "la búsqueda médica."
            )

        )