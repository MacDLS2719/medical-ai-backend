from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.services.search_usage_service import search_usage_service
from app.services.rag.research.medical_search_service import medical_search_service

router = APIRouter(
    prefix="/api/advanced-search",
    tags=["Advanced Medical Search"],
)


# ──────────────────────────────────────────────
# Schemas
# ──────────────────────────────────────────────

class AdvancedSearchRequest(BaseModel):
    query: str
    max_results_per_source: int = 2
    existing_references: list[dict] = Field(default_factory=list)


class AdvancedSearchResponse(BaseModel):
    summary: str
    references: list[dict]
    sources: dict[str, dict[str, int | str]] = Field(default_factory=dict)


class UsageResponse(BaseModel):
    is_pro: bool
    searches_used: int
    searches_limit: int
    searches_remaining: int


# ──────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────

@router.get("/usage", response_model=UsageResponse)
def get_usage(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Devuelve el uso diario actual del usuario.
    El frontend lo usa para mostrar / ocultar el contador y bloquear el botón.
    """
    summary = search_usage_service.get_usage_summary(user, db)
    return UsageResponse(**summary)


@router.post("/query", response_model=AdvancedSearchResponse)
async def advanced_search(
    request: AdvancedSearchRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    # Validar cuota ANTES de llamar a la IA (evita consumo innecesario)
    pro = search_usage_service.is_pro(user, db)
    sub_id = search_usage_service.get_active_subscription_id(user, db)
    usage = search_usage_service.get_or_create_today_usage(user, db, sub_id)

    if not pro and usage.search_count >= 10:
        raise HTTPException(
            status_code=403,
            detail="Has superado el límite de 10 búsquedas por día en el plan gratuito. Actualiza a PRO para continuar.",
        )

    try:
        # Llama al servicio de búsqueda avanzado (librerías + OpenAI)
        result = await medical_search_service.advanced_research_search(
            query=request.query,
            max_results_per_source=request.max_results_per_source,
        )

        # Solo se incrementa si la búsqueda fue exitosa
        usage.search_count += 1
        db.commit()

        summary = result.get("summary", "") if isinstance(result, dict) else str(result)
        references = result.get("references", []) if isinstance(result, dict) else []
        sources = result.get("sources", {}) if isinstance(result, dict) else {}

        return AdvancedSearchResponse(
            summary=summary,
            references=references,
            sources=sources,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/university-query", response_model=AdvancedSearchResponse)
async def university_search(
    request: AdvancedSearchRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Búsqueda universitaria especializada: fuentes de universidades,
    preprints académicos y centros de investigación.
    """
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    pro = search_usage_service.is_pro(user, db)
    sub_id = search_usage_service.get_active_subscription_id(user, db)
    usage = search_usage_service.get_or_create_today_usage(user, db, sub_id)

    if not pro and usage.search_count >= 10:
        raise HTTPException(
            status_code=403,
            detail="Has superado el límite de 10 búsquedas por día en el plan gratuito. Actualiza a PRO para continuar.",
        )

    try:
        result = await medical_search_service.university_research_search(
            query=request.query,
            max_results_per_source=request.max_results_per_source,
            existing_references=request.existing_references,
        )

        usage.search_count += 1
        db.commit()

        summary = result.get("summary", "") if isinstance(result, dict) else str(result)
        references = result.get("references", []) if isinstance(result, dict) else []
        sources = result.get("sources", {}) if isinstance(result, dict) else {}

        return AdvancedSearchResponse(
            summary=summary,
            references=references,
            sources=sources,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

