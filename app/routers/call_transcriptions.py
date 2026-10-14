import logging
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.deps import get_db
from app.services.call_transcription_service import CallTranscriptionPipeline
from app.services.transcription_pdf_service import (
    create_clinical_report_pdf,
    create_transcription_pdf,
    create_transcription_report_pdf,
)
from app.models.transcription_attachment import TranscriptionAttachment
from app.models.user import User


router = APIRouter(tags=["Call Transcriptions"])
logger = logging.getLogger(__name__)


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
        .filter(
            TranscriptionAttachment.doctor_id == current_user.id,
            TranscriptionAttachment.patient_id.isnot(None),
        )
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


@router.get("/call-transcriptions/doctor")
def list_doctor_transcriptions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "doctor":
        raise HTTPException(status_code=403, detail="Solo los médicos pueden consultar este historial")

    records = (
        db.query(TranscriptionAttachment)
        .filter(
            TranscriptionAttachment.doctor_id == current_user.id,
            TranscriptionAttachment.conversation_id.is_(None),
        )
        .order_by(TranscriptionAttachment.recorded_at.desc())
        .all()
    )
    return [_serialize(record, include_text=True) for record in records]


@router.post("/call-transcriptions/doctor")
async def create_doctor_transcription(
    audio_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "doctor":
        raise HTTPException(status_code=403, detail="Solo los médicos pueden crear transcripciones personales")

    doctor_id = current_user.id
    try:
        result = await CallTranscriptionPipeline.process_doctor_recording(
            db=db,
            doctor_id=doctor_id,
            audio_file=audio_file,
        )
        if result.get("status") == "transcription_failed":
            raise HTTPException(status_code=422, detail=result["error"])
        return {"status": "ok", "data": result}
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Error procesando una grabación personal del médico %s", doctor_id)
        raise HTTPException(status_code=500, detail=f"Error procesando la grabación: {exc}")


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


@router.post("/call-transcriptions/{transcription_id}/approve")
def approve_call_transcription_summary(
    transcription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "doctor":
        raise HTTPException(status_code=403, detail="Solo los médicos pueden aprobar resúmenes")

    record = (
        db.query(TranscriptionAttachment)
        .filter(
            TranscriptionAttachment.id == transcription_id,
            TranscriptionAttachment.doctor_id == current_user.id,
        )
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Transcripción no encontrada")
    if record.patient_id is None:
        raise HTTPException(
            status_code=400,
            detail="Las grabaciones personales no se comparten con pacientes.",
        )
    if record.status != "completed" or not record.summary_text:
        raise HTTPException(
            status_code=409,
            detail="Solo se puede aprobar un resumen completado.",
        )

    if not record.summary_approved:
        record.summary_approved = True
        record.summary_approved_at = datetime.utcnow()
        db.commit()
        db.refresh(record)
    return _serialize(record, include_text=True)


@router.get("/call-transcriptions/patient")
def list_patient_transcriptions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "patient":
        raise HTTPException(status_code=403, detail="Solo los pacientes pueden consultar sus informes")

    records = (
        db.query(TranscriptionAttachment)
        .filter(
            TranscriptionAttachment.patient_id == current_user.id,
        )
        .order_by(TranscriptionAttachment.recorded_at.desc())
        .all()
    )
    return [
        _serialize(
            record,
            include_text=record.summary_approved,
            include_preview=False,
        )
        for record in records
    ]


def _get_authorized_record(
    db: Session,
    transcription_id: int,
    current_user: User,
) -> TranscriptionAttachment:
    record = (
        db.query(TranscriptionAttachment)
        .filter(TranscriptionAttachment.id == transcription_id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Transcripción no encontrada")
    if current_user.id == record.doctor_id and current_user.role == "doctor":
        return record
    if (
        current_user.role == "patient"
        and current_user.id == record.patient_id
        and record.summary_approved
    ):
        return record
    raise HTTPException(status_code=403, detail="Sin acceso al informe o transcripción")


def _format_spanish_datetime(dt: datetime | None) -> str:
    if not dt:
        return "Fecha no disponible"
    meses = [
        "", "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ]
    return f"{dt.day} de {meses[dt.month]} de {dt.year}, {dt.strftime('%H:%M')}"


def _patient_gender(user: User | None) -> str:
    if not user:
        return "No especificado"
    patient_profile = getattr(user, "patient", None)
    if patient_profile and getattr(patient_profile, "gender", None):
        return patient_profile.gender
    return "No especificado"


@router.get("/call-transcriptions/{transcription_id}/clinical-report.pdf")
def download_clinical_report(
    transcription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Descarga el INFORME MÉDICO oficial generado por la IA en formato PDF.
    Contiene: Servicio, Medicina General, Fecha, Datos del Paciente (Nombre, Sexo),
    Motivo de consulta, Exploración física, Impresión diagnóstica y Plan y tratamiento.
    """
    record = _get_authorized_record(db, transcription_id, current_user)
    if not record.summary_text:
        raise HTTPException(status_code=409, detail="El informe médico aún no está completo.")

    service_type = "Videollamada" if record.conversation_id is not None else "Presencial"
    date_str = _format_spanish_datetime(record.recorded_at or record.created_at)
    patient_name = _user_name(
        record.patient,
        "Consulta personal / presencial" if record.conversation_id is None else "Paciente",
    )
    patient_gender = _patient_gender(record.patient)
    doctor_name = _user_name(record.doctor, "Médico tratante")

    pdf = create_clinical_report_pdf(
        service_type=service_type,
        specialty="Medicina General",
        date_str=date_str,
        patient_name=patient_name,
        patient_gender=patient_gender,
        doctor_name=doctor_name,
        summary=record.summary_text,
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="informe-medico-{record.id}.pdf"',
            "Cache-Control": "private, no-store",
        },
    )


@router.get("/call-transcriptions/{transcription_id}/transcript.pdf")
def download_transcript_pdf(
    transcription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Descarga la TRANSCRIPCIÓN COMPLETA del audio de la consulta médica en formato PDF.
    """
    record = _get_authorized_record(db, transcription_id, current_user)
    if not record.transcript_text:
        raise HTTPException(status_code=409, detail="La transcripción de audio aún no está disponible.")

    service_type = "Videollamada" if record.conversation_id is not None else "Presencial"
    date_str = _format_spanish_datetime(record.recorded_at or record.created_at)
    patient_name = _user_name(
        record.patient,
        "Consulta personal / presencial" if record.conversation_id is None else "Paciente",
    )
    doctor_name = _user_name(record.doctor, "Médico tratante")

    pdf = create_transcription_pdf(
        service_type=service_type,
        specialty="Medicina General",
        date_str=date_str,
        patient_name=patient_name,
        doctor_name=doctor_name,
        transcript=record.transcript_text,
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="transcripcion-{record.id}.pdf"',
            "Cache-Control": "private, no-store",
        },
    )


@router.get("/call-transcriptions/{transcription_id}/report.pdf")
def download_call_transcription_report(
    transcription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return download_clinical_report(transcription_id, db, current_user)


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
                and_(
                    TranscriptionAttachment.doctor_id == current_user.id,
                    current_user.role == "doctor",
                ),
                and_(
                    TranscriptionAttachment.patient_id == current_user.id,
                    TranscriptionAttachment.summary_approved.is_(True),
                    current_user.role == "patient",
                ),
            )
        )
        .order_by(TranscriptionAttachment.recorded_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [
        _serialize(record, include_preview=current_user.role != "patient")
        for record in records
    ]


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
    is_patient = current_user.role == "patient"
    return _serialize(
        record,
        include_text=not is_patient or record.summary_approved,
        include_preview=not is_patient,
    )


def _serialize(
    record: TranscriptionAttachment,
    include_text: bool = False,
    include_preview: bool = True,
) -> dict:
    data = {
        "id": record.id,
        "conversation_id": record.conversation_id,
        "patient_id": record.patient_id,
        "doctor_id": record.doctor_id,
        "patient_name": _user_name(record.patient, "Paciente"),
        "doctor_name": _user_name(record.doctor, "Médico"),
        "status": record.status,
        "summary_approved": record.summary_approved,
        "summary_approved_at": (
            record.summary_approved_at.isoformat()
            if record.summary_approved_at
            else None
        ),
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
    elif include_preview:
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
