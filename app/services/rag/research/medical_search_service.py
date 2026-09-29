import asyncio
from typing import List
from app.services.rag.schemas import NormalizedDocument

# Importamos las librerías / servicios
from app.services.rag.librerias.clinical_trials_service import ClinicalTrialsService
from app.services.rag.librerias.cochrane_service import CochraneService
from app.services.rag.librerias.europe_pmc_service import EuropePMCService
from app.services.rag.librerias.openfda_service import OpenFDAService
from app.services.rag.librerias.pubmed_service import PubMedService

# Importamos el servicio de OpenAI
from app.services.rag.research.openai_service import openai_service

class MedicalSearchService:
    def __init__(self):
        self.clinical_trials = ClinicalTrialsService()
        self.cochrane = CochraneService()
        self.europe_pmc = EuropePMCService()
        self.openfda = OpenFDAService()
        self.pubmed = PubMedService()

    async def advanced_research_search(self, query: str, max_results_per_source: int = 2) -> str:
        """
        Busca en las librerías configuradas,
        combina los resultados y usa OpenAI (GPT-3.5) para generar un resumen avanzado.
        """
        # Ejecutar búsquedas en paralelo para optimizar tiempo
        tasks = [
            self.clinical_trials.search_and_fetch(query, max_results_per_source),
            self.cochrane.search_and_fetch(query, max_results_per_source),
            self.europe_pmc.search_and_fetch(query, max_results_per_source),
            self.openfda.search_and_fetch(query, max_results_per_source),
            self.pubmed.search_and_fetch(query, max_results_per_source)
        ]
        
        # Obtenemos los resultados manejando excepciones
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_documents: List[NormalizedDocument] = []
        for result in results:
            if isinstance(result, list):
                all_documents.extend(result)
            elif isinstance(result, Exception):
                print(f"Error al obtener resultados de una de las librerías: {result}")
                
        # Si no se encontró ningún documento, se lo indicamos a GPT para que use su conocimiento
        if not all_documents:
            print("No se encontró información en las librerías para la búsqueda proporcionada. Consultando a OpenAI...")
            
        # Llamar a OpenAI para que estructure el resumen general y las referencias
        summary_markdown = await openai_service.generate_research_summary(query, all_documents)
        return summary_markdown

    async def university_research_search(self, query: str, max_results_per_source: int = 2) -> dict:
        """
        Búsqueda especializada en fuentes universitarias y centros de investigación.
        Reutiliza los mismos adaptadores de fuentes pero usa el prompt universitario de OpenAI.
        """
        tasks = [
            self.europe_pmc.search_and_fetch(query, max_results_per_source),
            self.pubmed.search_and_fetch(query, max_results_per_source),
            self.cochrane.search_and_fetch(query, max_results_per_source),
            self.clinical_trials.search_and_fetch(query, max_results_per_source),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_documents: List[NormalizedDocument] = []
        for result in results:
            if isinstance(result, list):
                all_documents.extend(result)
            elif isinstance(result, Exception):
                print(f"[UniversitySearch] Error en fuente: {result}")

        # Llama al prompt universitario especializado
        return await openai_service.generate_university_summary(query, all_documents)

medical_search_service = MedicalSearchService()
