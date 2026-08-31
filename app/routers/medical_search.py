from fastapi import APIRouter, HTTPException, Depends, Header
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.schemas.medical import (
    MedicalSearchRequest,
    MedicalSearchResponse,
)

from app.services.medical_search_service import MedicalSearchService
from app.services.pubmed_service import PubMedService
from app.services.clinical_trials_service import ClinicalTrialsService
from app.services.cochrane_service import CochraneService
from app.services.europe_pmc_service import EuropePMCService
from app.services.who_ictrp_service import WHOICTRPService

# Nuevos servicios por categoría
from app.services.evidence_search_service import EvidenceSearchService
from app.services.trials_search_service import TrialsSearchService
from app.services.drug_search_service import DrugSearchService

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
        europe_pmc_service=EuropePMCService(),
        who_ictrp_service=WHOICTRPService()
    )


# ==========================================================
# MEDICAL SEARCH
# ==========================================================

@router.post(
    "/search"
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
        "MEDICAL SEARCH REQUEST (STREAMING)"
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

        return StreamingResponse(
            service.search_stream(
                query=query,
                max_results=request.max_results,
                target_lang=target_lang
            ),
            media_type="application/x-ndjson"
        )

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


# ==============================================================
# EVIDENCIA CIENTÍFICA: PubMed + Cochrane + Europe PMC
# ==============================================================

@router.post("/search/evidence")
async def search_evidence(
    request: MedicalSearchRequest,
    accept_language: str | None = Header(default=None),
    db: Session = Depends(get_db)
):
    """
    Búsqueda en evidencia científica (artículos y revisiones):
      - PubMed
      - Cochrane
      - Europe PMC

    Acepta lenguaje natural amplio (ej: 'artículos sobre diabetes tipo 2').
    El servicio limpia stopwords y traduce la consulta automáticamente.
    """
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    from app.core.i18n import normalize_language
    target_lang = normalize_language(user.language or accept_language)

    query = request.query or ""

    # Enriquecer query con contexto del usuario si aplica
    if user.role == "patient" and not query:
        patient = db.query(Patient).filter(Patient.user_id == user.id).first()
        if patient and patient.patient_pathologies:
            pathologies = [
                pp.pathology.name
                for pp in patient.patient_pathologies
                if pp.pathology
            ]
            if pathologies:
                query = " OR ".join(pathologies)
    elif user.role == "doctor" and not query:
        doctor = db.query(Doctor).filter(Doctor.user_id == user.id).first()
        if doctor and doctor.specialty:
            query = doctor.specialty

    if not query:
        raise HTTPException(
            status_code=400,
            detail="Se requiere una consulta de búsqueda."
        )

    try:
        service = EvidenceSearchService()
        return await service.search(
            query=query,
            max_results=request.max_results,
            target_lang=target_lang,
        )
    except Exception as e:
        print(f"Error en evidence search: {e}")
        raise HTTPException(
            status_code=500,
            detail="No fue posible realizar la búsqueda de evidencia científica."
        )


# ==============================================================
# ENSAYOS CLÍNICOS: ClinicalTrials + WHO ICTRP
# ==============================================================

@router.post("/search/trials")
async def search_trials(
    request: MedicalSearchRequest,
    accept_language: str | None = Header(default=None),
    db: Session = Depends(get_db)
):
    """
    Búsqueda en registros de ensayos clínicos:
      - ClinicalTrials.gov
      - WHO ICTRP

    Acepta lenguaje natural (ej: 'ensayos sobre hipertensión en adultos mayores').
    El servicio limpia stopwords y traduce la consulta automáticamente.
    """
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    from app.core.i18n import normalize_language
    target_lang = normalize_language(user.language or accept_language)

    query = request.query or ""

    # Enriquecer query con contexto del usuario si aplica
    if user.role == "patient" and not query:
        patient = db.query(Patient).filter(Patient.user_id == user.id).first()
        if patient and patient.patient_pathologies:
            pathologies = [
                pp.pathology.name
                for pp in patient.patient_pathologies
                if pp.pathology
            ]
            if pathologies:
                query = " OR ".join(pathologies)
    elif user.role == "doctor" and not query:
        doctor = db.query(Doctor).filter(Doctor.user_id == user.id).first()
        if doctor and doctor.specialty:
            query = doctor.specialty

    if not query:
        raise HTTPException(
            status_code=400,
            detail="Se requiere una consulta de búsqueda."
        )

    try:
        service = TrialsSearchService()
        return await service.search(
            query=query,
            max_results=request.max_results,
            target_lang=target_lang,
        )
    except Exception as e:
        print(f"Error en trials search: {e}")
        raise HTTPException(
            status_code=500,
            detail="No fue posible realizar la búsqueda de ensayos clínicos."
        )


# ==============================================================
# MEDICAMENTOS: openFDA
# ==============================================================

@router.post("/search/drugs")
async def search_drugs(
    request: MedicalSearchRequest,
    accept_language: str | None = Header(default=None),
    db: Session = Depends(get_db)
):
    """
    Búsqueda de medicamentos en openFDA por nombre genérico o de marca.
      Ej: 'ibuprofen', 'ibuprofeno', 'metformin', 'aspirina'

    A diferencia de la búsqueda de artículos, aquí el query debe ser
    el nombre (o parte del nombre) del medicamento. El servicio traduce
    automáticamente de español a inglés antes de consultar openFDA.
    """
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    from app.core.i18n import normalize_language
    target_lang = normalize_language(user.language or accept_language)

    query = (request.query or "").strip()
    if not query:
        raise HTTPException(
            status_code=400,
            detail="Se requiere el nombre del medicamento a buscar."
        )

    try:
        service = DrugSearchService()
        return await service.search(
            query=query,
            max_results=request.max_results,
            target_lang=target_lang,
        )
    except Exception as e:
        print(f"Error en drug search: {e}")
        raise HTTPException(
            status_code=500,
            detail="No fue posible realizar la búsqueda de medicamentos."
        )
