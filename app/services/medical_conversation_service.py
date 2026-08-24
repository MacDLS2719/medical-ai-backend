from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.models.medical_conversation import MedicalConversation
from app.models.medical_message import MedicalMessage
from app.models.medical_message_notification import MedicalMessageNotification


class MedicalConversationService:

    # ==========================================================
    # CREAR / OBTENER CONVERSACIÓN
    # ==========================================================

    @staticmethod
    def get_or_create_conversation(
        db: Session,
        patient_id: int,
        doctor_id: int
    ):

        conversation = db.query(MedicalConversation).filter(
            and_(
                MedicalConversation.patient_id == patient_id,
                MedicalConversation.doctor_id == doctor_id
            )
        ).first()

        if conversation:
            return conversation

        conversation = MedicalConversation(
            patient_id=patient_id,
            doctor_id=doctor_id,
            status="active"
        )

        db.add(conversation)
        db.commit()
        db.refresh(conversation)

        return conversation

    # ==========================================================
    # OBTENER TODAS LAS CONVERSACIONES DEL USUARIO
    # ==========================================================

    @staticmethod
    def get_user_conversations(
        db: Session,
        user_id: int
    ):

        return db.query(
            MedicalConversation
        ).filter(
            or_(
                MedicalConversation.patient_id == user_id,
                MedicalConversation.doctor_id == user_id
            )
        ).order_by(
            MedicalConversation.updated_at.desc()
        ).all()

    # ==========================================================
    # OBTENER UNA CONVERSACIÓN
    # ==========================================================

    @staticmethod
    def get_conversation(
        db: Session,
        conversation_id: int,
        user_id: int
    ):

        return db.query(
            MedicalConversation
        ).filter(
            MedicalConversation.id == conversation_id,
            or_(
                MedicalConversation.patient_id == user_id,
                MedicalConversation.doctor_id == user_id
            )
        ).first()

    # ==========================================================
    # ENVIAR MENSAJE
    # ==========================================================

    @staticmethod
    def send_message(
        db: Session,
        conversation_id: int,
        sender_id: int,
        message: str
    ):

        conversation = db.query(
            MedicalConversation
        ).filter(
            MedicalConversation.id == conversation_id,
            or_(
                MedicalConversation.patient_id == sender_id,
                MedicalConversation.doctor_id == sender_id
            )
        ).first()

        if not conversation:
            return None

        # Determinar receptor
        if conversation.patient_id == sender_id:
            receiver_id = conversation.doctor_id
        else:
            receiver_id = conversation.patient_id

        # Crear mensaje
        medical_message = MedicalMessage(
            conversation_id=conversation_id,
            sender_id=sender_id,
            receiver_id=receiver_id,
            message=message,
            is_read=False
        )

        db.add(medical_message)

        # Necesitamos el ID del mensaje
        db.flush()

        # Crear notificación
        notification = MedicalMessageNotification(
            message_id=medical_message.id,
            user_id=receiver_id,
            type="new_message",
            title="Nuevo mensaje médico",
            message="Has recibido un nuevo mensaje."
        )

        db.add(notification)

        # Actualizar conversación
        conversation.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(medical_message)

        return medical_message

    # ==========================================================
    # OBTENER MENSAJES
    # ==========================================================

    @staticmethod
    def get_messages(
        db: Session,
        conversation_id: int,
        user_id: int
    ):

        conversation = (
            MedicalConversationService.get_conversation(
                db=db,
                conversation_id=conversation_id,
                user_id=user_id
            )
        )

        if not conversation:
            return None

        return db.query(
            MedicalMessage
        ).filter(
            MedicalMessage.conversation_id == conversation_id
        ).order_by(
            MedicalMessage.created_at.asc()
        ).all()

    # ==========================================================
    # MARCAR MENSAJE COMO LEÍDO
    # ==========================================================

    @staticmethod
    def mark_message_as_read(
        db: Session,
        message_id: int,
        user_id: int
    ):

        message = db.query(
            MedicalMessage
        ).filter(
            MedicalMessage.id == message_id,
            MedicalMessage.receiver_id == user_id
        ).first()

        if not message:
            return None

        message.is_read = True
        message.read_at = datetime.utcnow()

        notification = db.query(
            MedicalMessageNotification
        ).filter(
            MedicalMessageNotification.message_id == message_id,
            MedicalMessageNotification.user_id == user_id,
            MedicalMessageNotification.is_read == False
        ).first()

        if notification:
            notification.is_read = True

        db.commit()
        db.refresh(message)

        return message

    # ==========================================================
    # OBTENER NOTIFICACIONES
    # ==========================================================

    @staticmethod
    def get_notifications(
        db: Session,
        user_id: int
    ):

        return db.query(
            MedicalMessageNotification
        ).filter(
            MedicalMessageNotification.user_id == user_id
        ).order_by(
            MedicalMessageNotification.created_at.desc()
        ).all()

    # ==========================================================
    # MARCAR NOTIFICACIÓN COMO LEÍDA
    # ==========================================================

    @staticmethod
    def mark_notification_as_read(
        db: Session,
        notification_id: int,
        user_id: int
    ):

        notification = db.query(
            MedicalMessageNotification
        ).filter(
            MedicalMessageNotification.id == notification_id,
            MedicalMessageNotification.user_id == user_id
        ).first()

        if not notification:
            return None

        notification.is_read = True

        db.commit()
        db.refresh(notification)

        return notification

    # ==========================================================
    # ELIMINAR CONVERSACIÓN
    # ==========================================================

    @staticmethod
    def delete_conversation(
        db: Session,
        conversation_id: int,
        user_id: int
    ):

        conversation = db.query(
            MedicalConversation
        ).filter(
            MedicalConversation.id == conversation_id,
            or_(
                MedicalConversation.patient_id == user_id,
                MedicalConversation.doctor_id == user_id
            )
        ).first()

        if not conversation:
            return None

        db.delete(conversation)
        db.commit()

        return True