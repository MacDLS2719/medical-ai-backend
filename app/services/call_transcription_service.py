import asyncio
import io
import logging
import os
import uuid
from datetime import datetime

import cloudinary
import httpx
from fastapi import UploadFile
from openai import AsyncOpenAI
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.medical_conversation import MedicalConversation
from app.models.transcription_attachment import TranscriptionAttachment
from app.routers.websockets import manager as ws_manager

logger = logging.getLogger(__name__)


class CallTranscriptionPipeline:
    """
    Orquesta el flujo completo de videollamada:
    Audio grabado -> Cloudinary -> tabla de transcripciones -> OpenAI -> resumen
    """

    MAX_TRANSCRIPTION_SIZE = 25 * 1024 * 1024

    @staticmethod
    async def _download_bytes(url: str) -> bytes:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content

    @staticmethod
    async def _transcribe_audio(audio_bytes: bytes, filename: str, content_type: str) -> str:
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY no está configurada para transcribir el audio.")
        if len(audio_bytes) > CallTranscriptionPipeline.MAX_TRANSCRIPTION_SIZE:
            raise ValueError(
                "La grabación supera el límite de 25 MB de OpenAI. "
                "Divide la llamada en grabaciones más cortas e inténtalo de nuevo."
            )

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        result = await client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=(filename, audio_bytes, content_type.split(";", 1)[0]),
            language="es",
            prompt="Transcripción en español de una consulta médica.",
        )
        return result.text.strip()

    @staticmethod
    async def _generate_summary(
        transcript: str,
        recording_label: str = "Videollamada",
    ) -> str:
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            return (
                "MOTIVO DE CONSULTA:\nConsulta registrada.\n\n"
                "EXPLORACIÓN FÍSICA:\nNo referida o no evaluada en esta sesión.\n\n"
                "IMPRESIÓN DIAGNÓSTICA:\nPendiente de evaluación médica.\n\n"
                "PLAN Y TRATAMIENTO:\nSe registró la sesión correctamente, pero OpenAI no está configurado."
            )

        client = AsyncOpenAI(api_key=api_key)
        prompt = (
            f"Analiza la siguiente transcripción de una consulta médica ({recording_label}) en español y "
            "genera el INFORME MÉDICO estructurado obligatoriamente con estas 4 secciones en mayúsculas:\n\n"
            "MOTIVO DE CONSULTA:\n"
            "[Describe los síntomas, motivo principal o causa que motivó la consulta según lo conversado]\n\n"
            "EXPLORACIÓN FÍSICA:\n"
            "[Detalla hallazgos referidos, observados o explorados durante la sesión. Si no se realizó o no se mencionaron, indica: 'No referida o no evaluada en esta sesión']\n\n"
            "IMPRESIÓN DIAGNÓSTICA:\n"
            "[Diagnóstico(s) presuntivo(s), diferencial(es) o confirmado(s) mencionados en la conversación]\n\n"
            "PLAN Y TRATAMIENTO:\n"
            "[Indicaciones, medicamentos, dosis recomendadas, estudios o exámenes solicitados, recomendaciones y citas de seguimiento]\n\n"
            "Reglas estrictas:\n"
            "- Sé 100% fiel al audio transcrito. No inventes síntomas, diagnósticos ni medicamentos que no figuren en la transcripción.\n"
            "- Si es una grabación breve o de prueba, resume brevemente lo expresado en la sección correspondiente sin inventar patologías.\n"
            "- Conserva siempre los 4 encabezados indicados.\n\n"
            f"<transcripcion>\n{transcript[:12000]}\n</transcripcion>"
        )

        completion = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un asistente médico clínico para la plataforma Mivor. Redactas informes médicos formales, "
                        "estructurados y fieles a las consultas transcritas."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=1500,
        )

        return completion.choices[0].message.content.strip() or "Resumen no disponible."

    @staticmethod
    def _create_document_payload(
        summary: str,
        transcript: str,
        recording_label: str = "VIDEOLLAMADA",
    ) -> tuple[bytes, str, str]:
        text = (
            f"INFORME MÉDICO - {recording_label}\n\n"
            f"{summary}\n\n"
            "--- TRANSCRIPCIÓN COMPLETA ---\n"
            f"{transcript}"
        )
        return text.encode("utf-8-sig"), "informe_medico_y_transcripcion.txt", "text/plain; charset=utf-8"

    @staticmethod
    async def _upload_to_cloudinary(file_bytes: bytes, filename: str, folder: str, resource_type: str = "video") -> dict:
        stem, extension = os.path.splitext(filename)
        unique_name = f"{stem}_{uuid.uuid4().hex[:10]}"
        public_id = f"{unique_name}{extension}" if resource_type == "raw" else unique_name
        if resource_type == "video" or len(file_bytes) > 10 * 1024 * 1024:
            result = await asyncio.to_thread(
                cloudinary.uploader.upload_large,
                io.BytesIO(file_bytes),
                folder=folder,
                resource_type=resource_type,
                public_id=public_id,
                chunk_size=6000000,  # 6 MB chunks
            )
        else:
            result = await asyncio.to_thread(
                cloudinary.uploader.upload,
                io.BytesIO(file_bytes),
                folder=folder,
                resource_type=resource_type,
                public_id=public_id,
            )

        return {
            "public_id": result.get("public_id"),
            "file_url": result.get("secure_url"),
            "secure_url": result.get("secure_url"),
            "file_name": filename,
            "mime_type": result.get("resource_type", "application/octet-stream"),
            "file_size": result.get("bytes", 0),
            "storage_disk": "cloudinary",
        }

    @staticmethod
    async def process_call_recording(
        db: Session,
        conversation_id: int,
        sender_id: int,
        audio_url: str | None = None,
        audio_file: UploadFile | None = None,
        file_name: str = "recording.webm",
    ):
        conversation = db.query(MedicalConversation).filter(
            MedicalConversation.id == conversation_id,
            (
                (MedicalConversation.patient_id == sender_id)
                | (MedicalConversation.doctor_id == sender_id)
            ),
        ).first()

        if not conversation:
            raise ValueError("Conversación no encontrada o no autorizada para este usuario.")

        patient_id = conversation.patient_id
        doctor_id = conversation.doctor_id
        db.rollback()

        if audio_file is not None:
            await audio_file.seek(0)
            audio_bytes = await audio_file.read()
            original_filename = audio_file.filename or file_name
            content_type = audio_file.content_type or "audio/webm"
        elif audio_url:
            audio_bytes = await CallTranscriptionPipeline._download_bytes(audio_url)
            original_filename = file_name or "recording.webm"
            content_type = "audio/webm"
        else:
            raise ValueError("Se requiere un audio de la videollamada o una URL con el archivo grabado.")

        return await CallTranscriptionPipeline._process_recording(
            db=db,
            conversation_id=conversation_id,
            patient_id=patient_id,
            doctor_id=doctor_id,
            audio_bytes=audio_bytes,
            original_filename=original_filename,
            content_type=content_type,
            storage_folder=f"medical_conversations/{conversation_id}",
        )

    @staticmethod
    async def process_doctor_recording(
        db: Session,
        doctor_id: int,
        audio_file: UploadFile,
    ):
        await audio_file.seek(0)
        audio_bytes = await audio_file.read()
        if not audio_bytes:
            raise ValueError("La grabación está vacía. Graba audio antes de transcribir.")
        db.rollback()

        return await CallTranscriptionPipeline._process_recording(
            db=db,
            conversation_id=None,
            patient_id=None,
            doctor_id=doctor_id,
            audio_bytes=audio_bytes,
            original_filename=audio_file.filename or "doctor-recording.webm",
            content_type=audio_file.content_type or "audio/webm",
            storage_folder=f"doctor_transcriptions/{doctor_id}",
        )

    @staticmethod
    async def _process_recording(
        db: Session,
        conversation_id: int | None,
        patient_id: int | None,
        doctor_id: int,
        audio_bytes: bytes,
        original_filename: str,
        content_type: str,
        storage_folder: str,
    ):
        folder_path = f"{storage_folder}/recordings"
        audio_upload = await CallTranscriptionPipeline._upload_to_cloudinary(
            file_bytes=audio_bytes,
            filename=original_filename,
            folder=folder_path,
            resource_type="video",
        )

        transcription_attachment = TranscriptionAttachment(
            conversation_id=conversation_id,
            patient_id=patient_id,
            doctor_id=doctor_id,
            recording_url=audio_upload["secure_url"],
            recording_public_id=audio_upload["public_id"],
            recording_file_name=original_filename[:255],
            recording_mime_type=content_type[:100],
            recording_file_size=audio_upload["file_size"],
            recorded_at=datetime.utcnow(),
            status="processing",
        )
        db.add(transcription_attachment)
        db.commit()
        db.refresh(transcription_attachment)
        transcription_attachment_id = transcription_attachment.id

        logger.info(
            "[CallTranscription] Enviando %s bytes a OpenAI para transcripción.",
            len(audio_bytes),
        )
        try:
            transcript = await CallTranscriptionPipeline._transcribe_audio(
                audio_bytes,
                original_filename,
                content_type or "audio/webm",
            )
            if not transcript:
                error_message = (
                    "OpenAI no detectó voz en el audio. Comprueba el micrófono o la fuente de audio "
                    "compartida y vuelve a grabar."
                )
                transcription_attachment.status = "failed"
                transcription_attachment.error_message = error_message
                db.commit()
                logger.warning(
                    "OpenAI returned an empty transcript (conversation_id=%s, audio_bytes=%s)",
                    conversation_id or "doctor-only",
                    len(audio_bytes),
                )
                return {
                    "status": "transcription_failed",
                    "error": error_message,
                    "transcription_attachment_id": transcription_attachment.id,
                    "recording_url": transcription_attachment.recording_url,
                }

            recording_label = "GRABACIÓN PERSONAL / PRESENCIAL" if conversation_id is None else "VIDEOLLAMADA"
            summary = await CallTranscriptionPipeline._generate_summary(
                transcript,
                recording_label=recording_label,
            )
            document_name = "informe_medico_y_transcripcion.txt"
            document_bytes, _, _ = CallTranscriptionPipeline._create_document_payload(
                summary,
                transcript,
                recording_label,
            )
            document_upload = None
            try:
                document_upload = await CallTranscriptionPipeline._upload_to_cloudinary(
                    file_bytes=document_bytes,
                    filename=document_name,
                    folder=f"{storage_folder}/documents",
                    resource_type="raw",
                )
            except Exception as document_error:
                logger.warning(
                    "[CallTranscription] No se pudo subir el resumen a Cloudinary: %s",
                    document_error,
                )

            if document_upload:
                transcription_attachment.transcript_file_url = document_upload["secure_url"]
                transcription_attachment.transcript_file_public_id = document_upload["public_id"]
                transcription_attachment.transcript_file_name = document_name

            transcription_attachment.transcript_text = transcript
            transcription_attachment.summary_text = summary
            transcription_attachment.status = "completed"
            transcription_attachment.error_message = (
                "No se pudo subir el archivo de resumen a Cloudinary; el resumen y la transcripción se conservaron en la base de datos."
                if not document_upload
                else None
            )
            db.commit()
        except Exception as exc:
            db.rollback()
            failed_record = db.query(TranscriptionAttachment).filter(
                TranscriptionAttachment.id == transcription_attachment_id,
            ).first()
            if failed_record:
                failed_record.status = "failed"
                failed_record.error_message = str(exc)[:2000]
                db.commit()
            logger.exception(
                "[CallTranscription] No se pudo completar la transcripción (id=%s).",
                transcription_attachment_id,
            )
            raise

        return {
            "transcription_attachment_id": transcription_attachment.id,
            "recording_url": transcription_attachment.recording_url,
            "transcript_file_url": transcription_attachment.transcript_file_url,
            "transcript": transcript,
            "summary": summary,
            "recorded_at": transcription_attachment.recorded_at.isoformat(),
        }