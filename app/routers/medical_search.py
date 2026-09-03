import json
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, Header
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.services.rag.schemas import MedicalSearchRequest
from app.services.rag.medical_search_orchestrator import MedicalSearchOrchestrator

from app.core.database import get_db
from app.models.user import User
from app.models.patient import Patient
from app.models.doctor import Doctor
from app.core.i18n import normalize_language


router = APIRouter(
    prefix="/api/medical",
    tags=["Medical Search"],
)


# ==============================================================
# MAPEO DE FUENTES: frontend  →  orchestrator
# ==============================================================
#
# El frontend envía strings simples como 'europepmc', 'whoictrp'
# o 'clinicaltrials'.  El orchestrador usa sus propias claves
# internas: 'europe_pmc', 'who_ictrp', 'clinical_trials'.

SOURCE_MAP: dict[str, str] = {
    "pubmed": "pubmed",
    "cochrane": "cochrane",
    "europepmc": "europe_pmc",
    "europe_pmc": "europe_pmc",
    "openfda": "openfda",
    "open_fda": "openfda",
    "whoictrp": "who_ictrp",
    "who_ictrp": "who_ictrp",
    "clinicaltrials": "clinical_trials",
    "clinical_trials": "clinical_trials",
}


def _resolve_sources(source: Optional[str]) -> Optional[List[str]]:
    """
    Convierte el valor de `source` enviado por el frontend
    en la lista de fuentes que entiende el orchestrador.

    'all' o None  →  None  (buscar en todas las fuentes)
    'pubmed'      →  ['pubmed']
    'europepmc'   →  ['europe_pmc']
    (etc.)
    """
    if not source or source.strip().lower() == "all":
        return None

    key = source.strip().lower()
    mapped = SOURCE_MAP.get(key)

    if mapped is None:
        # Fuente desconocida → buscar en todas por seguridad
        return None

    return [mapped]


# ==============================================================
# GENERADOR DE STREAMING (NDJSON)
# ==============================================================

async def _stream_search(
    query: str,
    sources: Optional[List[str]],
    max_results: int,
):
    """
    Ejecuta la búsqueda en el orchestrador y transmite los
    resultados como NDJSON línea a línea.

    Formato de cada línea:
        {"type": "results", "data": [...]}
        {"type": "error",   "source": "pubmed", "message": "..."}
    """
    orchestrator = MedicalSearchOrchestrator()

    try:
        result = await orchestrator.search(
            query=query,
            sources=sources,
            max_results=max_results,
        )

        errors: dict = result.get("errors", {})
        all_results: list = result.get("results", [])

        # ----------------------------------------------------------
        # Emitir errores por fuente (si los hay)
        # ----------------------------------------------------------
        for source_name, error_msg in errors.items():
            yield json.dumps(
                {
                    "type": "error",
                    "source": source_name,
                    "message": error_msg,
                },
                ensure_ascii=False,
            ) + "\n"

        # ----------------------------------------------------------
        # Emitir los resultados
        # ----------------------------------------------------------
        if all_results:
            docs = []
            for doc in all_results:
                if hasattr(doc, "model_dump"):
                    docs.append(doc.model_dump())
                elif hasattr(doc, "dict"):
                    docs.append(doc.dict())
                else:
                    docs.append(doc)

            yield json.dumps(
                {"type": "results", "data": docs},
                ensure_ascii=False,
                default=str,
            ) + "\n"

    except Exception as exc:
        yield json.dumps(
            {
                "type": "error",
                "source": "orchestrator",
                "message": str(exc),
            },
            ensure_ascii=False,
        ) + "\n"


# ==============================================================
# ENDPOINT PRINCIPAL: POST /api/medical/search
# ==============================================================

@router.post("/search")
async def medical_search(
    request: MedicalSearchRequest,
    accept_language: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    # ----------------------------------------------------------
    # 1. USUARIO
    # ----------------------------------------------------------
    user = db.query(User).filter(User.id == request.user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # ----------------------------------------------------------
    # 2. IDIOMA
    # ----------------------------------------------------------
    target_lang = normalize_language(user.language or accept_language)

    print("==========================================")
    print("MEDICAL SEARCH REQUEST")
    print(f"USER ID   : {user.id}")
    print(f"ROLE      : {user.role}")
    print(f"LANGUAGE  : {target_lang}")
    print(f"SOURCE    : {request.source}")
    print(f"QUERY     : {request.query!r}")
    print("==========================================")

    # ----------------------------------------------------------
    # 3. CONSTRUIR QUERY SEGÚN ROL
    # ----------------------------------------------------------
    query: str = request.query or ""

    if user.role == "patient":
        patient = (
            db.query(Patient)
            .filter(Patient.user_id == user.id)
            .first()
        )

        if patient and patient.patient_pathologies:
            pathologies = [
                pp.pathology.name
                for pp in patient.patient_pathologies
                if pp.pathology
            ]

            if pathologies:
                pathology_str = " OR ".join(pathologies)
                query = (
                    f"({query}) AND ({pathology_str})"
                    if query
                    else pathology_str
                )
            else:
                raise HTTPException(
                    status_code=403,
                    detail="Patient has no registered pathologies to search.",
                )
        else:
            raise HTTPException(
                status_code=403,
                detail="Patient has no registered pathologies.",
            )

    elif user.role == "doctor":
        doctor = (
            db.query(Doctor)
            .filter(Doctor.user_id == user.id)
            .first()
        )

        if doctor and doctor.specialty:
            specialty_str = doctor.specialty
            query = (
                f"({query}) AND ({specialty_str})"
                if query
                else specialty_str
            )
        else:
            if not query:
                raise HTTPException(
                    status_code=400,
                    detail="Doctor has no specialty and query is empty.",
                )

    else:
        if not query:
            raise HTTPException(
                status_code=400,
                detail="Query cannot be empty.",
            )

    # ----------------------------------------------------------
    # 4. RESOLVER FUENTES
    # ----------------------------------------------------------
    sources = _resolve_sources(request.source)

    print(f"FINAL QUERY: {query!r}")
    print(f"SOURCES    : {sources}")
    print("==========================================")

    # ----------------------------------------------------------
    # 5. STREAMING
    # ----------------------------------------------------------
    return StreamingResponse(
        _stream_search(
            query=query,
            sources=sources,
            max_results=request.max_results,
        ),
        media_type="application/x-ndjson",
    )
