from datetime import datetime
from typing import List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class SupportAIRequest(BaseModel):
    """
    Datos de entrada para la consulta a la IA de soporte de MIVOR.
    Valida formato y longitud del mensaje.
    """

    message: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="Pregunta o problema que el usuario quiere consultar al soporte de MIVOR.",
    )
    user_id: Optional[int] = Field(
        default=None,
        description="ID del usuario (paciente o médico) que realiza la consulta.",
    )
    conversation_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="ID único de conversación (UUID) para dar continuidad al hilo de chat.",
    )

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("El mensaje no puede estar vacío ni contener únicamente espacios en blanco.")
        clean_text = v.strip()
        if len(clean_text) > 4000:
            raise ValueError("El mensaje no puede exceder los 4000 caracteres.")
        return clean_text


class SupportAIResponse(BaseModel):
    """
    Respuesta que devuelve la IA de soporte de MIVOR.
    """

    response: str = Field(
        ...,
        description="Respuesta generada por la IA de soporte de MIVOR.",
    )
    conversation_id: str = Field(
        ...,
        description="Identificador UUID de la conversación guardada.",
    )
    id: Optional[int] = Field(
        default=None,
        description="ID del registro almacenado en la tabla support_ai_conversations.",
    )
    user_id: Optional[int] = Field(
        default=None,
        description="ID del usuario asociado a la consulta.",
    )
    created_at: Optional[datetime] = Field(
        default=None,
        description="Fecha y hora en que se registró la consulta.",
    )


class SupportAIHistoryItem(BaseModel):
    """
    Elemento individual del historial de una conversación con el soporte.
    """

    id: int
    user_id: int
    conversation_id: str
    question: str
    answer: str
    created_at: datetime

    class Config:
        from_attributes = True


class SupportAIHistoryResponse(BaseModel):
    """
    Historial de mensajes de una conversación.
    """

    conversation_id: str
    messages: List[SupportAIHistoryItem]