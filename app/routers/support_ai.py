import logging
import uuid
from typing import List, Optional, Union
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.support_ai_conversation import SupportAIConversation
from app.models.user import User
from app.schemas.support_ai import (
    SupportAIHistoryItem,
    SupportAIHistoryResponse,
    SupportAIRequest,
    SupportAIResponse,
)
from app.services.support_ai_service import SupportAIService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/support-ai",
    tags=["Support AI"],
)

support_ai_service = SupportAIService()


def _resolve_user(db: Session, requested_user_id: Optional[int]) -> User:
    """
    Identifica y obtiene al usuario que realiza la consulta de soporte
    (sin importar si es paciente, médico o administrador).
    Si no existe o no se especificó, recurre a un usuario activo de fallback
    para garantizar la integridad referencial en la base de datos.
    """
    if requested_user_id is not None:
        user = db.query(User).filter(User.id == requested_user_id).first()
        if user:
            return user
        logger.warning(
            f"Usuario con id={requested_user_id} no encontrado en la base de datos. Buscando usuario por defecto."
        )

    # Fallback con usuarios estándar de desarrollo/demo (1: paciente, 2: médico)
    user = db.query(User).filter(User.id == 1).first()
    if not user:
        user = db.query(User).filter(User.id == 2).first()
    if not user:
        user = db.query(User).first()

    # Si la tabla users estuviera completamente vacía, creamos un usuario de soporte base
    if not user:
        logger.info("Creando usuario base para soporte técnico...")
        user = User(
            email="soporte_usuario@mivor.com",
            password_hash="nopass",
            role="patient",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return user


def _resolve_conversation_id(
    raw_conversation_id: Optional[Union[UUID, str]]
) -> UUID:
    """
    Valida y resuelve el UUID de la conversación. Si no viene uno válido, genera uno nuevo.
    """
    if not raw_conversation_id:
        return uuid.uuid4()

    if isinstance(raw_conversation_id, UUID):
        return raw_conversation_id

    try:
        return uuid.UUID(str(raw_conversation_id))
    except (ValueError, TypeError):
        logger.warning(
            f"conversation_id '{raw_conversation_id}' no es un UUID válido. Generando nuevo UUID."
        )
        return uuid.uuid4()


@router.post(
    "/chat",
    response_model=SupportAIResponse,
    status_code=status.HTTP_200_OK,
    summary="Consultar a la IA de soporte de MIVOR",
)
async def support_ai_chat(
    request: SupportAIRequest,
    db: Session = Depends(get_db),
):
    """
    Recibe una pregunta del usuario, valida el formato y la longitud del mensaje,
    consulta al asistente virtual de OpenAI y guarda la conversación (pregunta y respuesta)
    en la tabla `support_ai_conversations`, tanto para pacientes como para médicos.
    """
    clean_message = request.message.strip()

    # Validación adicional de formato y longitud
    if not clean_message:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El mensaje no puede estar vacío.",
        )

    if len(clean_message) > 4000:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La longitud del mensaje excede el límite permitido de 4000 caracteres.",
        )

    # Identificar al usuario (paciente o médico)
    target_user = _resolve_user(db, request.user_id)

    # Resolver el identificador único del hilo de conversación
    conversation_uuid = _resolve_conversation_id(request.conversation_id)

    # Cargar historial previo de la conversación para dar contexto si existe
    history = []
    try:
        previous_records = (
            db.query(SupportAIConversation)
            .filter(SupportAIConversation.conversation_id == conversation_uuid)
            .order_by(SupportAIConversation.created_at.asc())
            .limit(10)
            .all()
        )

        for record in previous_records:
            history.append({"role": "user", "content": record.question})
            history.append({"role": "assistant", "content": record.answer})
    except Exception as exc:
        logger.warning(
            f"No se pudo cargar el historial previo de conversación: {exc}"
        )

    # Comunicación con OpenAI mediante el servicio
    try:
        ai_response = await support_ai_service.ask(
            message=clean_message,
            history=history,
        )
    except RuntimeError as exc:
        logger.error(f"Error en SupportAIService al procesar consulta: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error(f"Error inesperado al generar respuesta de soporte: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al generar la respuesta de soporte.",
        ) from exc

    # Guardar la conversación y consulta en la tabla support_ai_conversations
    try:
        conversation_record = SupportAIConversation(
            user_id=target_user.id,
            conversation_id=conversation_uuid,
            question=clean_message,
            answer=ai_response,
        )
        db.add(conversation_record)
        db.commit()
        db.refresh(conversation_record)

        logger.info(
            f"Conversación guardada con éxito: ID={conversation_record.id}, "
            f"User={target_user.id} ({target_user.role}), ConvID={conversation_uuid}"
        )

        return SupportAIResponse(
            response=ai_response,
            conversation_id=str(conversation_uuid),
            id=conversation_record.id,
            user_id=conversation_record.user_id,
            created_at=conversation_record.created_at,
        )

    except Exception as exc:
        db.rollback()
        logger.error(
            f"Error al guardar la conversación de soporte en la base de datos: {exc}",
            exc_info=True,
        )
        # Si ocurre un error al persistir, devolvemos igualmente la respuesta para no bloquear al usuario
        return SupportAIResponse(
            response=ai_response,
            conversation_id=str(conversation_uuid),
            id=None,
            user_id=target_user.id,
            created_at=None,
        )


@router.get(
    "/history/{conversation_id}",
    response_model=SupportAIHistoryResponse,
    summary="Obtener el historial de una conversación con soporte",
)
def get_conversation_history(
    conversation_id: str,
    db: Session = Depends(get_db),
):
    """
    Recupera todas las interacciones (preguntas y respuestas) de un hilo de conversación.
    """
    try:
        conv_uuid = uuid.UUID(conversation_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El formato de conversation_id debe ser un UUID válido.",
        )

    records = (
        db.query(SupportAIConversation)
        .filter(SupportAIConversation.conversation_id == conv_uuid)
        .order_by(SupportAIConversation.created_at.asc())
        .all()
    )

    items = [
        SupportAIHistoryItem(
            id=rec.id,
            user_id=rec.user_id,
            conversation_id=str(rec.conversation_id),
            question=rec.question,
            answer=rec.answer,
            created_at=rec.created_at,
        )
        for rec in records
    ]

    return SupportAIHistoryResponse(
        conversation_id=str(conv_uuid),
        messages=items,
    )


@router.get(
    "/user/{user_id}",
    response_model=List[SupportAIHistoryItem],
    summary="Obtener todas las consultas de soporte de un usuario (médico o paciente)",
)
def get_user_support_conversations(
    user_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """
    Recupera las consultas realizadas por un usuario específico (paciente o médico).
    """
    records = (
        db.query(SupportAIConversation)
        .filter(SupportAIConversation.user_id == user_id)
        .order_by(SupportAIConversation.created_at.desc())
        .limit(limit)
        .all()
    )

    return [
        SupportAIHistoryItem(
            id=rec.id,
            user_id=rec.user_id,
            conversation_id=str(rec.conversation_id),
            question=rec.question,
            answer=rec.answer,
            created_at=rec.created_at,
        )
        for rec in records
    ]