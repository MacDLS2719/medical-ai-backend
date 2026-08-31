import asyncio
import sys
import os

# Agregar el directorio del proyecto al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.europe_pmc_service import EuropePMCService
from app.services.who_ictrp_service import WHOICTRPService
from app.schemas.medical import NormalizedDocument

async def test_europe_pmc():
    """Test de Europe PMC Service"""
    print("=" * 60)
    print("TEST: Europe PMC Service")
    print("=" * 60)
    
    service = EuropePMCService()
    
    # Test con una búsqueda simple
    query = "diabetes"
    print(f"\nBuscando: '{query}' en Europe PMC...")
    
    try:
        results = await service.search_and_fetch(query, max_results=3)
        
        print(f"\n✅ Resultados obtenidos: {len(results)}")
        
        for i, doc in enumerate(results, 1):
            print(f"\n--- Documento {i} ---")
            print(f"ID: {doc.source_id}")
            print(f"Tipo: {doc.source_type}")
            print(f"Título: {doc.title[:100]}..." if len(doc.title) > 100 else f"Título: {doc.title}")
            print(f"Abstract: {doc.abstract[:150]}..." if len(doc.abstract) > 150 else f"Abstract: {doc.abstract}")
            print(f"Autores: {doc.authors[:3]}..." if len(doc.authors) > 3 else f"Autores: {doc.authors}")
            print(f"Fecha: {doc.publication_date}")
            print(f"URL: {doc.url}")
            print(f"Metadata: {doc.metadata}")
            
        return len(results) > 0
        
    except Exception as e:
        print(f"❌ Error en Europe PMC: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_who_ictrp():
    """Test de WHO ICTRP Service"""
    print("\n" + "=" * 60)
    print("TEST: WHO ICTRP Service")
    print("=" * 60)
    
    service = WHOICTRPService()
    
    # Test con una búsqueda simple
    query = "diabetes"
    print(f"\nBuscando: '{query}' en WHO ICTRP...")
    
    try:
        results = await service.search_and_fetch(query, max_results=3)
        
        print(f"\n✅ Resultados obtenidos: {len(results)}")
        
        for i, doc in enumerate(results, 1):
            print(f"\n--- Documento {i} ---")
            print(f"ID: {doc.source_id}")
            print(f"Tipo: {doc.source_type}")
            print(f"Título: {doc.title[:100]}..." if len(doc.title) > 100 else f"Título: {doc.title}")
            print(f"Abstract: {doc.abstract[:150]}..." if len(doc.abstract) > 150 else f"Abstract: {doc.abstract}")
            print(f"Autores: {doc.authors[:3]}..." if len(doc.authors) > 3 else f"Autores: {doc.authors}")
            print(f"Fecha: {doc.publication_date}")
            print(f"URL: {doc.url}")
            print(f"Metadata: {doc.metadata}")
            
        return len(results) > 0
        
    except Exception as e:
        print(f"❌ Error en WHO ICTRP: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_integration():
    """Test de integración con MedicalSearchService"""
    print("\n" + "=" * 60)
    print("TEST: Integración con MedicalSearchService")
    print("=" * 60)
    
    from app.services.medical_search_service import MedicalSearchService
    from app.services.pubmed_service import PubMedService
    from app.services.clinical_trials_service import ClinicalTrialsService
    from app.services.cochrane_service import CochraneService
    
    try:
        service = MedicalSearchService(
            pubmed_service=PubMedService(),
            clinical_trials_service=ClinicalTrialsService(),
            cochrane_service=CochraneService(),
            europe_pmc_service=EuropePMCService(),
            who_ictrp_service=WHOICTRPService()
        )
        
        print("\n✅ MedicalSearchService inicializado correctamente")
        print(f"Europe PMC service: {'✅' if service.europe_pmc_service else '❌'}")
        print(f"WHO ICTRP service: {'✅' if service.who_ictrp_service else '❌'}")
        
        # Test de búsqueda simple
        query = "diabetes"
        print(f"\nBuscando: '{query}' en todas las fuentes...")
        
        result = await service.search(query, max_results=5, target_lang="es")
        
        print(f"\n✅ Búsqueda completada")
        print(f"Total resultados: {result['total_results']}")
        print(f"PubMed: {result['sources']['pubmed']['count']}")
        print(f"ClinicalTrials: {result['sources']['clinical_trials']['count']}")
        print(f"Cochrane: {result['sources']['cochrane']['count']}")
        print(f"Europe PMC: {result['sources']['europe_pmc']['count']}")
        print(f"WHO ICTRP: {result['sources']['who_ictrp']['count']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en integración: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Ejecutar todos los tests"""
    print("INICIANDO TESTS DE SERVICIOS NUEVOS\n")
    
    results = []
    
    # Test Europe PMC
    europe_pmc_ok = await test_europe_pmc()
    results.append(("Europe PMC", europe_pmc_ok))
    
    # Test WHO ICTRP
    who_ictrp_ok = await test_who_ictrp()
    results.append(("WHO ICTRP", who_ictrp_ok))
    
    # Test Integración
    integration_ok = await test_integration()
    results.append(("Integración", integration_ok))
    
    # Resumen
    print("\n" + "=" * 60)
    print("RESUMEN DE TESTS")
    print("=" * 60)
    
    for test_name, ok in results:
        status = "PASO" if ok else "FALLO"
        print(f"{test_name}: {status}")
    
    all_passed = all(ok for _, ok in results)
    print(f"\n{'TODOS LOS TESTS PASARON' if all_passed else 'ALGUNOS TESTS FALLARON'}")

if __name__ == "__main__":
    asyncio.run(main())