from pydantic import BaseModel

class MedicalAlertCreate(BaseModel):
    user_id: int
    name: str
    topic: str
    info_type: str
    frequency: str
    source: str
    is_active: bool

class MedicalAlertUpdate(BaseModel):
    is_active: bool
