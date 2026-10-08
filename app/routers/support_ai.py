from fastapi import APIRouter, HTTPException, status

from app.schemas.support_ai import (
    SupportAIRequest,
    SupportAIResponse,
)
from app.services.support_ai_service import SupportAIService


router = APIRouter(
    prefix="/support-ai",
    tags=["Support AI"],
)


support_ai_service = SupportAIService()


@router.post(
    "/chat",
    response_model=SupportAIResponse,
    status_code=status.HTTP_200_OK,
)
async def support_ai_chat(
    request: SupportAIRequest,
):
    """
    Recibe una pregunta del usuario y devuelve
    una respuesta generada por la IA de soporte de MIVOR.
    """

    try:
        response = await support_ai_service.ask(
            request.message
        )

        return SupportAIResponse(
            response=response
        )

    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc