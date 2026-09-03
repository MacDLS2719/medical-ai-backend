"""
Script de depuración para diagnosticar problemas de búsqueda médica
"""
import asyncio
import sys
import os

# Agregar el directorio padre al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.services.pubmed_service import PubMedService
from app.services.clinical_trials_service import ClinicalTrialsService
from app.services.cochrane_service import CochraneService
from app.services.medical_search_service import MedicalSearchService


async def test_individual_services():
    """Probar cada servicio individualmente"""

    print("=" * 50)
    print("PRUEBA DE SERVICIOS INDIVIDUALES")
    print("=" * 50)

    test_query = "diabetes"

    # Test PubMed
    print("\n--- TEST PUBMED ---")
    pubmed_service = PubMedService()
    try:
        pubmed_results = await pubmed_service.search_and_fetch(test_query, max_results=5)
        print(f"PubMed results: {len(pubmed_results)}")
        if pubmed_results:
            print(f"First result: {pubmed_results[0].title}")
        else:
            print("❌ PubMed no encontró resultados")
    except Exception as e:
        print(f"❌ PubMed error: {e}")

    # Test ClinicalTrials
    print("\n--- TEST CLINICAL TRIALS ---")
    clinical_service = ClinicalTrialsService()
    try:
        clinical_results = await clinical_service.search_and_fetch(test_query, max_results=5)
        print(f"ClinicalTrials results: {len(clinical_results)}")
        if clinical_results:
            print(f"First result: {clinical_results[0].title}")
        else:
            print("❌ ClinicalTrials no encontró resultados")
    except Exception as e:
        print(f"❌ ClinicalTrials error: {e}")

    # Test Cochrane
    print("\n--- TEST COCHRANE ---")
    cochrane_service = CochraneService()
    try:
        cochrane_results = await cochrane_service.search_and_fetch(test_query, max_results=5)
        print(f"Cochrane results: {len(cochrane_results)}")
        if cochrane_results:
            print(f"First result: {cochrane_results[0].title}")
        else:
            print("❌ Cochrane no encontró resultados")
    except Exception as e:
        print(f"❌ Cochrane error: {e}")


async def test_search_service():
    """Probar el servicio de búsqueda médico completo"""

    print("\n" + "=" * 50)
    print("PRUEBA DEL SERVICIO DE BÚSQUEDA MÉDICO")
    print("=" * 50)

    medical_search_service = MedicalSearchService(
        pubmed_service=PubMedService(),
        clinical_trials_service=ClinicalTrialsService(),
        cochrane_service=CochraneService(),
    )

    test_query = "diabetes"

    try:
        result = await medical_search_service.search(
            query=test_query,
            max_results=10,
            target_lang="es"
        )

        print(f"\nQuery original: {result.get('query')}")
        print(f"Query traducido: {result.get('search_query')}")
        print(f"Total resultados: {result.get('total_results')}")

        print(f"\nPubMed: {result['sources']['pubmed']['count']}")
        print(f"ClinicalTrials: {result['sources']['clinical_trials']['count']}")
        print(f"Cochrane: {result['sources']['cochrane']['count']}")

        if result.get('results'):
            print(f"\nPrimer resultado: {result['results'][0].title}")
        else:
            print("❌ No se encontraron resultados")

    except Exception as e:
        print(f"❌ Error en medical search: {e}")
        import traceback
        traceback.print_exc()


async def test_query_cleaning():
    """Probar la limpieza de consultas"""

    print("\n" + "=" * 50)
    print("PRUEBA DE LIMPIEZA DE CONSULTAS")
    print("=" * 50)

    test_queries = [
        "diabetes",
        "diabetes treatment",
        "diabetes AND hypertension",
        "quiero buscar sobre diabetes",
        "articles about diabetes"
    ]

    for query in test_queries:
        cleaned = MedicalSearchService._clean_search_terms(query)
        print(f"'{query}' -> '{cleaned}'")


if __name__ == "__main__":
    asyncio.run(test_individual_services())
    asyncio.run(test_search_service())
    asyncio.run(test_query_cleaning())
