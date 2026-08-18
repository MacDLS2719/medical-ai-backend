from fastapi import APIRouter, HTTPException, Depends
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

router = APIRouter(
    prefix="/api/medical",
    tags=["Medical Search"]
)

def get_medical_search_service() -> MedicalSearchService:
    return MedicalSearchService(
        pubmed_service=PubMedService(),
        clinical_trials_service=ClinicalTrialsService(),
        cochrane_service=CochraneService(),
    )

@router.post(
    "/search",
    response_model=MedicalSearchResponse
)
async def medical_search(
    request: MedicalSearchRequest,
    db: Session = Depends(get_db)
):
    service = get_medical_search_service()
    
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    query = request.query
    if user.role == "patient":
        patient = db.query(Patient).filter(Patient.user_id == user.id).first()
        if patient and patient.patient_pathologies:
            pathologies = [pp.pathology.name for pp in patient.patient_pathologies if pp.pathology]
            if pathologies:
                pathology_str = " OR ".join(pathologies)
                if query:
                    query = f"({query}) AND ({pathology_str})"
                else:
                    query = pathology_str
            else:
                raise HTTPException(status_code=403, detail="Patient has no registered pathologies to search.")
        else:
            raise HTTPException(status_code=403, detail="Patient has no registered pathologies.")
    else:
        if not query:
            raise HTTPException(status_code=400, detail="Query cannot be empty for non-patients.")

    try:
        result = await service.search(
            query=query,
            max_results=request.max_results
        )
        # Note: Depending on service.search return type, you may need to wrap it in a dictionary if it isn't already a dict/model that matches MedicalSearchResponse
        # e.g., return {"results": result} if result is a list
        if isinstance(result, list):
            return {"results": result}
        return result
    except Exception as e:
        print(f"Error en búsqueda médica: {e}")
        raise HTTPException(
            status_code=500,
            detail="No fue posible realizar la búsqueda médica."
        )