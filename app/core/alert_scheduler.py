from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.core.database import SessionLocal
from app.models.medical_notification import MedicalNotification
from app.services.rag.research.alert_search_service import alert_search_service
import datetime

scheduler = AsyncIOScheduler()

async def process_active_alerts():
    db = SessionLocal()
    try:
        # Buscamos las alertas activas (su status es "active" o boolean is_active, 
        # en la migración vimos que se usa is_active pero el modelo dice status='active', 
        # sin embargo, busquemos todas las que no digan inactivo).
        # Ajustar según como se guarde realmente:
        active_alerts = db.query(MedicalNotification).filter(MedicalNotification.status == "active").all()
        
        for alert in active_alerts:
            try:
                # Aquí se podría chequear frequency == "Diario", etc.
                await alert_search_service.process_alert(db, alert)
                print(f"[Alert Scheduler] Procesada alerta {alert.id}")
            except Exception as e:
                print(f"[Alert Scheduler] Error procesando alerta {alert.id}: {e}")
                
    except Exception as e:
        print(f"[Alert Scheduler] Error general: {e}")
    finally:
        db.close()

def start_scheduler():
    scheduler.add_job(process_active_alerts, "interval", hours=24, id="daily_alerts")
    scheduler.start()
