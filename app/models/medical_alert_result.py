from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base

class MedicalAlertResult(Base):
    __tablename__ = "medical_alert_results"

    id = Column(Integer, primary_key=True, index=True)
    
    alert_id = Column(
        Integer, 
        ForeignKey("medical_notifications.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    
    summary = Column(Text, nullable=False)
    
    # Lista de referencias almacenadas como JSON string
    references_json = Column(Text, nullable=False) 
    
    is_read = Column(Boolean, nullable=False, default=False)
    
    created_at = Column(
        DateTime, 
        nullable=False, 
        server_default=func.now()
    )

    alert = relationship(
        "MedicalNotification", 
        backref="results"
    )
