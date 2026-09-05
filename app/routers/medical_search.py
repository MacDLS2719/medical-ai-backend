import asyncio
import json
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, Header
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.services.rag.schemas import MedicalSearchRequest

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

def _extract_primary_term(query: str) -> str:
    """
    Extrae el primer término médico de una query compuesta.
    Ej: 'cáncer AND Endocrinology' → 'cáncer'
    Ej: 'diabetes OR hypertension' → 'diabetes'
    Ej: 'heart failure' → 'heart failure'
    """
    import re
    # Cortar en el primer AND / OR / NOT booleano
    term = re.split(r'\s+(?:AND|OR|NOT)\s+', query, maxsplit=1, flags=re.IGNORECASE)[0]
    # Quitar puntuación suelta al final
    term = term.strip().rstrip('.,;:')
    return term or query


async def _stream_search(
    query: str,
    sources: Optional[List[str]],
    max_results: int,
):
    """
    Ejecuta la búsqueda en paralelo en todas las fuentes seleccionadas
    y transmite los resultados de cada fuente EN CUANTO terminan,
    sin esperar a que todas las demás fuentes finalicen.

    - PubMed / Cochrane / EuropePMC / ClinicalTrials: reciben la query booleana completa.
    - OpenFDA: recibe solo el primer término médico (acepta nombres de medicamentos).
    - WHO ICTRP: deshabilitado temporalmente (API v2 devuelve 404).

    Formato de cada línea NDJSON:
        {"type": "results", "source": "pubmed",  "data": [...]}
        {"type": "error",   "source": "cochrane", "message": "..."}
    """
    from app.services.rag.librerias.pubmed_service import PubMedService
    from app.services.rag.librerias.cochrane_service import CochraneService
    from app.services.rag.librerias.clinical_trials_service import ClinicalTrialsService
    from app.services.rag.librerias.europe_pmc_service import EuropePMCService
    from app.services.rag.librerias.openfda_service import OpenFDAService
    from datetime import date, datetime

    # Término primario simple para fuentes que no soportan booleanos
    primary_term = _extract_primary_term(query)

    # Mapa de fuente → (servicio, query a usar)
    ALL_SOURCES: dict[str, tuple] = {
        "pubmed":          (PubMedService(),          query),
        "cochrane":        (CochraneService(),        query),
        "clinical_trials": (ClinicalTrialsService(),  query),
        "europe_pmc":      (EuropePMCService(),       query),
        # OpenFDA solo acepta términos simples, no booleanos
        "openfda":         (OpenFDAService(),         primary_term),
        # WHO ICTRP API v2 devuelve 404 — deshabilitado hasta que lo corrijan
        # "who_ictrp":    (WHOICTRPService(),         query),
    }

    # Si se pide una fuente concreta usar solo esa, sino todas
    active_sources = (
        {k: v for k, v in ALL_SOURCES.items() if k in sources}
        if sources
        else ALL_SOURCES
    )

    print(f"PRIMARY TERM : {primary_term!r}")
    print(f"FULL QUERY   : {query!r}")

    # Cola para recibir resultados de cada fuente en cuanto termina
    queue: asyncio.Queue = asyncio.Queue()

    def _serialize(doc) -> dict:
        if hasattr(doc, "model_dump"):
            return doc.model_dump()
        if hasattr(doc, "dict"):
            return doc.dict()
        return doc

    def _is_future(doc) -> bool:
        """Descarta documentos con fecha futura."""
        today = date.today()
        raw = getattr(doc, "publication_date", None) or getattr(doc, "date", None)
        if not raw:
            return False
        try:
            if isinstance(raw, datetime):
                return raw.date() > today
            if isinstance(raw, date):
                return raw > today
            if isinstance(raw, str):
                d = datetime.strptime(raw[:10], "%Y-%m-%d").date()
                return d > today
        except Exception:
            pass
        return False

    async def _fetch_source(source_name: str, service, source_query: str):
        """Busca en una fuente y pone el resultado en la cola."""
        try:
            results = await asyncio.wait_for(
                service.search_and_fetch(
                    query=source_query,
                    max_results=max_results,
                ),
                timeout=20.0
            )
            results = [r for r in (results or []) if not _is_future(r)]
            await queue.put(("ok", source_name, results))
        except asyncio.TimeoutError:
            await queue.put(("error", source_name, "Timeout (20s)"))
        except Exception as exc:
            await queue.put(("error", source_name, str(exc)))

    # Lanzar todas las fuentes en paralelo
    tasks = [
        asyncio.create_task(_fetch_source(name, svc, src_query))
        for name, (svc, src_query) in active_sources.items()
    ]

    total = len(tasks)
    finished = 0

    # Emitir resultados según van llegando
    while finished < total:
        kind, source_name, payload = await queue.get()
        finished += 1

        if kind == "error":
            # Solo logueamos internamente, no enviamos errores al frontend
            print(f"Source error [{source_name}]: {payload}")
        else:
            if payload:
                docs = [_serialize(d) for d in payload]
                yield json.dumps(
                    {"type": "results", "source": source_name, "data": docs},
                    ensure_ascii=False,
                    default=str,
                ) + "\n"

    # Asegurarse de que todas las tasks terminaron
    await asyncio.gather(*tasks, return_exceptions=True)



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
    raw_query: str = request.query or ""
    
    from app.services.rag.query_normalization_service import QueryNormalizationService
    normalizer = QueryNormalizationService()
    query = normalizer.clean_query(raw_query) if raw_query else ""

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
                # No usamos paréntesis duros porque rompen OpenFDA
                query = f"{query} AND {pathology_str}" if query else pathology_str
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
            query = f"{query} AND {specialty_str}" if query else specialty_str
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
