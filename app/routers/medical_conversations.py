from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.core.database import get_db

from app.schemas.medical_conversation import (
    ConversationCreate,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
    NotificationResponse
)

from app.services.medical_conversation_service import (
    MedicalConversationService
)
from app.services.audio_storage_service import AudioStorageService
from app.routers.websockets import manager as ws_manager
from datetime import datetime


router = APIRouter()


# ==========================================================
# CREAR / OBTENER CONVERSACIÓN
# ==========================================================

@router.post(
    "/conversations",
    response_model=ConversationResponse
)
def create_conversation(
    data: ConversationCreate,
    db: Session = Depends(get_db)
):

    conversation = (
        MedicalConversationService.get_or_create_conversation(
            db=db,
            patient_id=data.patient_id,
            doctor_id=data.doctor_id
        )
    )

    return conversation


# ==========================================================
# OBTENER TODAS LAS CONVERSACIONES DEL USUARIO
# ==========================================================

@router.get(
    "/conversations",
    response_model=list[ConversationResponse]
)
def get_user_conversations(
    user_id: int,
    db: Session = Depends(get_db)
):

    return MedicalConversationService.get_user_conversations(
        db=db,
        user_id=user_id
    )


# ==========================================================
# OBTENER UNA CONVERSACIÓN
# ==========================================================

@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationResponse
)
def get_conversation(
    conversation_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):

    conversation = (
        MedicalConversationService.get_conversation(
            db=db,
            conversation_id=conversation_id,
            user_id=user_id
        )
    )

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail="Conversación no encontrada"
        )

    return conversation


# ==========================================================
# ENVIAR MENSAJE
# ==========================================================

@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageResponse
)
def send_message(
    conversation_id: int,
    data: MessageCreate,
    sender_id: int,
    db: Session = Depends(get_db)
):

    message = (
        MedicalConversationService.send_message(
            db=db,
            conversation_id=conversation_id,
            sender_id=sender_id,
            message=data.message
        )
    )

    if not message:
        raise HTTPException(
            status_code=404,
            detail="Conversación no encontrada o usuario no autorizado"
        )

    return message


# ==========================================================
# VIDEOLLAMADA (JITSI MEET)
# ==========================================================

@router.post(
    "/conversations/{conversation_id}/video-call"
)
async def create_video_call(
    conversation_id: int,
    sender_id: int,
    db: Session = Depends(get_db)
):
    try:
        conversation = MedicalConversationService.get_conversation(db, conversation_id, sender_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversación no encontrada")
            
        receiver_id = conversation.doctor_id if conversation.patient_id == sender_id else conversation.patient_id
        
        timestamp = int(datetime.now().timestamp())
        room_name = f"MedicalChat-{conversation_id}-{timestamp}"
            
        await ws_manager.send_personal_message({
            "action": "INCOMING_CALL",
            "from_user": sender_id,
            "conversation_id": conversation_id,
            "room_name": room_name
        }, receiver_id)
        
        return {"status": "calling", "room_name": room_name}
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al crear videollamada: {str(e)}")


# ==========================================================
# ENVIAR AUDIO
# ==========================================================

@router.post(
    "/conversations/{conversation_id}/messages/audio",
    response_model=MessageResponse
)
async def send_audio_message(
    conversation_id: int,
    sender_id: int,
    audio: UploadFile = File(...),
    duration: float = Form(None),
    db: Session = Depends(get_db)
):
    # 1. Crear el mensaje en la base de datos con un texto genérico
    message = MedicalConversationService.send_message(
        db=db,
        conversation_id=conversation_id,
        sender_id=sender_id,
        message="[Mensaje de Voz]"
    )

    if not message:
        raise HTTPException(
            status_code=404,
            detail="Conversación no encontrada o usuario no autorizado"
        )

    # 2. Guardar el archivo de audio física/lógicamente
    audio_service = AudioStorageService()
    try:
        attachment_data = await audio_service.save_audio(audio, message.id)
    except ValueError as e:
        db.delete(message)
        db.commit()
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        db.delete(message)
        db.commit()
        raise HTTPException(
            status_code=500,
            detail=f"Error al guardar el archivo de audio: {str(e)}"
        )

    # 3. Crear el registro del attachment en la base de datos
    try:
        MedicalConversationService.create_attachment(
            db=db,
            message_id=message.id,
            attachment_data=attachment_data,
            duration=duration
        )
    except Exception as e:
        await audio_service.delete_audio(attachment_data["file_path"])
        db.delete(message)
        db.commit()
        raise HTTPException(
            status_code=500,
            detail=f"Error al registrar el adjunto de audio: {str(e)}"
        )

    return message


# ==========================================================
# OBTENER MENSAJES
# ==========================================================

@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[MessageResponse]
)
def get_messages(
    conversation_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):

    messages = (
        MedicalConversationService.get_messages(
            db=db,
            conversation_id=conversation_id,
            user_id=user_id
        )
    )

    if messages is None:
        raise HTTPException(
            status_code=404,
            detail="Conversación no encontrada o usuario no autorizado"
        )

    return messages


# ==========================================================
# MARCAR MENSAJE COMO LEÍDO
# ==========================================================

@router.patch(
    "/messages/{message_id}/read",
    response_model=MessageResponse
)
def mark_message_as_read(
    message_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):

    message = (
        MedicalConversationService.mark_message_as_read(
            db=db,
            message_id=message_id,
            user_id=user_id
        )
    )

    if not message:
        raise HTTPException(
            status_code=404,
            detail="Mensaje no encontrado"
        )

    return message


# ==========================================================
# OBTENER NOTIFICACIONES
# ==========================================================

@router.get(
    "/notifications",
    response_model=list[NotificationResponse]
)
def get_notifications(
    user_id: int,
    db: Session = Depends(get_db)
):

    return MedicalConversationService.get_notifications(
        db=db,
        user_id=user_id
    )


# ==========================================================
# MARCAR NOTIFICACIÓN COMO LEÍDA
# ==========================================================

@router.patch(
    "/notifications/{notification_id}/read",
    response_model=NotificationResponse
)
def mark_notification_as_read(
    notification_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):

    notification = (
        MedicalConversationService.mark_notification_as_read(
            db=db,
            notification_id=notification_id,
            user_id=user_id
        )
    )

    if not notification:
        raise HTTPException(
            status_code=404,
            detail="Notificación no encontrada"
        )

    return notification


# ==========================================================
# ELIMINAR CONVERSACIÓN
# ==========================================================

@router.delete(
    "/conversations/{conversation_id}"
)
def delete_conversation(
    conversation_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):

    deleted = (
        MedicalConversationService.delete_conversation(
            db=db,
            conversation_id=conversation_id,
            user_id=user_id
        )
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Conversación no encontrada o usuario no autorizado"
        )

    return {
        "message": "Conversación eliminada correctamente"
    }
