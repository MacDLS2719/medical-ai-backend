"""
Servicio para interactuar con la API de Daily.co.
Incluye creación y eliminación de salas de videollamada.
"""

import time
import httpx

from app.core.config import settings

DAILY_API_KEY = settings.DAILY_API_KEY
DAILY_API_URL = "https://api.daily.co/v1"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {DAILY_API_KEY}",
        "Content-Type": "application/json",
    }


# ---------------------------------------------------------------------------
# Salas
# ---------------------------------------------------------------------------

async def create_daily_room(room_name: str) -> dict:
    """
    Crea una sala de videollamada temporal. La sala expira automáticamente
    2 horas después de crearse.
    """
    payload = {
        "name": room_name,
        "properties": {
            "exp": int(time.time()) + 7200,   # expira en 2 horas
            "enable_chat": True,
            "enable_screenshare": True,
            "start_video_off": False,
            "start_audio_off": False,
        },
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{DAILY_API_URL}/rooms",
            json=payload,
            headers=_headers(),
        )

        if response.status_code not in (200, 201):
            raise Exception(f"Error en Daily.co API: {response.text}")

        return response.json()


async def delete_daily_room(room_name: str) -> None:
    """
    Elimina una sala en Daily.co (llamar al colgar para limpiar).
    """
    async with httpx.AsyncClient() as client:
        await client.delete(
            f"{DAILY_API_URL}/rooms/{room_name}",
            headers=_headers(),
        )
