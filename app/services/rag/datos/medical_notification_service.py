from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.medical_notification import MedicalNotification


class MedicalNotificationService:

    def __init__(self, db: Session):
        self.db = db

    # ==========================================================
    # CREAR ALERTA
    # ==========================================================

    def create_notification(
        self,
        user_id: int,
        name: str,
        medical_topic: str,
        information_type: str,
        frequency: str,
        source: str,
        status: str = "active",
    ) -> MedicalNotification:

        notification = MedicalNotification(
            user_id=user_id,
            name=name,
            medical_topic=medical_topic,
            information_type=information_type,
            frequency=frequency,
            source=source,
            status=status,
        )

        self.db.add(notification)
        self.db.flush()

        self.db.commit()
        self.db.refresh(notification)

        return notification

    # ==========================================================
    # OBTENER ALERTA POR ID
    # ==========================================================

    def get_notification(
        self,
        notification_id: int,
        user_id: Optional[int] = None,
    ) -> Optional[MedicalNotification]:

        statement = select(
            MedicalNotification
        ).where(
            MedicalNotification.id == notification_id
        )

        if user_id is not None:
            statement = statement.where(
                MedicalNotification.user_id == user_id
            )

        return self.db.execute(
            statement
        ).scalar_one_or_none()

    # ==========================================================
    # OBTENER ALERTAS DE UN USUARIO
    # ==========================================================

    def get_user_notifications(
        self,
        user_id: int,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[MedicalNotification]:

        statement = select(
            MedicalNotification
        ).where(
            MedicalNotification.user_id == user_id
        )

        if status is not None:
            statement = statement.where(
                MedicalNotification.status == status
            )

        statement = (
            statement
            .order_by(
                MedicalNotification.created_at.desc()
            )
            .limit(limit)
        )

        return list(
            self.db.execute(
                statement
            ).scalars().all()
        )

    # ==========================================================
    # OBTENER ALERTAS ACTIVAS
    # ==========================================================

    def get_active_notifications(
        self,
        user_id: Optional[int] = None,
    ) -> List[MedicalNotification]:

        statement = select(
            MedicalNotification
        ).where(
            MedicalNotification.status == "active"
        )

        if user_id is not None:
            statement = statement.where(
                MedicalNotification.user_id == user_id
            )

        statement = statement.order_by(
            MedicalNotification.created_at.desc()
        )

        return list(
            self.db.execute(
                statement
            ).scalars().all()
        )

    # ==========================================================
    # ACTUALIZAR ALERTA
    # ==========================================================

    def update_notification(
        self,
        notification_id: int,
        user_id: int,
        name: Optional[str] = None,
        medical_topic: Optional[str] = None,
        information_type: Optional[str] = None,
        frequency: Optional[str] = None,
        source: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Optional[MedicalNotification]:

        notification = self.get_notification(
            notification_id=notification_id,
            user_id=user_id,
        )

        if not notification:
            return None

        if name is not None:
            notification.name = name

        if medical_topic is not None:
            notification.medical_topic = medical_topic

        if information_type is not None:
            notification.information_type = information_type

        if frequency is not None:
            notification.frequency = frequency

        if source is not None:
            notification.source = source

        if status is not None:
            notification.status = status

        self.db.flush()
        self.db.commit()
        self.db.refresh(notification)

        return notification

    # ==========================================================
    # ACTIVAR ALERTA
    # ==========================================================

    def activate_notification(
        self,
        notification_id: int,
        user_id: int,
    ) -> Optional[MedicalNotification]:

        return self.update_notification(
            notification_id=notification_id,
            user_id=user_id,
            status="active",
        )

    # ==========================================================
    # DESACTIVAR ALERTA
    # ==========================================================

    def deactivate_notification(
        self,
        notification_id: int,
        user_id: int,
    ) -> Optional[MedicalNotification]:

        return self.update_notification(
            notification_id=notification_id,
            user_id=user_id,
            status="inactive",
        )

    # ==========================================================
    # ELIMINAR ALERTA
    # ==========================================================

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

        self.db.delete(notification)
        self.db.commit()

        return True

    # ==========================================================
    # CONTAR ALERTAS ACTIVAS
    # ==========================================================

    def count_active_notifications(
        self,
        user_id: int,
    ) -> int:

        notifications = self.get_active_notifications(
            user_id=user_id
        )

        return len(notifications)

    # ==========================================================
    # CAMBIAR ESTADO
    # ==========================================================

    def change_status(
        self,
        notification_id: int,
        user_id: int,
        status: str,
    ) -> Optional[MedicalNotification]:

        return self.update_notification(
            notification_id=notification_id,
            user_id=user_id,
            status=status,
        )

    # ==========================================================
    # MÉTODOS STUB PARA COMPATIBILIDAD CON EL ENRUTADOR
    # ==========================================================

    def count_unread(self, user_id: int) -> int:
        # Como las alertas médicas actuales no tienen un estado de lectura,
        # devolvemos 0 para evitar errores en la interfaz.
        return 0

    def mark_as_read(self, notification_id: int, user_id: int) -> Optional[MedicalNotification]:
        return self.get_notification(notification_id=notification_id, user_id=user_id)

    def mark_as_unread(self, notification_id: int, user_id: int) -> Optional[MedicalNotification]:
        return self.get_notification(notification_id=notification_id, user_id=user_id)

    def mark_all_as_read(self, user_id: int) -> int:
        return 0

    def delete_read_notifications(self, user_id: int) -> int:
        return 0