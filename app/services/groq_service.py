import os
from typing import Optional

from groq import Groq


class GroqService:

    def __init__(self):

        self.api_key = os.getenv("GROQ_API_KEY")

        if not self.api_key:
            raise ValueError(
                "Falta la variable de entorno GROQ_API_KEY"
            )

        self.model = os.getenv(
            "GROQ_MODEL",
            "openai/gpt-oss-120b"
        )

        self.client = Groq(
            api_key=self.api_key
        )

    def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_completion_tokens: int = 2048,
    ) -> dict:

        if not prompt.strip():
            raise ValueError(
                "El prompt no puede estar vacío"
            )

        if system_prompt is None:

            system_prompt = (
                "Eres un asistente médico especializado "
                "en análisis de evidencia científica. "

                "Tu función es explicar información científica "
                "obtenida de fuentes médicas confiables. "

                "Debes utilizar únicamente la evidencia "
                "proporcionada en el contexto. "

                "No inventes estudios, autores, resultados, "
                "tratamientos, estadísticas ni referencias. "

                "Si existen diferentes tipos de evidencia, "
                "diferéncialos claramente. "

                "Cuando exista evidencia contradictoria, "
                "indícalo. "

                "Cuando la evidencia sea insuficiente, "
                "indícalo claramente. "

                "Explica la información utilizando un "
                "lenguaje comprensible para el usuario. "

                "La información es de carácter informativo "
                "y no sustituye la valoración de un "
                "profesional de la salud."
            )

        try:

            completion = (
                self.client
                .chat
                .completions
                .create(
                    model=self.model,

                    messages=[
                        {
                            "role": "system",
                            "content": system_prompt,
                        },
                        {
                            "role": "user",
                            "content": prompt,
                        },
                    ],

                    temperature=temperature,

                    max_completion_tokens=(
                        max_completion_tokens
                    ),
                )
            )

            reply = (
                completion
                .choices[0]
                .message
                .content
            )

            usage = completion.usage

            tokens_used = None

            if usage:
                tokens_used = getattr(
                    usage,
                    "total_tokens",
                    None
                )

            return {
                "response": reply,
                "model": self.model,
                "tokens_used": tokens_used,
            }

        except Exception as e:

            raise RuntimeError(
                f"Error al generar respuesta con Groq: {str(e)}"
            ) from e