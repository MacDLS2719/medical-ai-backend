from typing import List, Optional
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.medical_notification import MedicalNotification

from app.services.rag.medical_search_orchestrator import (
    MedicalSearchOrchestrator,
)

from app.services.rag.datos.medical_notification_service import (
    MedicalNotificationService,
)


class MedicalNotificationSearchService:

    def __init__(self, db: Session):
        self.db = db

        self.notification_service = (
            MedicalNotificationService(db)
        )

        self.medical_search_orchestrator = (
            MedicalSearchOrchestrator()
        )

    # ==========================================================
    # EJECUTAR ALERTA
    # ==========================================================

    async def execute_notification(
        self,
        notification: MedicalNotification,
        max_results: int = 10,
    ) -> Optional[dict]:

        # ------------------------------------------------------
        # VALIDAR ESTADO
        # ------------------------------------------------------

        if notification.status != "active":
            return None

        # ------------------------------------------------------
        # VALIDAR FRECUENCIA
        # ------------------------------------------------------

        if not self._should_execute(notification):
            return None

        # ------------------------------------------------------
        # VALIDAR TEMA MÉDICO
        # ------------------------------------------------------

        if not notification.medical_topic:
            return None

        # ------------------------------------------------------
        # DETERMINAR FUENTES
        # ------------------------------------------------------

        sources = self._normalize_sources(
            notification.source
        )

        # ------------------------------------------------------
        # EJECUTAR BÚSQUEDA
        # ------------------------------------------------------

        search_result = (
            await self.medical_search_orchestrator.search(
                query=notification.medical_topic,
                sources=sources,
                max_results=max_results,
            )
        )

        results = search_result.get(
            "results",
            []
        ) or []

        # ------------------------------------------------------
        # MARCAR EJECUCIÓN
        # ------------------------------------------------------

        self._mark_as_checked(notification)

        return {
            "notification_id": notification.id,
            "name": notification.name,
            "medical_topic": notification.medical_topic,
            "information_type": notification.information_type,
            "frequency": notification.frequency,
            "source": notification.source,
            "status": notification.status,
            "results": results,
            "total_results": len(results),
        }

    # ==========================================================
    # EJECUTAR ALERTA POR ID
    # ==========================================================

    async def execute_notification_by_id(
        self,
        notification_id: int,
        user_id: Optional[int] = None,
        max_results: int = 10,
    ) -> Optional[dict]:

        notification = (
            self.notification_service.get_notification(
                notification_id=notification_id,
                user_id=user_id,
            )
        )

        if not notification:
            return None

        return await self.execute_notification(
            notification=notification,
            max_results=max_results,
        )

    # ==========================================================
    # EJECUTAR ALERTAS ACTIVAS DE UN USUARIO
    # ==========================================================

    async def execute_user_notifications(
        self,
        user_id: int,
        max_results: int = 10,
    ) -> List[dict]:

        notifications = (
            self.notification_service
            .get_active_notifications(
                user_id=user_id
            )
        )

        results = []

        for notification in notifications:

            result = await self.execute_notification(
                notification=notification,
                max_results=max_results,
            )

            if result is not None:
                results.append(result)

        return results

    # ==========================================================
    # EJECUTAR TODAS LAS ALERTAS ACTIVAS
    # ==========================================================

    async def execute_all_active_notifications(
        self,
        max_results: int = 10,
    ) -> List[dict]:

        notifications = (
            self.notification_service
            .get_active_notifications()
        )

        results = []

        for notification in notifications:

            result = await self.execute_notification(
                notification=notification,
                max_results=max_results,
            )

            if result is not None:
                results.append(result)

        return results

    # ==========================================================
    # VALIDAR SI CORRESPONDE EJECUTAR
    # ==========================================================

    def _should_execute(
        self,
        notification: MedicalNotification,
    ) -> bool:

        # Si todavía nunca se ha ejecutado,
        # corresponde ejecutarla.
        if not notification.last_checked_at:
            return True

        now = datetime.utcnow()

        last_checked = notification.last_checked_at

        frequency = (
            notification.frequency.lower()
            if notification.frequency
            else "weekly"
        )

        # ------------------------------------------------------
        # DIARIA
        # ------------------------------------------------------

        if frequency == "daily":

            return (
                now - last_checked
            ) >= timedelta(days=1)

        # ------------------------------------------------------
        # SEMANAL
        # ------------------------------------------------------

        if frequency == "weekly":

            return (
                now - last_checked
            ) >= timedelta(days=7)

        # ------------------------------------------------------
        # MENSUAL
        # ------------------------------------------------------

        if frequency == "monthly":

            return (
                now - last_checked
            ) >= timedelta(days=30)

        # ------------------------------------------------------
        # FRECUENCIA DESCONOCIDA
        # ------------------------------------------------------

        return False

    # ==========================================================
    # NORMALIZAR FUENTES
    # ==========================================================

    def _normalize_sources(
        self,
        source: Optional[str],
    ) -> Optional[List[str]]:

        if not source:
            return None

        source = source.strip().lower()

        # ------------------------------------------------------
        # TODAS LAS FUENTES
        # ------------------------------------------------------

        if source in (
            "all",
            "all_sources",
            "todas",
            "todas_las_fuentes",
        ):
            return None

        # ------------------------------------------------------
        # VARIAS FUENTES
        # ------------------------------------------------------

        sources = [
            item.strip().lower()
            for item in source.split(",")
            if item.strip()
        ]

        return sources or None

    # ==========================================================
    # ACTUALIZAR ÚLTIMA EJECUCIÓN
    # ==========================================================

    def _mark_as_checked(
        self,
        notification: MedicalNotification,
    ) -> None:

        notification.last_checked_at = datetime.utcnow()

        self.db.commit()

        self.db.refresh(notification)