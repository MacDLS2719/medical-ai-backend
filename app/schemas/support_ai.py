from pydantic import BaseModel, Field


class SupportAIRequest(BaseModel):
    """
    Datos que recibe la IA de soporte.
    """

    message: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="Pregunta o problema que el usuario quiere consultar al soporte de MIVOR.",
    )


class SupportAIResponse(BaseModel):
    """
    Respuesta que devuelve la IA de soporte.
    """

    response: str = Field(
        ...,
        description="Respuesta generada por la IA de soporte de MIVOR.",
    )