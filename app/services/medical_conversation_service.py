from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.models.medical_conversation import MedicalConversation
from app.models.medical_message import MedicalMessage
from app.models.medical_message_notification import MedicalMessageNotification
from app.models.medical_message_attachment import MedicalMessageAttachment


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

        conversation = db.query(
            MedicalConversation
        ).filter(
            and_(
                MedicalConversation.patient_id == patient_id,
                MedicalConversation.doctor_id == doctor_id
            )
        ).first()

        if conversation:

            # --------------------------------------------------
            # Reactivar para ambos participantes
            # --------------------------------------------------
            #
            # Si alguno había desactivado anteriormente
            # la conversación y vuelve a abrir el chat,
            # la conversación vuelve a estar disponible.
            #
            # No se eliminan mensajes ni historial.
            # --------------------------------------------------

            changed = False

            if conversation.patient_deleted_at is not None:
                conversation.patient_deleted_at = None
                changed = True

            if conversation.doctor_deleted_at is not None:
                conversation.doctor_deleted_at = None
                changed = True

            if changed:
                conversation.status = "active"
                conversation.updated_at = datetime.utcnow()

                db.commit()
                db.refresh(conversation)

            return conversation

        # ------------------------------------------------------
        # Crear nueva conversación
        # ------------------------------------------------------

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

        # ------------------------------------------------------
        # Paciente
        # ------------------------------------------------------

        patient_conversations = db.query(
            MedicalConversation
        ).filter(
            MedicalConversation.patient_id == user_id,
            MedicalConversation.patient_deleted_at.is_(None)
        )

        # ------------------------------------------------------
        # Médico
        # ------------------------------------------------------

        doctor_conversations = db.query(
            MedicalConversation
        ).filter(
            MedicalConversation.doctor_id == user_id,
            MedicalConversation.doctor_deleted_at.is_(None)
        )

        # ------------------------------------------------------
        # Unificar ambos casos
        # ------------------------------------------------------

        return db.query(
            MedicalConversation
        ).filter(
            or_(
                and_(
                    MedicalConversation.patient_id == user_id,
                    MedicalConversation.patient_deleted_at.is_(None)
                ),
                and_(
                    MedicalConversation.doctor_id == user_id,
                    MedicalConversation.doctor_deleted_at.is_(None)
                )
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

        conversation = db.query(
            MedicalConversation
        ).filter(
            MedicalConversation.id == conversation_id,
            or_(
                and_(
                    MedicalConversation.patient_id == user_id,
                    MedicalConversation.patient_deleted_at.is_(None)
                ),
                and_(
                    MedicalConversation.doctor_id == user_id,
                    MedicalConversation.doctor_deleted_at.is_(None)
                )
            )
        ).first()

        return conversation

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

        # ------------------------------------------------------
        # Buscar conversación y verificar que el usuario
        # todavía tenga el chat activo.
        # ------------------------------------------------------

        conversation = db.query(
            MedicalConversation
        ).filter(
            MedicalConversation.id == conversation_id,
            or_(
                and_(
                    MedicalConversation.patient_id == sender_id,
                    MedicalConversation.patient_deleted_at.is_(None)
                ),
                and_(
                    MedicalConversation.doctor_id == sender_id,
                    MedicalConversation.doctor_deleted_at.is_(None)
                )
            )
        ).first()

        if not conversation:
            return None

        # ------------------------------------------------------
        # Determinar receptor
        # ------------------------------------------------------

        if conversation.patient_id == sender_id:
            receiver_id = conversation.doctor_id
        else:
            receiver_id = conversation.patient_id

        # ------------------------------------------------------
        # Crear mensaje
        #
        # MedicalMessage.message utiliza EncryptedText(),
        # por lo que se cifra automáticamente antes de
        # almacenarse en la base de datos.
        # ------------------------------------------------------

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

        # ------------------------------------------------------
        # Crear notificación
        # ------------------------------------------------------

        notification = MedicalMessageNotification(
            message_id=medical_message.id,
            user_id=receiver_id,
            type="new_message",
            title="Nuevo mensaje médico",
            message="Has recibido un nuevo mensaje."
        )

        db.add(notification)

        # ------------------------------------------------------
        # Actualizar conversación
        # ------------------------------------------------------

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

        messages = db.query(
            MedicalMessage
        ).filter(
            MedicalMessage.conversation_id == conversation_id
        ).order_by(
            MedicalMessage.created_at.asc()
        ).all()

        # Marcar como leídos los mensajes no leídos dirigidos al usuario actual
        unread_msgs = [m for m in messages if m.receiver_id == user_id and not m.is_read]
        if unread_msgs:
            for m in unread_msgs:
                m.is_read = True
                m.read_at = datetime.utcnow()
            db.commit()

        return messages

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
            MedicalMessageNotification.is_read.is_(False)
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
    # DESACTIVAR CONVERSACIÓN PARA UN USUARIO
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

        # ------------------------------------------------------
        # Paciente
        # ------------------------------------------------------

        if conversation.patient_id == user_id:

            conversation.patient_deleted_at = datetime.utcnow()

        # ------------------------------------------------------
        # Médico
        # ------------------------------------------------------

        elif conversation.doctor_id == user_id:

            conversation.doctor_deleted_at = datetime.utcnow()

        # ------------------------------------------------------
        # Importante:
        #
        # NO hacemos:
        #
        # db.delete(conversation)
        #
        # La conversación, mensajes, archivos y notificaciones
        # permanecen almacenados.
        # ------------------------------------------------------

        db.commit()

        return True

    # ==========================================================
    # CREAR ADJUNTO
    # ==========================================================

    @staticmethod
    def create_attachment(
        db: Session,
        message_id: int,
        attachment_data: dict,
        duration: float = None
    ):

        attachment = MedicalMessageAttachment(
            message_id=message_id,
            file_name=attachment_data["file_name"],
            file_path=attachment_data["file_path"],
            file_url=attachment_data["file_url"],
            mime_type=attachment_data["mime_type"],
            file_size=attachment_data["file_size"],
            storage_disk=attachment_data["storage_disk"],
            attachment_type=attachment_data["attachment_type"],
            duration=duration
        )

        db.add(attachment)
        db.commit()
        db.refresh(attachment)

        return attachment