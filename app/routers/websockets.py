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
        if user_id in self.active_connections:
            websocket = self.active_connections[user_id]
            try:
                await websocket.send_json(message)
            except Exception:
                self.disconnect(user_id)

manager = ConnectionManager()

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Can be used to handle messages from the client if needed
            # e.g., CALL_ACCEPTED, CALL_REJECTED
            
            import json
            try:
                parsed = json.loads(data)
                action = parsed.get("action")
                target_user = parsed.get("target_user")
                
                if action and target_user:
                    # Forward the message to the target user
                    await manager.send_personal_message({
                        "action": action,
                        "from_user": user_id,
                        **parsed
                    }, int(target_user))
            except:
                pass
                
    except WebSocketDisconnect:
        manager.disconnect(user_id)
