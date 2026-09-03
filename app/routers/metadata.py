from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.models.pathology import Pathology
from app.models.specialty import Specialty

router = APIRouter(prefix="/metadata", tags=["metadata"])


@router.get("/pathologies")
def get_pathologies(db: Session = Depends(get_db)):
    pathologies = db.query(Pathology).all()
    return [{"id": p.id, "name": p.name, "description": p.description} for p in pathologies]


@router.get("/specialties")
def get_specialties(db: Session = Depends(get_db)):
    specialties = db.query(Specialty).all()
    return [{"id": s.id, "name": s.name} for s in specialties]
