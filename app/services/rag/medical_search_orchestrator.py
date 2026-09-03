# app/services/rag/medical_search_orchestrator.py

import asyncio
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from app.services.rag.schemas import NormalizedDocument

from app.services.rag.librerias.pubmed_service import PubMedService
from app.services.rag.librerias.cochrane_service import CochraneService
from app.services.rag.librerias.clinical_trials_service import ClinicalTrialsService
from app.services.rag.librerias.europe_pmc_service import EuropePMCService
from app.services.rag.librerias.openfda_service import OpenFDAService
from app.services.rag.librerias.who_ictrp_service import WHOICTRPService


class MedicalSearchOrchestrator:
    """
    Orquesta las búsquedas en las diferentes fuentes médicas.

    Responsabilidades:
    - Registrar las fuentes disponibles.
    - Permitir buscar en todas las fuentes.
    - Permitir buscar solamente en fuentes específicas.
    - Ejecutar las búsquedas en paralelo.
    - Aislar errores individuales de cada fuente.
    - Eliminar resultados con fechas futuras.
    - Ordenar resultados por fecha.
    - Consolidar los resultados de todas las fuentes.

    Este servicio NO:
    - detecta el idioma,
    - normaliza la consulta,
    - traduce resultados,
    - genera respuestas con IA.
    """

    def __init__(self):
        self.sources = {
            "pubmed": PubMedService(),
            "cochrane": CochraneService(),
            "clinical_trials": ClinicalTrialsService(),
            "europe_pmc": EuropePMCService(),
            "openfda": OpenFDAService(),
            "who_ictrp": WHOICTRPService(),
        }

    async def search(
        self,
        query: str,
        sources: Optional[List[str]] = None,
        max_results: int = 5,
    ) -> Dict[str, Any]:
        """
        Ejecuta una búsqueda médica.

        Parameters
        ----------
        query:
            Consulta médica.

        sources:
            Lista opcional de fuentes.

            None:
                Busca en todas las fuentes.

            ["pubmed"]:
                Busca solamente en PubMed.

            ["pubmed", "openfda"]:
                Busca solamente en PubMed y OpenFDA.

        max_results:
            Cantidad máxima de resultados solicitados por fuente.

        Returns
        -------
        Dict[str, Any]
            Resultado consolidado de todas las fuentes.
        """

        if not query or not query.strip():
            return {
                "sources": {},
                "results": [],
                "errors": {},
            }

        query = query.strip()

        selected_sources = self._get_selected_sources(sources)

        # Ejecutar todas las fuentes seleccionadas en paralelo.
        tasks = [
            self._safe_result(
                source_name=source_name,
                service=service,
                query=query,
                max_results=max_results,
            )
            for source_name, service in selected_sources.items()
        ]

        source_results = await asyncio.gather(*tasks)

        results_by_source: Dict[str, List[NormalizedDocument]] = {}
        errors: Dict[str, str] = {}

        all_results: List[NormalizedDocument] = []

        for source_name, results, error in source_results:
            results_by_source[source_name] = results

            if error:
                errors[source_name] = error

            all_results.extend(results)

        # Eliminar resultados con fechas futuras.
        all_results = self._filter_future_dates(all_results)

        # Ordenar todos los resultados de forma descendente.
        all_results = self._sort_results(all_results)

        return {
            "sources": results_by_source,
            "results": all_results,
            "errors": errors,
        }

    def _get_selected_sources(
        self,
        sources: Optional[List[str]],
    ) -> Dict[str, Any]:
        """
        Determina qué fuentes se utilizarán.

        sources=None
            → todas las fuentes.

        sources=["pubmed"]
            → solamente PubMed.
        """

        if sources is None:
            return self.sources.copy()

        if not sources:
            return {}

        invalid_sources = [
            source
            for source in sources
            if source not in self.sources
        ]

        if invalid_sources:
            raise ValueError(
                f"Fuentes no soportadas: {', '.join(invalid_sources)}. "
                f"Fuentes disponibles: {', '.join(self.sources.keys())}"
            )

        return {
            source_name: self.sources[source_name]
            for source_name in sources
        }

    async def _safe_result(
        self,
        source_name: str,
        service: Any,
        query: str,
        max_results: int,
    ):
        """
        Ejecuta una fuente de manera segura.

        Si una fuente falla, no afecta las demás.
        """

        try:
            results = await service.search_and_fetch(
                query=query,
                max_results=max_results,
            )

            if results is None:
                results = []

            return source_name, results, None

        except Exception as exc:
            return source_name, [], str(exc)

    def _filter_future_dates(
        self,
        results: List[NormalizedDocument],
    ) -> List[NormalizedDocument]:
        """
        Elimina resultados cuya fecha sea posterior a hoy.

        Los documentos sin fecha se conservan.
        """

        today = date.today()

        filtered_results = []

        for result in results:
            result_date = self._extract_date(result)

            if result_date is None:
                filtered_results.append(result)
                continue

            if result_date <= today:
                filtered_results.append(result)

        return filtered_results

    def _sort_results(
        self,
        results: List[NormalizedDocument],
    ) -> List[NormalizedDocument]:
        """
        Ordena los resultados desde los más recientes
        hasta los más antiguos.

        Los documentos sin fecha quedan al final.
        """

        return sorted(
            results,
            key=lambda result: self._extract_date(result)
            or date.min,
            reverse=True,
        )

    @staticmethod
    def _extract_date(
        result: NormalizedDocument,
    ) -> Optional[date]:
        """
        Extrae la fecha del documento normalizado.

        Soporta:
        - date
        - datetime
        - strings ISO
        - strings con fecha YYYY-MM-DD
        """

        value = getattr(result, "publication_date", None)

        if value is None:
            value = getattr(result, "date", None)

        if value is None:
            value = getattr(result, "published_date", None)

        if value is None:
            return None

        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, date):
            return value

        if isinstance(value, str):
            value = value.strip()

            if not value:
                return None

            # ISO datetime.
            try:
                return datetime.fromisoformat(
                    value.replace("Z", "+00:00")
                ).date()
            except ValueError:
                pass

            # Fecha simple YYYY-MM-DD.
            try:
                return datetime.strptime(
                    value[:10],
                    "%Y-%m-%d",
                ).date()
            except ValueError:
                pass

        return None