import os
from dotenv import load_dotenv
load_dotenv()
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.deps import get_db

from app.services.medical_search_service import MedicalSearchService
from app.services.pubmed_service import PubMedService
from app.services.clinical_trials_service import ClinicalTrialsService
from app.services.cochrane_service import CochraneService

from app.services.medical_document_service import MedicalDocumentService
from app.services.medical_query_service import MedicalQueryService
from app.services.medical_response_service import MedicalResponseService
from app.services.groq_service import GroqService
from app.services.medical_rag_service import MedicalRAGService

router = APIRouter(prefix="/api/ai", tags=["AI Medical Assistant"])


class ChatRequest(BaseModel):
    prompt: str
    user_id: int
    lang: str = "es"  # idioma de la consulta del usuario


def get_medical_rag_service(db: Session = Depends(get_db)):
    medical_search_service = MedicalSearchService(
        pubmed_service=PubMedService(),
        clinical_trials_service=ClinicalTrialsService(),
        cochrane_service=CochraneService(),
    )
    return MedicalRAGService(
        db=db,
        medical_search_service=medical_search_service,
        medical_document_service=MedicalDocumentService(db),
        medical_query_service=MedicalQueryService(db),
        medical_response_service=MedicalResponseService(db),
        groq_service=GroqService()
    )


@router.post("/chat")
async def generate_response(
    request: ChatRequest,
    rag_service: MedicalRAGService = Depends(get_medical_rag_service)
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