from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.services.medical_notification_service import MedicalNotificationService
from app.core.auth import get_current_user


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