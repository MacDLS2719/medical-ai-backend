from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import metadata, medical_search, ai_chat, medical_notifications, profile

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

app.include_router(
    medical_notifications.router,
    prefix="/api"
)

app.include_router(
    profile.router,
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