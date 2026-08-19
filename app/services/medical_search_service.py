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

        search_query = query
        if target_lang != "en" and query:
            try:
                search_query = await asyncio.to_thread(
                    GoogleTranslator(source=target_lang, target='en').translate, query
                )
            except Exception as e:
                print(f"Error translating query: {e}")

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

        pubmed_results = self._safe_result(results[0])
        clinical_trials_results = self._safe_result(results[1])
        cochrane_results = self._safe_result(results[2])

        all_results: List[NormalizedDocument] = (
            pubmed_results
            + clinical_trials_results
            + cochrane_results
        )

        if target_lang != "en":
            translator = GoogleTranslator(source='en', target=target_lang)
            for doc in all_results:
                try:
                    if doc.title:
                        doc.title = await asyncio.to_thread(translator.translate, doc.title)
                    if doc.abstract and len(doc.abstract) > 0:
                        doc.abstract = await asyncio.to_thread(translator.translate, doc.abstract[:4999])
                except Exception as e:
                    print(f"Error translating doc {doc.source_id}: {e}")

        return {
            "query": query,
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

            "results": all_results,
        }

    @staticmethod
    def _safe_result(result):

        if isinstance(result, Exception):
            print(f"Error consultando fuente médica: {result}")
            return []

        return result