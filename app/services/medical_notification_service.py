from typing import Optional, List

from sqlalchemy.orm import Session

from app.models.medical_notification import MedicalNotification


class MedicalNotificationService:

    def __init__(self, db: Session):
        self.db = db

    # ==============================================================
    # CREAR NOTIFICACIÓN
    # ==============================================================

    def create_notification(
        self,
        user_id: int,
        notification_type: str,
        frequency: str,
        title: str,
        message: str,
        data: Optional[dict] = None,
    ) -> MedicalNotification:

        notification = MedicalNotification(
            user_id=user_id,
            type=notification_type,
            frequency=frequency,
            title=title,
            message=message,
            is_read=False,
            data=data,
        )

        self.db.add(notification)

        self.db.commit()

        self.db.refresh(notification)

        return notification

    # ==============================================================
    # OBTENER NOTIFICACIÓN POR ID
    # ==============================================================

    def get_notification(
        self,
        notification_id: int,
        user_id: Optional[int] = None,
    ) -> Optional[MedicalNotification]:

        query = (
            self.db.query(
                MedicalNotification
            )
            .filter(
                MedicalNotification.id
                == notification_id
            )
        )

        if user_id is not None:

            query = query.filter(
                MedicalNotification.user_id
                == user_id
            )

        return query.first()

    # ==============================================================
    # OBTENER NOTIFICACIONES DE UN USUARIO
    # ==============================================================

    def get_user_notifications(
        self,
        user_id: int,
        unread_only: bool = False,
        notification_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[MedicalNotification]:

        query = (
            self.db.query(
                MedicalNotification
            )
            .filter(
                MedicalNotification.user_id
                == user_id
            )
        )

        # ----------------------------------------------------------
        # SOLO NO LEÍDAS
        # ----------------------------------------------------------

        if unread_only:

            query = query.filter(
                MedicalNotification.is_read
                == False
            )

        # ----------------------------------------------------------
        # FILTRAR POR TIPO
        # ----------------------------------------------------------

        if notification_type:

            query = query.filter(
                MedicalNotification.type
                == notification_type
            )

        # ----------------------------------------------------------
        # ORDENAR MÁS RECIENTE PRIMERO
        # ----------------------------------------------------------

        query = query.order_by(
            MedicalNotification.created_at.desc()
        )

        # ----------------------------------------------------------
        # LIMITAR RESULTADOS
        # ----------------------------------------------------------

        query = query.limit(
            limit
        )

        return query.all()

    # ==============================================================
    # CONTAR NOTIFICACIONES NO LEÍDAS
    # ==============================================================

    def count_unread(
        self,
        user_id: int,
    ) -> int:

        return (
            self.db.query(
                MedicalNotification
            )
            .filter(
                MedicalNotification.user_id
                == user_id,

                MedicalNotification.is_read
                == False,
            )
            .count()
        )

    # ==============================================================
    # MARCAR COMO LEÍDA
    # ==============================================================

    def mark_as_read(
        self,
        notification_id: int,
        user_id: int,
    ) -> Optional[MedicalNotification]:

        notification = self.get_notification(
            notification_id=notification_id,
            user_id=user_id,
        )

        if not notification:
            return None

        notification.is_read = True

        self.db.commit()

        self.db.refresh(
            notification
        )

        return notification

    # ==============================================================
    # MARCAR COMO NO LEÍDA
    # ==============================================================

    def mark_as_unread(
        self,
        notification_id: int,
        user_id: int,
    ) -> Optional[MedicalNotification]:

        notification = self.get_notification(
            notification_id=notification_id,
            user_id=user_id,
        )

        if not notification:
            return None

        notification.is_read = False

        self.db.commit()

        self.db.refresh(
            notification
        )

        return notification

    # ==============================================================
    # MARCAR TODAS COMO LEÍDAS
    # ==============================================================

    def mark_all_as_read(
        self,
        user_id: int,
    ) -> int:

        notifications = (
            self.db.query(
                MedicalNotification
            )
            .filter(
                MedicalNotification.user_id
                == user_id,

                MedicalNotification.is_read
                == False,
            )
            .all()
        )

        for notification in notifications:

            notification.is_read = True

        self.db.commit()

        return len(
            notifications
        )

    # ==============================================================
    # ELIMINAR NOTIFICACIÓN
    # ==============================================================

    def delete_notification(
        self,
        notification_id: int,
        user_id: int,
    ) -> bool:

        notification = self.get_notification(
            notification_id=notification_id,
            user_id=user_id,
        )

        if not notification:
            return False

        self.db.delete(
            notification
        )

        self.db.commit()

        return True

    # ==============================================================
    # ELIMINAR TODAS LAS NOTIFICACIONES LEÍDAS
    # ==============================================================

    def delete_read_notifications(
        self,
        user_id: int,
    ) -> int:

        notifications = (
            self.db.query(
                MedicalNotification
            )
            .filter(
                MedicalNotification.user_id
                == user_id,

                MedicalNotification.is_read
                == True,
            )
            .all()
        )

        count = len(
            notifications
        )

        for notification in notifications:

            self.db.delete(
                notification
            )

        self.db.commit()

        return count