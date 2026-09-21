from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional

from app.services.rag.medical_agent_service import MedicalAgentService
from app.services.rag.medical_agent_schemas import MedicalAgentResponse, MedicalAgentResult

router = APIRouter(
    prefix="/api/medical-agent",
    tags=["Medical Agent"],
)


class MedicalAgentAskRequest(BaseModel):
    query: str = Field(..., min_length=1)
    source: Optional[str] = Field(default="all")
    language: str = Field(default="es", max_length=10)
    max_results: int = Field(default=10, ge=1, le=30)


_service: Optional[MedicalAgentService] = None


def get_service() -> MedicalAgentService:
    global _service
    if _service is None:
        _service = MedicalAgentService()
    return _service


@router.post("/ask", response_model=MedicalAgentResponse)
async def ask_medical_agent(body: MedicalAgentAskRequest):
    try:
        service = get_service()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    source_slug = (body.source or "all").strip().lower()

    source_display = (
        MedicalAgentService.ALLOWED_SOURCES.get(source_slug, "Todas las fuentes autorizadas")
        if source_slug != "all"
        else "Todas las fuentes autorizadas"
    )

    try:
        raw_results = await service.search(
            query=body.query,
            source_slug=source_slug,
            max_results=body.max_results,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar el Medical Agent: {str(exc)}",
        )

    # Convertir dicts → MedicalAgentResult
    results: List[MedicalAgentResult] = [
        MedicalAgentResult(
            source=r.get("source", source_display),
            title=r.get("title", "Sin título"),
            abstract=r.get("abstract"),
            summary=None,
            url=r.get("url"),
            published_at=r.get("published_at"),
        )
        for r in raw_results
    ]

    answer = (
        f"Se encontraron {len(results)} artículo(s) científico(s) sobre «{body.query}»"
        + (f" en {source_display}" if source_slug != "all" else "")
        + ", ordenados del más reciente al más antiguo."
        if results
        else (
            f"No se encontraron artículos sobre «{body.query}»"
            + (f" en {source_display}" if source_slug != "all" else "") + "."
        )
    )

    return MedicalAgentResponse(
        query=body.query,
        answer=answer,
        results=results,
    )


@router.get("/sources")
def list_sources():
    return {
        "sources": [
            {"id": slug, "name": name}
            for slug, name in MedicalAgentService.ALLOWED_SOURCES.items()
        ]
    }
