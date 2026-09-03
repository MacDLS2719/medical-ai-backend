import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_db

from app.services.rag.medical_rag_service import MedicalRAGService
from app.services.rag.medical_search_orchestrator import MedicalSearchOrchestrator
from app.services.rag.query_normalization_service import QueryNormalizationService
from app.services.rag.result_presenter_service import ResultPresenterService
from app.services.rag.datos.medical_document_service import MedicalDocumentService
from app.services.rag.datos.medical_query_service import MedicalQueryService
from app.services.rag.datos.medical_response_service import MedicalResponseService
from app.services.rag.groq_service import GroqService


router = APIRouter(prefix="/api/ai", tags=["AI Medical Assistant"])


class ChatRequest(BaseModel):
    prompt: str
    user_id: int
    lang: str = "es"


def get_medical_rag_service(db: Session = Depends(get_db)):
    return MedicalRAGService(
        db=db,
        query_normalization_service=QueryNormalizationService(),
        medical_search_orchestrator=MedicalSearchOrchestrator(),
        result_presenter_service=ResultPresenterService(),
        medical_document_service=MedicalDocumentService(db),
        medical_query_service=MedicalQueryService(db),
        medical_response_service=MedicalResponseService(db),
        groq_service=GroqService(),
    )


@router.post("/chat")
async def generate_response(
    request: ChatRequest,
    rag_service: MedicalRAGService = Depends(get_medical_rag_service),
):
    try:
        result = await rag_service.generate_response(
            user_id=request.user_id,
            query=request.prompt,
            query_type="general",
            max_results=5,
            lang=request.lang,
        )
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar la solicitud con RAG: {str(e)}"
        )
