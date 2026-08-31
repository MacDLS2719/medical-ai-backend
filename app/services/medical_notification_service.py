from typing import Optional, List
from datetime import datetime, timedelta
import asyncio

from sqlalchemy.orm import Session

from app.models.medical_notification import MedicalNotification
from app.models.patient import Patient
from app.models.doctor import Doctor
from app.models.pathology import Pathology
from app.models.patient_pathology import PatientPathology

from app.services.medical_search_service import MedicalSearchService
from app.services.pubmed_service import PubMedService
from app.services.clinical_trials_service import ClinicalTrialsService
from app.services.cochrane_service import CochraneService
from app.services.europe_pmc_service import EuropePMCService
from app.services.who_ictrp_service import WHOICTRPService


class MedicalNotificationService:

    def __init__(self, db: Session):
        self.db = db

        # Inicializar servicios de búsqueda
        self.medical_search_service = MedicalSearchService(
            pubmed_service=PubMedService(),
            clinical_trials_service=ClinicalTrialsService(),
            cochrane_service=CochraneService(),
            europe_pmc_service=EuropePMCService(),
            who_ictrp_service=WHOICTRPService()
        )

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

    # ==============================================================
    # GENERAR NOTIFICACIONES PARA PACIENTES
    # ==============================================================

    async def generate_patient_notifications(
        self,
        user_id: int,
        target_lang: str = "es"
    ) -> List[MedicalNotification]:
        """
        Genera notificaciones para pacientes basadas en sus patologías
        con los últimos estudios publicados.
        """

        # Obtener paciente y sus patologías
        patient = (
            self.db.query(Patient)
            .filter(Patient.user_id == user_id)
            .first()
        )

        if not patient or not patient.patient_pathologies:
            return []

        # Obtener nombres de patologías
        pathologies = [
            pp.pathology.name
            for pp in patient.patient_pathologies
            if pp.pathology
        ]

        if not pathologies:
            return []

        print(f"Generando notificaciones para paciente {user_id} con patologías: {pathologies}")

        notifications_created = []

        # Para cada patología, buscar los últimos estudios
        for pathology in pathologies:
            try:
                # Buscar estudios recientes para esta patología
                search_result = await self.medical_search_service.search(
                    query=pathology,
                    max_results=5,  # Limitar a los 5 más recientes
                    target_lang=target_lang
                )

                if search_result.get("results"):
                    latest_studies = search_result["results"][:3]  # Top 3

                    # Verificar si ya existe notificación reciente para esta patología
                    recent_notification = (
                        self.db.query(MedicalNotification)
                        .filter(
                            MedicalNotification.user_id == user_id,
                            MedicalNotification.type == "research_update",
                            MedicalNotification.created_at > datetime.now() - timedelta(days=7)
                        )
                        .first()
                    )

                    if recent_notification and recent_notification.data:
                        # Obtener IDs de estudios ya notificados
                        if isinstance(recent_notification.data, dict):
                            notified_ids = recent_notification.data.get("study_ids", [])
                        else:
                            notified_ids = []
                    else:
                        notified_ids = []

                    # Filtrar estudios nuevos
                    new_studies = [
                        study for study in latest_studies
                        if study.source_id not in notified_ids
                    ]

                    if new_studies:
                        # Crear notificación consolidada con estudios nuevos
                        studies_data = [
                            {
                                "source_id": study.source_id,
                                "title": study.title,
                                "url": study.url,
                                "publication_date": study.publication_date
                            }
                            for study in new_studies
                        ]

                        all_study_ids = notified_ids + [study.source_id for study in new_studies]

                        notification = self.create_notification(
                            user_id=user_id,
                            notification_type="research_update",
                            frequency="weekly",
                            title=f"Nuevos estudios sobre {pathology}",
                            message=f"Se encontraron {len(new_studies)} nuevos estudios relevantes sobre {pathology}. Mantente informado sobre los últimos avances.",
                            data={
                                "pathology": pathology,
                                "study_ids": all_study_ids,
                                "new_studies": studies_data,
                                "total_new": len(new_studies)
                            }
                        )
                        notifications_created.append(notification)
                        print(f"Notificación creada para {pathology}: {len(new_studies)} estudios nuevos")
                    else:
                        print(f"No hay estudios nuevos para {pathology}")

            except Exception as e:
                print(f"Error generando notificaciones para patología {pathology}: {e}")
                continue

        return notifications_created

    # ==============================================================
    # GENERAR NOTIFICACIONES PARA DOCTORES
    # ==============================================================

    async def generate_doctor_notifications(
        self,
        user_id: int,
        target_lang: str = "es"
    ) -> List[MedicalNotification]:
        """
        Genera notificaciones para doctores con las últimas publicaciones
        en su especialidad.
        """

        # Obtener doctor y su especialidad
        doctor = (
            self.db.query(Doctor)
            .filter(Doctor.user_id == user_id)
            .first()
        )

        if not doctor or not doctor.specialty:
            return []

        specialty = doctor.specialty
        print(f"Generando notificaciones para doctor {user_id} con especialidad: {specialty}")

        notifications_created = []

        try:
            # Buscar publicaciones recientes en la especialidad
            search_result = await self.medical_search_service.search(
                query=specialty,
                max_results=10,  # Más resultados para doctores
                target_lang=target_lang
            )

            if search_result.get("results"):
                latest_publications = search_result["results"][:5]  # Top 5

                # Verificar si hay notificaciones recientes para esta especialidad
                recent_notification = (
                    self.db.query(MedicalNotification)
                    .filter(
                        MedicalNotification.user_id == user_id,
                        MedicalNotification.type == "specialty_update",
                        MedicalNotification.created_at > datetime.now() - timedelta(days=7)
                    )
                    .first()
                )

                if not recent_notification:
                    # Crear notificación con las últimas publicaciones
                    publications_data = [
                        {
                            "source_id": pub.source_id,
                            "title": pub.title,
                            "url": pub.url,
                            "publication_date": pub.publication_date,
                            "source": pub.source_type
                        }
                        for pub in latest_publications
                    ]

                    notification = self.create_notification(
                        user_id=user_id,
                        notification_type="specialty_update",
                        frequency="weekly",
                        title=f"Nuevas publicaciones en {specialty}",
                        message=f"Se encontraron {len(latest_publications)} nuevas publicaciones relevantes en {specialty}. Mantente al día con los últimos avances.",
                        data={
                            "specialty": specialty,
                            "publications": publications_data,
                            "total_count": len(latest_publications)
                        }
                    )
                    notifications_created.append(notification)
                    print(f"Notificación creada para doctor: {notification.title}")
                else:
                    print(f"Ya existe notificación reciente para {specialty}, skipping")

        except Exception as e:
            print(f"Error generando notificaciones para doctor: {e}")

        return notifications_created

    # ==============================================================
    # GENERAR NOTIFICACIONES INTELIGENTES (UNIFICADO)
    # ==============================================================

    async def generate_smart_notifications(
        self,
        user_id: int,
        user_role: str,
        target_lang: str = "es"
    ) -> dict:
        """
        Genera notificaciones inteligentes según el rol del usuario.
        """

        result = {
            "success": False,
            "notifications_created": 0,
            "message": ""
        }

        try:
            if user_role == "patient":
                notifications = await self.generate_patient_notifications(
                    user_id=user_id,
                    target_lang=target_lang
                )
                result["success"] = True
                result["notifications_created"] = len(notifications)
                result["message"] = f"Se generaron {len(notifications)} notificaciones basadas en tus patologías."

            elif user_role == "doctor":
                notifications = await self.generate_doctor_notifications(
                    user_id=user_id,
                    target_lang=target_lang
                )
                result["success"] = True
                result["notifications_created"] = len(notifications)
                result["message"] = f"Se generaron {len(notifications)} notificaciones con las últimas publicaciones en tu especialidad."

            else:
                result["message"] = "Rol de usuario no soportado para notificaciones inteligentes."

        except Exception as e:
            result["message"] = f"Error generando notificaciones: {e}"
            print(f"Error en generate_smart_notifications: {e}")

        return result