import os
import time
import httpx

DAILY_API_KEY = os.getenv("DAILY_API_KEY")
DAILY_API_URL = "https://api.daily.co/v1"

async def create_daily_room(room_name: str) -> dict:
    """
    Crea una sala de videollamada temporal en Daily.co.
    La sala expira automáticamente 2 horas después de crearse.
    """
    headers = {
        "Authorization": f"Bearer {DAILY_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "name": room_name,
        "properties": {
            "exp": int(time.time()) + 7200,   # expira en 2 horas
            "enable_chat": True,
            "enable_screenshare": True,
            "start_video_off": False,
            "start_audio_off": False
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(f"{DAILY_API_URL}/rooms", json=payload, headers=headers)

        if response.status_code not in (200, 201):
            raise Exception(f"Error en Daily.co API: {response.text}")

        return response.json()


async def delete_daily_room(room_name: str):
    """
    Elimina una sala en Daily.co (llamar al colgar para limpiar).
    """
    headers = {
        "Authorization": f"Bearer {DAILY_API_KEY}"
    }
    async with httpx.AsyncClient() as client:
        await client.delete(f"{DAILY_API_URL}/rooms/{room_name}", headers=headers)