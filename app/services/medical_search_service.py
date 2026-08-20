import asyncio
from typing import List

from deep_translator import GoogleTranslator

from app.schemas.medical import NormalizedDocument

from app.services.pubmed_service import PubMedService
from app.services.clinical_trials_service import ClinicalTrialsService
from app.services.cochrane_service import CochraneService


class MedicalSearchService:

    def __init__(
        self,
        pubmed_service: PubMedService,
        clinical_trials_service: ClinicalTrialsService,
        cochrane_service: CochraneService,
    ):
        self.pubmed_service = pubmed_service
        self.clinical_trials_service = clinical_trials_service
        self.cochrane_service = cochrane_service

    async def search(
        self,
        query: str,
        max_results: int = 5,
        target_lang: str = "en"
    ) -> dict:

        # ==========================================================
        # 1. PREPARAR CONSULTA PARA LAS FUENTES CIENTÍFICAS
        # ==========================================================

        search_query = query

        # Las fuentes científicas trabajan principalmente en inglés.
        # Traducimos únicamente la consulta del usuario.
        if target_lang != "en" and query:

            try:

                search_query = await asyncio.to_thread(
                    GoogleTranslator(
                        source=target_lang,
                        target="en"
                    ).translate,
                    query
                )

                print(
                    f"Medical search query translated: "
                    f"{query} -> {search_query}"
                )

            except Exception as e:

                # Si falla la traducción de la consulta,
                # NO detenemos la búsqueda.
                print(
                    f"Error translating search query: {e}"
                )

                # Utilizamos la consulta original.
                search_query = query

        # ==========================================================
        # 2. CONSULTAR LAS FUENTES MÉDICAS
        # ==========================================================

        results = await asyncio.gather(

            self.pubmed_service.search_and_fetch(
                search_query,
                max_results
            ),

            self.clinical_trials_service.search_and_fetch(
                search_query,
                max_results
            ),

            self.cochrane_service.search_and_fetch(
                search_query,
                max_results
            ),

            return_exceptions=True
        )

        # ==========================================================
        # 3. PROTEGER CADA FUENTE CONTRA ERRORES
        # ==========================================================

        pubmed_results = self._safe_result(
            results[0]
        )

        clinical_trials_results = self._safe_result(
            results[1]
        )

        cochrane_results = self._safe_result(
            results[2]
        )

        # ==========================================================
        # 4. UNIFICAR DOCUMENTOS
        # ==========================================================

        all_results: List[NormalizedDocument] = (
            pubmed_results
            + clinical_trials_results
            + cochrane_results
        )

        # ==========================================================
        # IMPORTANTE:
        #
        # NO traducimos aquí los documentos.
        #
        # Los abstracts y títulos originales se conservan.
        #
        # El RAG utilizará esta evidencia original y Groq será
        # responsable de generar la respuesta en el idioma solicitado.
        # ==========================================================

        print(
            f"Medical search completed. "
            f"Total documents: {len(all_results)}"
        )

        # ==========================================================
        # 5. RESPUESTA NORMALIZADA
        # ==========================================================

        return {
            "query": query,

            # Consulta utilizada realmente para las fuentes.
            "search_query": search_query,

            "target_lang": target_lang,

            "total_results": len(all_results),

            "sources": {

                "pubmed": {
                    "count": len(pubmed_results),
                    "results": pubmed_results,
                },

                "clinical_trials": {
                    "count": len(clinical_trials_results),
                    "results": clinical_trials_results,
                },

                "cochrane": {
                    "count": len(cochrane_results),
                    "results": cochrane_results,
                },
            },

            # Todos los documentos originales para el RAG.
            "results": all_results,
        }

    @staticmethod
    def _safe_result(result):

        if isinstance(result, Exception):

            print(
                f"Error consultando fuente médica: {result}"
            )

            return []

        return result