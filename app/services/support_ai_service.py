import logging
import os
from typing import Dict, List, Optional

from dotenv import load_dotenv
from openai import (
    APIConnectionError,
    APIError,
    AsyncOpenAI,
    AuthenticationError,
    RateLimitError,
)

from app.prompts.support_ai_prompt import (
    SUPPORT_AI_SYSTEM_PROMPT,
    SUPPORT_CONTACT_FOOTER,
)

load_dotenv()
logger = logging.getLogger(__name__)


class SupportAIService:
    """
    Servicio encargado de comunicarse con OpenAI para proporcionar soporte
    a los usuarios de la plataforma MIVOR (tanto pacientes como médicos).
    Gestiona la selección del modelo, la integración con la API y el manejo de errores.
    """

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")

        if not self.api_key:
            logger.warning(
                "OPENAI_API_KEY no está configurada en las variables de entorno."
            )

        # Selección de modelo: variable específica para soporte, o modelo general de OpenAI, o gpt-4o por defecto
        self.model = (
            os.getenv("OPENAI_SUPPORT_MODEL")
            or os.getenv("OPENAI_MODEL")
            or "gpt-4o"
        )

        self._client: Optional[AsyncOpenAI] = None

    @property
    def client(self) -> AsyncOpenAI:
        """
        Inicialización perezosa (lazy) del cliente AsyncOpenAI.
        """
        if self._client is None:
            if not self.api_key:
                self.api_key = os.getenv("OPENAI_API_KEY")
                if not self.api_key:
                    raise RuntimeError(
                        "OPENAI_API_KEY no está configurada en las variables de entorno."
                    )

            self._client = AsyncOpenAI(api_key=self.api_key)

        return self._client

    async def ask(
        self,
        message: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """
        Envía la consulta del usuario al modelo de OpenAI junto con el contexto del hilo
        y devuelve la respuesta generada garantizando las directrices de soporte y contacto.
        """
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": SUPPORT_AI_SYSTEM_PROMPT}
        ]

        if history:
            messages.extend(history)

        messages.append({"role": "user", "content": message})

        try:
            logger.info(
                f"Enviando consulta a OpenAI utilizando el modelo: {self.model}"
            )

            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=1000,
            )

            choice = completion.choices[0]
            answer = (choice.message.content or "").strip()

            # Asegurar que la respuesta siempre incluya los datos de contacto
            if "soporte@mivor.com" not in answer.lower():
                answer = f"{answer}\n\n{SUPPORT_CONTACT_FOOTER}"

            return answer

        except AuthenticationError as exc:
            logger.error(f"Error de autenticación con OpenAI: {exc}")
            raise RuntimeError(
                "Error de autenticación con el servicio de IA de soporte."
            ) from exc

        except RateLimitError as exc:
            logger.error(f"Límite de peticiones de OpenAI excedido: {exc}")
            raise RuntimeError(
                "El servicio de soporte con IA está experimentando alta demanda. Intenta de nuevo en unos instantes."
            ) from exc

        except APIConnectionError as exc:
            logger.error(f"Error de conexión con OpenAI: {exc}")
            raise RuntimeError(
                "No fue posible conectar con el servicio de IA de soporte. Revisa tu conexión a Internet."
            ) from exc

        except APIError as exc:
            logger.error(f"Error de API de OpenAI: {exc}")
            raise RuntimeError(
                "Ocurrió un error en el servicio de OpenAI al procesar tu consulta."
            ) from exc

        except Exception as exc:
            logger.error(f"Error inesperado en SupportAIService: {exc}", exc_info=True)
            raise RuntimeError(
                "No fue posible comunicarse con la IA de soporte de MIVOR."
            ) from exc