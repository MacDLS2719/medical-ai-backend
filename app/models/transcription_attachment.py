from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class TranscriptionAttachment(Base):
    __tablename__ = "transcription_attachments"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(
        Integer,
        ForeignKey("medical_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    patient_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    doctor_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    recording_url = Column(String(2000), nullable=False)
    recording_public_id = Column(String(500), nullable=True)
    recording_file_name = Column(String(255), nullable=False)
    recording_mime_type = Column(String(100), nullable=False)
    recording_file_size = Column(BigInteger, nullable=True)

    transcript_file_url = Column(String(2000), nullable=True)
    transcript_file_public_id = Column(String(500), nullable=True)
    transcript_file_name = Column(String(255), nullable=True)
    transcript_text = Column(Text, nullable=True)
    summary_text = Column(Text, nullable=True)

    status = Column(
        String(30),
        nullable=False,
        default="processing",
        server_default="processing",
        index=True,
    )
    error_message = Column(Text, nullable=True)
    recorded_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    conversation = relationship("MedicalConversation")
    patient = relationship("User", foreign_keys=[patient_id])
    doctor = relationship("User", foreign_keys=[doctor_id])
