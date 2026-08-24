from datetime import datetime
from pydantic import BaseModel


class ConversationCreate(BaseModel):
    patient_id: int
    doctor_id: int


class ConversationResponse(BaseModel):
    id: int
    patient_id: int
    doctor_id: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    message: str


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    sender_id: int
    receiver_id: int
    message: str
    is_read: bool
    read_at: datetime | None
    created_at: datetime

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