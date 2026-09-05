from datetime import datetime
from typing import Optional
from pydantic import BaseModel, model_validator


class ConversationResponse(BaseModel):
    id: int
    patient_id: int
    doctor_id: int
    status: str
    created_at: datetime
    doctor_name: Optional[str] = None
    patient_name: Optional[str] = None

    @model_validator(mode='before')
    @classmethod
    def extract_names(cls, obj):
        # obj es el ORM object (MedicalConversation)
        if hasattr(obj, 'doctor') and obj.doctor is not None:
            user = obj.doctor  # relación -> User
            doctor_profile = getattr(user, 'doctor', None)
            if doctor_profile:
                obj.__dict__['doctor_name'] = f"{doctor_profile.first_name} {doctor_profile.last_name}"
        if hasattr(obj, 'patient') and obj.patient is not None:
            user = obj.patient  # relación -> User
            patient_profile = getattr(user, 'patient', None)
            if patient_profile:
                obj.__dict__['patient_name'] = f"{patient_profile.first_name} {patient_profile.last_name}"
        return obj

    class Config:
        from_attributes = True


class ConversationCreate(BaseModel):
    patient_id: int
    doctor_id: int

class MessageCreate(BaseModel):
    message: str


class MessageAttachmentResponse(BaseModel):
    id: int
    message_id: int
    file_name: str
    file_path: str
    file_url: str | None
    mime_type: str
    file_size: int | None
    duration: float | None
    storage_disk: str
    attachment_type: str
    created_at: datetime

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    sender_id: int
    receiver_id: int
    message: str
    is_read: bool
    read_at: datetime | None
    created_at: datetime
    attachments: list[MessageAttachmentResponse] = []

    class Config:
        from_attributes = True


class NotificationResponse(BaseModel):
    id: int
    message_id: int
    user_id: int
    type: str
    title: str
    message: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True
