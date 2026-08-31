from pydantic import BaseModel, Field
from typing import Optional
from datetime import date

class ProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    # Patient fields
    gender: Optional[str] = None
    birth_date: Optional[date] = None
    # Location fields
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class ProfileResponse(BaseModel):
    user_id: int
    email: str
    role: str
    first_name: str
    last_name: str
    # Common unique identifiers
    document_number: Optional[str] = None # For patient
    # Patient fields
    gender: Optional[str] = None
    birth_date: Optional[date] = None
    # Location fields
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    class Config:
        from_attributes = True
