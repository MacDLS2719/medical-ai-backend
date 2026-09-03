# app/services/rag/result_presenter_service.py

from typing import Any, Dict


class ResultPresenterService:
    """
    Organiza los resultados obtenidos por MedicalSearchOrchestrator
    en una respuesta unificada.

    Responsabilidades:
    - Organizar resultados por fuente.
    - Entregar todos los resultados en una lista unificada.
    - Conservar los errores de cada fuente.

    Este servicio NO:
    - realiza búsquedas.
    - selecciona fuentes.
    - normaliza consultas.
    - detecta idiomas.
    - traduce resultados.
    - genera respuestas con IA.
    """

    def present(
        self,
        search_response: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Construye la respuesta unificada a partir de los resultados
        del MedicalSearchOrchestrator.
        """

        if not search_response:
            return {
                "sources": {},
                "results": [],
                "errors": {},
            }

        return {
            "sources": search_response.get("sources", {}),
            "results": search_response.get("results", []),
            "errors": search_response.get("errors", {}),
        }