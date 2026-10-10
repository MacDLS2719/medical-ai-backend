from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.deps import get_db
from app.models.transcription_attachment import TranscriptionAttachment
from app.models.user import User


router = APIRouter(tags=["Call Transcriptions"])


@router.get("/call-transcriptions/patients")
def list_transcription_patients(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "doctor":
        raise HTTPException(status_code=403, detail="Solo los médicos pueden consultar este historial")

    grouped_records = (
        db.query(
            TranscriptionAttachment.patient_id,
            func.count(TranscriptionAttachment.id).label("recording_count"),
            func.max(TranscriptionAttachment.recorded_at).label("latest_recorded_at"),
        )
        .filter(TranscriptionAttachment.doctor_id == current_user.id)
        .group_by(TranscriptionAttachment.patient_id)
        .all()
    )
    patient_ids = [record.patient_id for record in grouped_records]
    patients = {
        patient.id: patient
        for patient in db.query(User).filter(User.id.in_(patient_ids)).all()
    } if patient_ids else {}

    return [
        {
            "patient_id": record.patient_id,
            "patient_name": _user_name(patients.get(record.patient_id), "Paciente"),
            "recording_count": record.recording_count,
            "latest_recorded_at": (
                record.latest_recorded_at.isoformat()
                if record.latest_recorded_at
                else None
            ),
        }
        for record in grouped_records
    ]


@router.get("/call-transcriptions/patients/{patient_id}")
def list_patient_call_transcriptions(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "doctor":
        raise HTTPException(status_code=403, detail="Solo los médicos pueden consultar este historial")

    records = (
        db.query(TranscriptionAttachment)
        .filter(
            TranscriptionAttachment.doctor_id == current_user.id,
            TranscriptionAttachment.patient_id == patient_id,
        )
        .order_by(TranscriptionAttachment.recorded_at.desc())
        .all()
    )
    return [_serialize(record, include_text=True) for record in records]


@router.get("/call-transcriptions")
def list_call_transcriptions(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    records = (
        db.query(TranscriptionAttachment)
        .filter(
            or_(
                TranscriptionAttachment.doctor_id == current_user.id,
                TranscriptionAttachment.patient_id == current_user.id,
            )
        )
        .order_by(TranscriptionAttachment.recorded_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [_serialize(record) for record in records]


@router.get("/call-transcriptions/{transcription_id}")
def get_call_transcription(
    transcription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = (
        db.query(TranscriptionAttachment)
        .filter(TranscriptionAttachment.id == transcription_id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Transcripción no encontrada")
    if current_user.id not in (record.doctor_id, record.patient_id):
        raise HTTPException(status_code=403, detail="Sin acceso")
    return _serialize(record, include_text=True)


def _serialize(record: TranscriptionAttachment, include_text: bool = False) -> dict:
    data = {
        "id": record.id,
        "conversation_id": record.conversation_id,
        "patient_id": record.patient_id,
        "doctor_id": record.doctor_id,
        "patient_name": _user_name(record.patient, "Paciente"),
        "doctor_name": _user_name(record.doctor, "Médico"),
        "status": record.status,
        "recording_url": record.recording_url,
        "recording_file_name": record.recording_file_name,
        "transcript_file_url": record.transcript_file_url,
        "transcript_file_name": record.transcript_file_name,
        "recorded_at": record.recorded_at.isoformat() if record.recorded_at else None,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
    }
    if include_text:
        data["transcript_text"] = record.transcript_text
        data["summary_text"] = record.summary_text
        data["error_message"] = record.error_message
    else:
        data["transcript_preview"] = (
            record.transcript_text or record.summary_text or ""
        )[:200] or None
    return data


def _user_name(user: User | None, fallback: str) -> str:
    if not user:
        return fallback
    profile = user.patient or user.doctor
    if profile:
        first_name = getattr(profile, "first_name", "")
        last_name = getattr(profile, "last_name", "")
        name = f"{first_name} {last_name}".strip()
        if name:
            return name
    return user.email
