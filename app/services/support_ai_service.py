import os

from openai import AsyncOpenAI

from app.prompts.support_ai_prompt import SUPPORT_AI_SYSTEM_PROMPT


class SupportAIService:
    """
    Servicio encargado de comunicarse con OpenAI
    para proporcionar soporte a los usuarios de MIVOR.
    """

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")

        if not self.api_key:
            raise RuntimeError(
                "OPENAI_API_KEY no está configurada en las variables de entorno."
            )

        self.model = os.getenv(
            "OPENAI_SUPPORT_MODEL",
            "gpt-3.5-turbo",
        )

        self.client = AsyncOpenAI(
            api_key=self.api_key,
        )

    async def ask(self, message: str) -> str:
        """
        Envía una pregunta del usuario a la IA de soporte
        y devuelve únicamente la respuesta generada.
        """

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SUPPORT_AI_SYSTEM_PROMPT},
                    {"role": "user", "content": message}
                ],
            )

            return response.choices[0].message.content.strip()

        except Exception as exc:
            print(f"Error en SupportAIService: {exc}")

            raise RuntimeError(
                "No fue posible comunicarse con la IA de soporte."
            ) from exc