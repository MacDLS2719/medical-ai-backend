from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.models.specialty import Specialty

router = APIRouter(prefix="/metadata", tags=["metadata"])


@router.get("/specialties")
def get_specialties(db: Session = Depends(get_db)):
    specialties = db.query(Specialty).all()
    return [{"id": s.id, "name": s.name} for s in specialties]
