from typing import Optional, Union
from pydantic import BaseModel, Field


class MedicalAgentRequest(BaseModel):
    """
    Datos recibidos por el Medical Agent.
    """

    query: str = Field(
        ...,
        min_length=1,
        description="Pregunta o consulta médica realizada por el usuario.",
    )

    language: str = Field(
        default="es",
        max_length=10,
        description="Idioma en el que el usuario desea recibir la respuesta.",
    )


class MedicalAgentResult(BaseModel):
    """
    Artículo científico encontrado por el Medical Agent.
    Campos idénticos a los que el frontend ya renderiza para las bibliotecas.
    """

    source: str = Field(
        ...,
        description="Nombre de la revista o fuente médica.",
    )

    title: str = Field(
        ...,
        description="Título del artículo.",
    )

    abstract: Optional[str] = Field(
        default=None,
        description="Resumen del artículo.",
    )

    summary: Optional[str] = Field(
        default=None,
        description="Resumen generado (reservado para uso futuro).",
    )

    url: Optional[str] = Field(
        default=None,
        description="URL original del artículo.",
    )

    published_at: Optional[str] = Field(
        default=None,
        description="Fecha de publicación (YYYY-MM-DD o YYYY-MM).",
    )


class MedicalAgentResponse(BaseModel):
    """
    Respuesta completa del Medical Agent:
    un mensaje resumen + lista de artículos encontrados.
    """

    query: str = Field(
        ...,
        description="Consulta original del usuario.",
    )

    answer: str = Field(
        ...,
        description="Mensaje resumen (cuántos artículos se encontraron y dónde).",
    )

    results: list[MedicalAgentResult] = Field(
        default_factory=list,
        description="Artículos científicos encontrados, ordenados del más reciente al más antiguo.",
    )