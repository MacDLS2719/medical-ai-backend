from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.rag.datos.medical_notification_service import MedicalNotificationService
from app.schemas.medical_alert import MedicalAlertCreate, MedicalAlertUpdate

router = APIRouter(
    prefix="/api/medical/notifications",
    tags=["Medical Alerts"],
)

@router.get("")
def get_alerts(user_id: int, db: Session = Depends(get_db)):
    service = MedicalNotificationService(db)
    notifications = service.get_user_notifications(user_id=user_id)
    result = []
    for notif in notifications:
        result.append({
            "id": notif.id,
            "user_id": notif.user_id,
            "name": notif.name,
            "topic": notif.medical_topic,
            "info_type": notif.information_type,
            "frequency": notif.frequency,
            "source": notif.source,
            "is_active": notif.status == "active",
            "created_at": notif.created_at
        })
    return result

@router.post("")
def create_alert(alert: MedicalAlertCreate, db: Session = Depends(get_db)):
    service = MedicalNotificationService(db)
    status_str = "active" if alert.is_active else "inactive"
    notif = service.create_notification(
        user_id=alert.user_id,
        name=alert.name,
        medical_topic=alert.topic,
        information_type=alert.info_type,
        frequency=alert.frequency,
        source=alert.source,
        status=status_str
    )
    return {
        "id": notif.id,
        "user_id": notif.user_id,
        "name": notif.name,
        "topic": notif.medical_topic,
        "info_type": notif.information_type,
        "frequency": notif.frequency,
        "source": notif.source,
        "is_active": notif.status == "active",
        "created_at": notif.created_at
    }

@router.patch("/{alert_id}")
def update_alert(alert_id: int, update_data: MedicalAlertUpdate, db: Session = Depends(get_db)):
    service = MedicalNotificationService(db)
    notif = service.get_notification(notification_id=alert_id)
    if not notif:
        raise HTTPException(status_code=404, detail="Alert not found")
    status_str = "active" if update_data.is_active else "inactive"
    notif = service.update_notification(
        notification_id=alert_id,
        user_id=notif.user_id,
        status=status_str
    )
    return {
        "id": notif.id,
        "is_active": notif.status == "active"
    }
