from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
import logging

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
from app.services.cloudinary_service import cloudinary_service
from app.services.daily_service import create_daily_room, delete_daily_room
from app.routers.websockets import manager as ws_manager
from datetime import datetime

logger = logging.getLogger(__name__)

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
# OBTENER CONTACTOS DISPONIBLES PARA CHAT (SEGÚN ROL)
# ==========================================================

@router.get(
    "/conversations/contacts"
)
def get_available_contacts(
    current_user_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    from app.models.user import User
    from app.models.doctor import Doctor
    from app.models.patient import Patient
    from sqlalchemy import or_

    result = []
    seen_user_ids = set()

    if current_user_id:
        seen_user_ids.add(current_user_id)

    # 1. Obtener todos los médicos registrados
    doctors = db.query(Doctor).join(
        User, Doctor.user_id == User.id
    ).filter(
        or_(User.is_active == True, User.is_active.is_(None)),
        or_(Doctor.is_active == True, Doctor.is_active.is_(None))
    ).order_by(Doctor.first_name).all()

    for d in doctors:
        if d.user_id not in seen_user_ids:
            seen_user_ids.add(d.user_id)
            result.append({
                "id": d.id,
                "user_id": d.user_id,
                "first_name": d.first_name,
                "last_name": d.last_name,
                "full_name": f"Dr. {d.first_name} {d.last_name}",
                "role": "doctor",
                "specialty": d.specialty or "Medicina General",
                "country": d.country,
                "city": d.city,
                "address": d.address,
                "professional_description": d.professional_description,
                "verification_status": d.verification_status,
            })

    # También buscar usuarios con role='doctor' que no estén en la tabla Doctor aún
    doctor_users = db.query(User).filter(
        User.role.ilike("doctor"),
        or_(User.is_active == True, User.is_active.is_(None))
    ).all()

    for u in doctor_users:
        if u.id not in seen_user_ids:
            seen_user_ids.add(u.id)
            name_part = u.email.split("@")[0].capitalize()
            result.append({
                "id": u.id,
                "user_id": u.id,
                "first_name": name_part,
                "last_name": "",
                "full_name": f"Dr. {name_part}",
                "role": "doctor",
                "specialty": "Médico Registrado",
                "country": None,
                "city": None,
                "address": None,
                "professional_description": None,
                "verification_status": "active",
            })

    # 2. Obtener todos los pacientes registrados
    patients = db.query(Patient).join(
        User, Patient.user_id == User.id
    ).filter(
        or_(User.is_active == True, User.is_active.is_(None))
    ).order_by(Patient.first_name).all()

    for p in patients:
        if p.user_id not in seen_user_ids:
            seen_user_ids.add(p.user_id)
            result.append({
                "id": p.id,
                "user_id": p.user_id,
                "first_name": p.first_name,
                "last_name": p.last_name,
                "full_name": f"{p.first_name} {p.last_name}",
                "role": "patient",
                "document_number": p.document_number,
                "gender": p.gender,
                "address": p.address,
                "specialty": "Paciente",
            })

    # También buscar usuarios con role='patient'
    patient_users = db.query(User).filter(
        User.role.ilike("patient"),
        or_(User.is_active == True, User.is_active.is_(None))
    ).all()

    for u in patient_users:
        if u.id not in seen_user_ids:
            seen_user_ids.add(u.id)
            name_part = u.email.split("@")[0].capitalize()
            result.append({
                "id": u.id,
                "user_id": u.id,
                "first_name": name_part,
                "last_name": "",
                "full_name": u.email,
                "role": "patient",
                "document_number": None,
                "gender": None,
                "address": None,
                "specialty": "Paciente",
            })

    return result


@router.get(
    "/conversations/doctors"
)
def get_available_doctors_for_chat(
    current_user_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    return get_available_contacts(current_user_id=current_user_id, db=db)


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

# ==========================================================
# VIDEOLLAMADA (DAILY.CO)
# ==========================================================

@router.post(
    "/conversations/{conversation_id}/video-call"
)
async def create_video_call(
    conversation_id: int,
    sender_id: int = Query(None),
    sender_id_form: int = Form(None, alias="sender_id"),
    db: Session = Depends(get_db)
):
    actual_sender_id = sender_id if sender_id is not None else sender_id_form
    if actual_sender_id is None:
        raise HTTPException(status_code=400, detail="El parámetro sender_id es requerido.")

    try:
        conversation = MedicalConversationService.get_conversation(db, conversation_id, actual_sender_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversación no encontrada")

        receiver_id = conversation.doctor_id if conversation.patient_id == actual_sender_id else conversation.patient_id

        # Obtener nombre del emisor
        from app.models.user import User
        caller_user = db.query(User).filter(User.id == actual_sender_id).first()
        caller_name = "Usuario"
        if caller_user:
            if caller_user.doctor:
                caller_name = f"Dr. {caller_user.doctor.first_name} {caller_user.doctor.last_name}"
            elif caller_user.patient:
                caller_name = f"{caller_user.patient.first_name} {caller_user.patient.last_name}"
            else:
                caller_name = caller_user.email

        # Crear sala real en Daily.co
        timestamp = int(datetime.now().timestamp())
        room_name = f"medicalchat-{conversation_id}-{timestamp}"
        daily_room = await create_daily_room(room_name)
        room_url = daily_room.get("url")   # URL lista para abrir en iframe
        room_name_final = daily_room.get("name", room_name)

        # Notificar al receptor vía WebSocket
        await ws_manager.send_personal_message({
            "action": "INCOMING_CALL",
            "from_user": actual_sender_id,
            "caller_name": caller_name,
            "conversation_id": conversation_id,
            "room_name": room_name_final,
            "room_url": room_url
        }, receiver_id)

        return {
            "status": "calling",
            "room_name": room_name_final,
            "room_url": room_url
        }
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Error al crear videollamada: {str(e)}", exc_info=True)
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
    sender_id: int = Query(None),
    sender_id_form: int = Form(None, alias="sender_id"),
    audio: UploadFile = File(...),
    duration: float = Form(None),
    db: Session = Depends(get_db)
):
    actual_sender_id = sender_id if sender_id is not None else sender_id_form
    if actual_sender_id is None:
        raise HTTPException(
            status_code=400,
            detail="El parámetro sender_id es requerido."
        )

    # 1. Crear el mensaje en la base de datos con un texto genérico
    message = MedicalConversationService.send_message(
        db=db,
        conversation_id=conversation_id,
        sender_id=actual_sender_id,
        message="[Mensaje de Voz]"
    )

    if not message:
        raise HTTPException(
            status_code=404,
            detail="Conversación no encontrada o usuario no autorizado"
        )

    # 2. Guardar el archivo de audio en Cloudinary en carpeta por conversation_id
    folder_path = f"medical_conversations/{conversation_id}"
    try:
        await audio.seek(0)
        cloudinary_details = await cloudinary_service.upload_file_with_details(
            file=audio,
            folder=folder_path,
            resource_type="video"
        )
        attachment_data = {
            "file_name": audio.filename or "audio.webm",
            "file_path": cloudinary_details.get("public_id", ""),
            "file_url": cloudinary_details.get("secure_url", ""),
            "mime_type": audio.content_type or cloudinary_details.get("mime_type", "audio/webm"),
            "file_size": cloudinary_details.get("file_size", 0),
            "storage_disk": "cloudinary",
            "attachment_type": "audio",
        }
    except Exception as e:
        logger.error(f"Error al guardar audio en Cloudinary: {str(e)}", exc_info=True)
        db.delete(message)
        db.commit()
        raise HTTPException(
            status_code=500,
            detail=f"Error al guardar el archivo de audio en Cloudinary: {str(e)}"
        )

    # 3. Crear el registro del attachment en la base de datos
    try:
        MedicalConversationService.create_attachment(
            db=db,
            message_id=message.id,
            attachment_data=attachment_data,
            duration=duration
        )
        db.refresh(message)
    except Exception as e:
        logger.error(f"Error al registrar adjunto de audio: {str(e)}", exc_info=True)
        cloudinary_service.delete_file(attachment_data["file_path"], resource_type="video")
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
