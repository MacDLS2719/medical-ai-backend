from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, Header
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.services.medical_notification_service import MedicalNotificationService
from app.core.auth import get_current_user
from app.core.i18n import normalize_language


router = APIRouter(
    prefix="/notifications",
    tags=["Medical Notifications"],
)


# ==============================================================
# OBTENER NOTIFICACIONES DEL USUARIO
# ==============================================================

@router.get("")
def get_notifications(
    unread_only: bool = Query(False),
    notification_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = MedicalNotificationService(db)

    notifications = service.get_user_notifications(
        user_id=current_user.id,
        unread_only=unread_only,
        notification_type=notification_type,
        limit=limit,
    )

    return {
        "success": True,
        "data": notifications,
    }


# ==============================================================
# OBTENER UNA NOTIFICACIÓN
# ==============================================================

@router.get("/{notification_id}")
def get_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = MedicalNotificationService(db)

    notification = service.get_notification(
        notification_id=notification_id,
        user_id=current_user.id,
    )

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notificación no encontrada",
        )

    return {
        "success": True,
        "data": notification,
    }


# ==============================================================
# CONTAR NOTIFICACIONES NO LEÍDAS
# ==============================================================

@router.get("/unread/count")
def count_unread_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = MedicalNotificationService(db)

    count = service.count_unread(
        user_id=current_user.id,
    )

    return {
        "success": True,
        "data": {
            "count": count,
        },
    }


# ==============================================================
# MARCAR COMO LEÍDA
# ==============================================================

@router.patch("/{notification_id}/read")
def mark_notification_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = MedicalNotificationService(db)

    notification = service.mark_as_read(
        notification_id=notification_id,
        user_id=current_user.id,
    )

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notificación no encontrada",
        )

    return {
        "success": True,
        "message": "Notificación marcada como leída",
        "data": notification,
    }


# ==============================================================
# MARCAR COMO NO LEÍDA
# ==============================================================

@router.patch("/{notification_id}/unread")
def mark_notification_as_unread(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = MedicalNotificationService(db)

    notification = service.mark_as_unread(
        notification_id=notification_id,
        user_id=current_user.id,
    )

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notificación no encontrada",
        )

    return {
        "success": True,
        "message": "Notificación marcada como no leída",
        "data": notification,
    }


# ==============================================================
# MARCAR TODAS COMO LEÍDAS
# ==============================================================

@router.patch("/read-all")
def mark_all_notifications_as_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = MedicalNotificationService(db)

    count = service.mark_all_as_read(
        user_id=current_user.id,
    )

    return {
        "success": True,
        "message": "Todas las notificaciones fueron marcadas como leídas",
        "data": {
            "updated": count,
        },
    }


# ==============================================================
# ELIMINAR NOTIFICACIÓN
# ==============================================================

@router.delete("/{notification_id}")
def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = MedicalNotificationService(db)

    deleted = service.delete_notification(
        notification_id=notification_id,
        user_id=current_user.id,
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notificación no encontrada",
        )

    return {
        "success": True,
        "message": "Notificación eliminada correctamente",
    }


# ==============================================================
# ELIMINAR TODAS LAS NOTIFICACIONES LEÍDAS
# ==============================================================

@router.delete("/read")
def delete_read_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = MedicalNotificationService(db)

    count = service.delete_read_notifications(
        user_id=current_user.id,
    )

    return {
        "success": True,
        "message": "Notificaciones leídas eliminadas correctamente",
        "data": {
            "deleted": count,
        },
    }


# ==============================================================
# GENERAR NOTIFICACIONES INTELIGENTES
# ==============================================================

@router.post("/generate")
async def generate_smart_notifications(
    accept_language: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Genera notificaciones inteligentes basadas en el rol del usuario:
    - Pacientes: Últimos estudios sobre sus patologías
    - Doctores: Últimas publicaciones en su especialidad
    """
    service = MedicalNotificationService(db)

    # Determinar idioma del usuario
    target_lang = normalize_language(
        current_user.language or accept_language
    )

    # Generar notificaciones según el rol
    result = await service.generate_smart_notifications(
        user_id=current_user.id,
        user_role=current_user.role,
        target_lang=target_lang
    )

    if result["success"]:
        return {
            "success": True,
            "message": result["message"],
            "data": {
                "notifications_created": result["notifications_created"]
            }
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["message"]
        )


# ==============================================================
# GENERAR NOTIFICACIONES PARA TODOS LOS USUARIOS (ADMIN/CRON)
# ==============================================================

@router.post("/generate-all")
async def generate_notifications_for_all_users(
    accept_language: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Genera notificaciones para todos los usuarios (endpoint para trabajos programados).
    Solo accesible para administradores o sistemas de cron.
    """
    # Verificar si es admin (opcional, según tus requisitos)
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo administradores pueden generar notificaciones masivas"
        )

    from app.models.user import User

    service = MedicalNotificationService(db)

    # Obtener todos los usuarios activos
    users = db.query(User).filter(User.is_active == True).all()

    total_notifications = 0
    users_processed = 0
    errors = []

    for user in users:
        try:
            # Determinar idioma del usuario
            target_lang = normalize_language(
                user.language or accept_language
            )

            # Generar notificaciones según el rol
            result = await service.generate_smart_notifications(
                user_id=user.id,
                user_role=user.role,
                target_lang=target_lang
            )

            if result["success"]:
                total_notifications += result["notifications_created"]
                users_processed += 1
            else:
                errors.append({
                    "user_id": user.id,
                    "error": result["message"]
                })

        except Exception as e:
            errors.append({
                "user_id": user.id,
                "error": str(e)
            })
            continue

    return {
        "success": True,
        "message": f"Procesados {users_processed} usuarios, {total_notifications} notificaciones creadas",
        "data": {
            "users_processed": users_processed,
            "total_notifications": total_notifications,
            "errors": errors
        }
    }