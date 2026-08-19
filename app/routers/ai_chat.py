import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from groq import Groq
from dotenv import load_dotenv


load_dotenv()

router = APIRouter(prefix="/ai", tags=["AI Medical Assistant"])


class ChatRequest(BaseModel):
    prompt: str

@router.post("/chat")
def generate_response(request: ChatRequest):
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        raise HTTPException(
            status_code=500, 
            detail="Falta la variable de entorno GROQ_API_KEY"
        )

    try:
        
        client = Groq(api_key=api_key)
        
        # Realizar la consulta a la API de Groq usando Llama 3
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",  # Modelo rápido y actualizado
            messages=[
                {
                    "role": "system",
                    "content": "Eres un asistente médico inteligente de apoyo. Proporciona respuestas precisas, profesionales, empáticas y breves.",
                },
                {
                    "role": "user", 
                    "content": request.prompt
                },
            ],
            temperature=0.3,
            max_completion_tokens=1024,
        )

        reply_text = completion.choices[0].message.content

        return {
            "status": "success",
            "reply": reply_text
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error al procesar la solicitud con Groq: {str(e)}"
        )