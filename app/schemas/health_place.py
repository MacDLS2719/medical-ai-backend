import uuid
from pydantic import BaseModel

class HealthPlacePrefetch(BaseModel):
    lat: float
    lng: float
    user_id: int = 1

class HealthPlaceRead(BaseModel):
    id: uuid.UUID
    name: str | None = None
    kind: str
    lat: float
    lng: float
    address: str | None = None

    class Config:
        from_attributes = True
