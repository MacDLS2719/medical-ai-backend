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
)

app = FastAPI(
    title="Medical AI API",
    description="API para plataforma de inteligencia artificial médica",
    version="1.0.0",
)

# Set up CORS for frontend connectivity
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(metadata.router)
app.include_router(medical_search.router)
app.include_router(ai_chat.router)

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