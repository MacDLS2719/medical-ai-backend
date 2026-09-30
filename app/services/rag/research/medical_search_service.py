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

    async def advanced_research_search(self, query: str, max_results_per_source: int = 2) -> dict:
        """
        Busca en las librerías configuradas,
        combina los resultados y usa OpenAI (GPT-3.5) para generar un resumen avanzado.
        """
        # Ejecutar búsquedas en paralelo para optimizar tiempo
        source_services = {
            "clinical_trials": self.clinical_trials,
            "cochrane": self.cochrane,
            "europe_pmc": self.europe_pmc,
            "openfda": self.openfda,
            "pubmed": self.pubmed,
        }
        tasks = [
            service.search_and_fetch(query, max_results_per_source)
            for service in source_services.values()
        ]
        
        # Obtenemos los resultados manejando excepciones
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_documents: List[NormalizedDocument] = []
        source_status = {}
        for (source_name, _), result in zip(source_services.items(), results):
            if isinstance(result, list):
                all_documents.extend(result)
                source_status[source_name] = {
                    "count": len(result),
                    "status": "ok",
                }
            elif isinstance(result, Exception):
                source_status[source_name] = {
                    "count": 0,
                    "status": "error",
                }
                print(f"Error al obtener resultados de {source_name}: {result}")
                
        # Si no se encontró ningún documento, se lo indicamos a GPT para que use su conocimiento
        if not all_documents:
            print("No se encontró información en las librerías para la búsqueda proporcionada. Consultando a OpenAI...")
            
        # Llamar a OpenAI para que estructure el resumen general y las referencias
        summary = await openai_service.generate_research_summary(query, all_documents)
        if isinstance(summary, dict):
            return {**summary, "sources": source_status}
        return {"summary": str(summary), "references": [], "sources": source_status}

    async def university_research_search(
        self,
        query: str,
        max_results_per_source: int = 2,
        existing_references: list | None = None,
    ) -> dict:
        """
        Búsqueda web universitaria independiente de los adaptadores bibliográficos.
        """
        return await openai_service.generate_university_summary(
            query,
            documents=[]
        )

medical_search_service = MedicalSearchService()
