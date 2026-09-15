from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: int):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_personal_message(self, message: dict, user_id: int):
        try:
            target_id = int(user_id)
            if target_id in self.active_connections:
                websocket = self.active_connections[target_id]
                await websocket.send_json(message)
                print(f"[WS] Mensaje enviado a user_id={target_id}: action={message.get('action')}")
            else:
                print(f"[WS] AVISO: user_id={target_id} no está en conexiones activas: {list(self.active_connections.keys())}")
        except Exception as e:
            print(f"[WS] Error enviando mensaje a user_id={user_id}: {e}")
            self.disconnect(user_id)

manager = ConnectionManager()

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await manager.connect(websocket, user_id)
    print(f"[WS] Usuario {user_id} conectado correctamente")
    try:
        while True:
            data = await websocket.receive_text()
            import json
            try:
                parsed = json.loads(data)
                action = parsed.get("action")
                target_user = parsed.get("target_user")
                
                if action and target_user is not None:
                    target_id = int(target_user)
                    print(f"[WS] Reenviando {action} de user {user_id} a target {target_id}")
                    # Forward the message to the target user
                    await manager.send_personal_message({
                        "action": action,
                        "from_user": user_id,
                        **parsed
                    }, target_id)
            except Exception as parse_err:
                print(f"[WS] Error procesando JSON de user {user_id}: {parse_err}")
                
    except WebSocketDisconnect:
        print(f"[WS] Usuario {user_id} desconectado")
        manager.disconnect(user_id)

