from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db

from app.services.rag.datos.medical_notification_service import (
    MedicalNotificationService
)

from app.services.rag.research.alert_search_service import (
    alert_search_service
)

from app.schemas.medical_alert import (
    MedicalAlertCreate,
    MedicalAlertUpdate
)

from app.models.medical_notification import MedicalNotification


router = APIRouter(
    prefix="/api/medical/notifications",
    tags=["Medical Alerts"],
)


# ============================================================
# OBTENER ALERTAS
# ============================================================

@router.get("")
def get_alerts(
    user_id: int,
    db: Session = Depends(get_db)
):
    service = MedicalNotificationService(db)

    notifications = service.get_user_notifications(
        user_id=user_id
    )

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


# ============================================================
# CREAR ALERTA
# ============================================================

@router.post("")
def create_alert(
    alert: MedicalAlertCreate,
    db: Session = Depends(get_db)
):
    service = MedicalNotificationService(db)

    status_str = (
        "active"
        if alert.is_active
        else "inactive"
    )

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


# ============================================================
# OBTENER RESULTADOS DE LAS ALERTAS
# ============================================================

@router.get("/results")
def get_alert_results(
    user_id: int,
    db: Session = Depends(get_db)
):
    from app.models.medical_alert_result import MedicalAlertResult
    from app.models.medical_notification import MedicalNotification

    results = (
        db.query(
            MedicalAlertResult,
            MedicalNotification
        )
        .join(
            MedicalNotification,
            MedicalAlertResult.alert_id
            == MedicalNotification.id
        )
        .filter(
            MedicalNotification.user_id == user_id
        )
        .order_by(
            MedicalAlertResult.created_at.desc()
        )
        .all()
    )

    output = []

    for res, notif in results:
        output.append({
            "id": res.id,
            "alert_id": res.alert_id,
            "topic": notif.medical_topic,
            "info_type": notif.information_type,
            "summary": res.summary,
            "references": res.references_json,
            "is_read": res.is_read,
            "created_at": res.created_at
        })

    return output


# ============================================================
# MARCAR RESULTADO COMO LEÍDO
# ============================================================

@router.patch("/results/{result_id}/read")
def mark_result_as_read(
    result_id: int,
    db: Session = Depends(get_db)
):
    from app.models.medical_alert_result import MedicalAlertResult

    result = (
        db.query(MedicalAlertResult)
        .filter(
            MedicalAlertResult.id == result_id
        )
        .first()
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Result not found"
        )

    result.is_read = True
    db.commit()

    return {
        "success": True
    }


# ============================================================
# EJECUTAR MANUALMENTE LA ÚLTIMA ALERTA ACTIVA
# ============================================================

@router.post("/test-run/{user_id}")
async def test_run_alert(
    user_id: int,
    db: Session = Depends(get_db)
):
    # Buscar la última alerta activa del usuario
    alert = (
        db.query(MedicalNotification)
        .filter(
            MedicalNotification.user_id == user_id,
            MedicalNotification.status == "active"
        )
        .order_by(
            MedicalNotification.id.desc()
        )
        .first()
    )

    if not alert:
        raise HTTPException(
            status_code=404,
            detail="No hay alertas activas para este usuario"
        )

    try:
        # Ejecutar exactamente el proceso de búsqueda
        # que utiliza el scheduler
        result = await alert_search_service.process_alert(
            db,
            alert
        )

        return {
            "success": True,
            "message": "Alerta ejecutada correctamente",
            "alert_id": alert.id,
            "result_id": result.id,
            "topic": alert.medical_topic,
            "frequency": alert.frequency,
            "source": alert.source
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error ejecutando la alerta: {str(e)}"
        )


# ============================================================
# ACTUALIZAR ALERTA
# ============================================================

@router.patch("/{alert_id}")
def update_alert(
    alert_id: int,
    update_data: MedicalAlertUpdate,
    db: Session = Depends(get_db)
):
    service = MedicalNotificationService(db)

    notif = service.get_notification(
        notification_id=alert_id
    )

    if not notif:
        raise HTTPException(
            status_code=404,
            detail="Alert not found"
        )

    status_str = (
        "active"
        if update_data.is_active
        else "inactive"
    )

    notif = service.update_notification(
        notification_id=alert_id,
        user_id=notif.user_id,
        status=status_str
    )

    return {
        "id": notif.id,
        "is_active": notif.status == "active"
    }