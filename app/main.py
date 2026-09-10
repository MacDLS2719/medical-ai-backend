from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.routers import (
    metadata,
    medical_search,
    ai_chat,
    medical_notifications,
    profile,
    medical_conversations,
    medical_appointments,
    doctor_profile,
    medical_alerts,
    websockets,
    doctor_verification,
)

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import re

app = FastAPI(
    title="Medical AI API",
    description="API para plataforma de inteligencia artificial médica",
    version="1.0.0",
)

# Middleware para normalizar barras dobles y prefijo /api
class PathNormalizationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = re.sub(r'/+', '/', request.scope.get("path", ""))
        
        # Si la ruta no empieza por /api y no es archivos / health / root, anteponer /api
        if not path.startswith("/api") and not path.startswith("/archivos") and path not in ["/", "/health", ""]:
            path = "/api" + path
            
        request.scope["path"] = path
        return await call_next(request)

# CORS debe registrarse PRIMERO para que envuelva todo el stack
# (en FastAPI/Starlette los middlewares se aplican en orden inverso al registro)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(PathNormalizationMiddleware)

app.include_router(metadata.router)
app.include_router(medical_search.router)
app.include_router(ai_chat.router)
app.include_router(medical_alerts.router)

# Mount the static files directory
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
archivos_dir = os.path.join(current_dir, "archivos")
if not os.path.exists(archivos_dir):
    os.makedirs(archivos_dir)
app.mount("/archivos", StaticFiles(directory=archivos_dir), name="archivos")

app.include_router(
    medical_notifications.router,
    prefix="/api"
)

app.include_router(
    profile.router,
    prefix="/api"
)

app.include_router(
    doctor_profile.router,
    prefix="/api"
)

app.include_router(
    medical_conversations.router,
    prefix="/api"
)

app.include_router(
    medical_appointments.router,
    prefix="/api"
)

app.include_router(
    websockets.router,
    prefix="/api"
)

app.include_router(
    doctor_verification.router,
    prefix="/api"
)


@app.get("/")
def root():
    return {
        "message": "Medical AI API funcionando correctamente",
        "version": "1.0.0",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "medical-ai-api",
    }
