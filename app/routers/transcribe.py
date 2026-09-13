# app/routers/transcribe.py
"""
Endpoint de transcripción de audio con Deepgram.
Soporta transcripción en tiempo real vía WebSocket y por archivo vía POST.
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, WebSocket, WebSocketDisconnect
from typing import Optional
import asyncio
import websockets
import json

from app.services.deepgram_service import transcribe_audio
from app.core.config import settings

router = APIRouter(
    prefix="/api/transcribe",
    tags=["Transcription"],
)

@router.websocket("/stream")
async def transcribe_stream(websocket: WebSocket, language: str = "es"):
    """
    Recibe audio en tiempo real del frontend y lo envía a Deepgram.
    Retorna transcripciones parciales y finales en tiempo real.
    """
    await websocket.accept()
    
    api_key = settings.DEEPGRAM
    if not api_key:
        await websocket.close(code=1011, reason="API key missing")
        return

    # Conectar a Deepgram (streaming no soporta detect_language, requiere el idioma)
    deepgram_url = f"wss://api.deepgram.com/v1/listen?model=nova-2&language={language}&smart_format=true&interim_results=true&punctuate=true"
    
    try:
        async with websockets.connect(
            deepgram_url, 
            additional_headers={"Authorization": f"Token {api_key}"}
        ) as dg_socket:
            
            async def sender():
                try:
                    while True:
                        data = await websocket.receive()
                        if "bytes" in data:
                            await dg_socket.send(data["bytes"])
                        elif "text" in data:
                            # Frontend puede mandar mensajes de control (ej. close)
                            msg = json.loads(data["text"])
                            if msg.get("type") == "close":
                                await dg_socket.send(json.dumps({"type": "CloseStream"}))
                                break
                except WebSocketDisconnect:
                    try:
                        await dg_socket.send(json.dumps({"type": "CloseStream"}))
                    except:
                        pass
                except Exception as e:
                    print(f"Error reading from client: {e}")

            async def receiver():
                try:
                    while True:
                        response = await dg_socket.recv()
                        data = json.loads(response)
                        
                        transcript = (
                            data.get("channel", {})
                            .get("alternatives", [{}])[0]
                            .get("transcript", "")
                        )
                        is_final = data.get("is_final", False)
                        
                        if transcript:
                            await websocket.send_json({
                                "transcript": transcript,
                                "is_final": is_final
                            })
                except websockets.exceptions.ConnectionClosed:
                    pass
                except Exception as e:
                    print(f"Error reading from Deepgram: {e}")

            await asyncio.gather(sender(), receiver())
            
    except Exception as e:
        print(f"Error connecting to Deepgram: {e}")
    finally:
        try:
            await websocket.close()
        except:
            pass


@router.post("")
async def transcribe(
    audio: UploadFile = File(..., description="Archivo de audio grabado por el navegador"),
    language: Optional[str] = Form(default="es", description="Código de idioma: 'es', 'en', etc."),
):
    """
    Endpoint alternativo por si falla WebSocket.
    """
    if not audio:
        raise HTTPException(status_code=400, detail="No se recibió archivo de audio.")

    audio_bytes = await audio.read()

    if not audio_bytes:
        raise HTTPException(status_code=400, detail="El archivo de audio está vacío.")

    content_type = audio.content_type or "audio/webm"

    try:
        transcript = await transcribe_audio(
            audio_bytes=audio_bytes,
            content_type=content_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Error al transcribir con Deepgram: {exc}",
        )

    return {"transcript": transcript}
