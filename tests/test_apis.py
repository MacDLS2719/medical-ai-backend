import asyncio
import httpx

async def test_all():
    query = "diabetes"

    # 1. PubMed
    try:
        url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        params = {"db": "pubmed", "term": query, "retmode": "json", "retmax": 2,
                  "email": "test@test.com", "tool": "test"}
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(url, params=params)
            ids = r.json().get("esearchresult", {}).get("idlist", [])
            print(f"PubMed OK: {ids}")
    except Exception as e:
        print(f"PubMed ERROR: {e}")

    # 2. Europe PMC
    try:
        url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
        params = {"query": query, "resultType": "core", "format": "json", "pageSize": 2, "cursor": "*"}
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(url, params=params)
            results = r.json().get("resultList", {}).get("result", [])
            print(f"EuropePMC OK: {len(results)} resultados")
    except Exception as e:
        print(f"EuropePMC ERROR: {e}")

    # 3. ClinicalTrials v2
    try:
        url = "https://clinicaltrials.gov/api/v2/studies"
        params = {"query.cond": query, "pageSize": 2, "format": "json"}
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(url, params=params)
            print(f"ClinicalTrials status: {r.status_code}")
            studies = r.json().get("studies", [])
            print(f"ClinicalTrials OK: {len(studies)} estudios")
    except Exception as e:
        print(f"ClinicalTrials ERROR: {e}")

    # 4. Cochrane via PubMed
    try:
        cochrane_query = '(diabetes) AND "Cochrane Database Syst Rev"[Journal]'
        url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        params = {"db": "pubmed", "term": cochrane_query, "retmode": "json", "retmax": 2,
                  "email": "test@test.com", "tool": "test"}
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(url, params=params)
            ids = r.json().get("esearchresult", {}).get("idlist", [])
            print(f"Cochrane OK: {ids}")
    except Exception as e:
        print(f"Cochrane ERROR: {e}")

asyncio.run(test_all())
