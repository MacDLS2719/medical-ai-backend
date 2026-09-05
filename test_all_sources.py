import asyncio
from app.services.rag.librerias.pubmed_service import PubMedService
from app.services.rag.librerias.cochrane_service import CochraneService
from app.services.rag.librerias.clinical_trials_service import ClinicalTrialsService
from app.services.rag.librerias.europe_pmc_service import EuropePMCService
from app.services.rag.librerias.openfda_service import OpenFDAService
from app.services.rag.librerias.who_ictrp_service import WHOICTRPService

async def test_service(name, svc):
    print(f"Starting {name}...")
    try:
        results = await asyncio.wait_for(svc.search_and_fetch('cancer', 100), timeout=30)
        print(f"{name} success: {len(results)} results")
    except asyncio.TimeoutError:
        print(f"{name} TIMEOUT")
    except Exception as e:
        print(f"{name} ERROR: {e}")

async def main():
    services = {
        "pubmed": PubMedService(),
        "cochrane": CochraneService(),
        "clinical_trials": ClinicalTrialsService(),
        "europe_pmc": EuropePMCService(),
        "openfda": OpenFDAService(),
        "who_ictrp": WHOICTRPService()
    }
    
    tasks = [test_service(name, svc) for name, svc in services.items()]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
