# app/services/deepgram_service.py
"""
Servicio de transcripción de audio con Deepgram.

Usa la API REST de Deepgram (no el SDK) para mantener la
dependencia mínima: solo httpx (ya instalado en el proyecto).

Endpoint:
    POST https://api.deepgram.com/v1/listen
    Headers: Authorization: Token <API_KEY>
    Body: bytes del audio
    Query params: model, language, smart_format, punctuate

Retorna el texto transcrito o cadena vacía si falla.
"""

import httpx
from app.core.config import settings


DEEPGRAM_URL = "https://api.deepgram.com/v1/listen"


async def transcribe_audio(audio_bytes: bytes, content_type: str = "audio/webm") -> str:
    """
    Envía el audio a Deepgram y retorna la transcripción como texto plano.

    Parameters
    ----------
    audio_bytes:
        Bytes crudos del archivo de audio grabado por el navegador.
    content_type:
        MIME type del audio. Normalmente 'audio/webm' (MediaRecorder Chrome/Firefox)
        o 'audio/ogg'. Deepgram lo detecta automáticamente si no se especifica.

    Returns
    -------
    str
        Texto transcrito. Cadena vacía si no hay transcripción o si ocurre un error.
    """

    api_key = settings.DEEPGRAM

    if not api_key:
        raise ValueError("DEEPGRAM API key no configurada en el .env")

    params = {
        "model": "nova-2",
        "smart_format": "true",
        "punctuate": "true",
        "detect_language": "true", # Deepgram detecta si es en/es/etc.
    }

    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": content_type,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                DEEPGRAM_URL,
                content=audio_bytes,
                headers=headers,
                params=params,
            )
            response.raise_for_status()
            data = response.json()

        # Deepgram devuelve:
        # results.channels[0].alternatives[0].transcript
        transcript = (
            data
            .get("results", {})
            .get("channels", [{}])[0]
            .get("alternatives", [{}])[0]
            .get("transcript", "")
            or ""
        )

        print(f"[Deepgram] Transcripción: {transcript!r}")
        return transcript.strip()

    except httpx.HTTPStatusError as exc:
        print(f"[Deepgram] HTTP error {exc.response.status_code}: {exc.response.text}")
        raise
    except Exception as exc:
        print(f"[Deepgram] Error inesperado: {exc}")
        raise
