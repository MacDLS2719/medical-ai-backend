"""
Servicio de control de cuota de búsquedas médicas por día.

Responsabilidades:
  - Determinar si el usuario tiene plan PRO (DoctorSubscription activa).
  - Obtener / crear el registro de uso diario (MedicalSearchUsage).
  - Validar que el usuario no haya superado el límite gratuito.
  - Incrementar el contador tras una búsqueda exitosa.

Límites:
  - Plan gratuito: 10 búsquedas / día.
  - Plan PRO     : sin límite.
"""

from datetime import date

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.doctor_subscription import DoctorSubscription
from app.models.medical_search_usage import MedicalSearchUsage
from app.models.user import User

FREE_DAILY_LIMIT = 10


class SearchUsageService:
    # ------------------------------------------------------------------
    # Consultas de estado
    # ------------------------------------------------------------------

    def is_pro(self, user: User, db: Session) -> bool:
        """Devuelve True si el usuario tiene una suscripción de médico activa."""
        if not user.doctor:
            return False
        active_sub = (
            db.query(DoctorSubscription)
            .filter(
                DoctorSubscription.doctor_id == user.doctor.id,
                DoctorSubscription.status == "active",
            )
            .first()
        )
        return active_sub is not None

    def get_active_subscription_id(self, user: User, db: Session) -> int | None:
        """Retorna el id de la suscripción activa, o None si no existe."""
        if not user.doctor:
            return None
        active_sub = (
            db.query(DoctorSubscription)
            .filter(
                DoctorSubscription.doctor_id == user.doctor.id,
                DoctorSubscription.status == "active",
            )
            .first()
        )
        return active_sub.id if active_sub else None

    def get_or_create_today_usage(
        self, user: User, db: Session, subscription_id: int | None = None
    ) -> MedicalSearchUsage:
        """
        Devuelve el registro de uso del día de hoy para el usuario.
        Si no existe lo crea con search_count = 0 y lo persiste.
        """
        today = date.today()
        usage = (
            db.query(MedicalSearchUsage)
            .filter(
                MedicalSearchUsage.user_id == user.id,
                MedicalSearchUsage.search_date == today,
            )
            .first()
        )
        if not usage:
            usage = MedicalSearchUsage(
                user_id=user.id,
                subscription_id=subscription_id,
                search_date=today,
                search_count=0,
            )
            db.add(usage)
            db.commit()
            db.refresh(usage)
        return usage

    def get_usage_summary(self, user: User, db: Session) -> dict:
        """
        Retorna un diccionario con:
          - is_pro: bool
          - searches_used: int  (búsquedas realizadas hoy)
          - searches_limit: int (límite aplicable)
          - searches_remaining: int
        """
        pro = self.is_pro(user, db)
        sub_id = self.get_active_subscription_id(user, db)
        usage = self.get_or_create_today_usage(user, db, sub_id)

        used = usage.search_count
        limit = FREE_DAILY_LIMIT  # Para PRO lo mostramos igual pero no bloqueamos
        remaining = max(0, limit - used) if not pro else limit

        return {
            "is_pro": pro,
            "searches_used": used,
            "searches_limit": limit,
            "searches_remaining": remaining,
        }

    # ------------------------------------------------------------------
    # Validación y registro
    # ------------------------------------------------------------------

    def validate_and_increment(self, user: User, db: Session) -> None:
        """
        1. Verifica si el usuario puede hacer una búsqueda.
        2. Si no puede (plan gratuito y límite alcanzado) lanza HTTPException 403.
        3. Si puede, incrementa el contador y guarda en BD.

        Llamar DESPUÉS de obtener el resultado de la IA para no consumir
        cuota si la búsqueda falla (el router debe invocarlo en el bloque
        de éxito).
        """
        pro = self.is_pro(user, db)
        sub_id = self.get_active_subscription_id(user, db)
        usage = self.get_or_create_today_usage(user, db, sub_id)

        if not pro and usage.search_count >= FREE_DAILY_LIMIT:
            raise HTTPException(
                status_code=403,
                detail=(
                    f"Has superado el límite de {FREE_DAILY_LIMIT} búsquedas "
                    "por día en el plan gratuito. Actualiza a PRO para continuar."
                ),
            )

        # Incrementar y persistir
        usage.search_count += 1
        db.commit()


search_usage_service = SearchUsageService()
