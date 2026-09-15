from datetime import datetime
from typing import Optional
from pydantic import BaseModel, model_validator


class ConversationResponse(BaseModel):
    id: int
    patient_id: int
    doctor_id: int
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    doctor_name: Optional[str] = None
    patient_name: Optional[str] = None
    last_message: Optional[str] = None
    last_message_sender_id: Optional[int] = None
    patient_unread_count: int = 0
    doctor_unread_count: int = 0

    @model_validator(mode='before')
    @classmethod
    def extract_names(cls, obj):
        # obj es el ORM object (MedicalConversation)
        if hasattr(obj, 'doctor') and obj.doctor is not None:
            user = obj.doctor  # relación -> User
            doctor_profile = getattr(user, 'doctor', None)
            patient_profile = getattr(user, 'patient', None)
            if doctor_profile:
                obj.__dict__['doctor_name'] = f"Dr. {doctor_profile.first_name} {doctor_profile.last_name}"
            elif patient_profile:
                obj.__dict__['doctor_name'] = f"{patient_profile.first_name} {patient_profile.last_name}"
            else:
                obj.__dict__['doctor_name'] = getattr(user, 'email', 'Médico')

        if hasattr(obj, 'patient') and obj.patient is not None:
            user = obj.patient  # relación -> User
            patient_profile = getattr(user, 'patient', None)
            doctor_profile = getattr(user, 'doctor', None)
            if patient_profile:
                obj.__dict__['patient_name'] = f"{patient_profile.first_name} {patient_profile.last_name}"
            elif doctor_profile:
                obj.__dict__['patient_name'] = f"Dr. {doctor_profile.first_name} {doctor_profile.last_name}"
            else:
                obj.__dict__['patient_name'] = getattr(user, 'email', 'Paciente')

        if hasattr(obj, 'messages') and obj.messages:
            sorted_msgs = sorted(obj.messages, key=lambda m: m.created_at or datetime.min)
            if sorted_msgs:
                last_msg = sorted_msgs[-1]
                obj.__dict__['last_message'] = last_msg.message
                obj.__dict__['last_message_sender_id'] = last_msg.sender_id
                
            patient_unread = sum(1 for m in obj.messages if m.receiver_id == obj.patient_id and not m.is_read)
            doctor_unread = sum(1 for m in obj.messages if m.receiver_id == obj.doctor_id and not m.is_read)
            obj.__dict__['patient_unread_count'] = patient_unread
            obj.__dict__['doctor_unread_count'] = doctor_unread

        obj.__dict__['updated_at'] = getattr(obj, 'updated_at', obj.created_at)
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
