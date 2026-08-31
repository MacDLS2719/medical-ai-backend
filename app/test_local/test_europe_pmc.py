import asyncio
import httpx


BASE_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


async def test_europe_pmc():
    print("=" * 70)
    print("MEDICAL AI - PRUEBA DE CONEXIÓN EUROPE PMC")
    print("=" * 70)

    query = "leukemia"

    params = {
        "query": query,
        "format": "json",
        "pageSize": 3,
        "resultType": "core",
    }

    print(f"\nConsulta: {query}")
    print("Conectando con Europe PMC...\n")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:

            response = await client.get(
                BASE_URL,
                params=params,
            )

            print(f"HTTP Status: {response.status_code}")

            response.raise_for_status()

            data = response.json()

        results = data.get("resultList", {}).get("result", [])

        print(f"Resultados encontrados: {len(results)}")

        print("\n" + "-" * 70)

        for index, result in enumerate(results, start=1):

            print(f"\n[{index}]")

            print(
                "ID:",
                result.get("id")
            )

            print(
                "Título:",
                result.get("title", "Sin título")
            )

            print(
                "PMID:",
                result.get("pmid", "No disponible")
            )

            print(
                "DOI:",
                result.get("doi", "No disponible")
            )

            print(
                "Fecha:",
                result.get("firstPublicationDate", "No disponible")
            )

            print(
                "Revista:",
                result.get("journalTitle", "No disponible")
            )

            abstract = result.get(
                "abstractText",
                "Sin abstract"
            )

            print(
                "Abstract:",
                abstract[:300],
                "..."
                if len(abstract) > 300
                else ""
            )

            print(
                "URL:",
                f"https://europepmc.org/article/MED/{result.get('id')}"
            )

        print("\n" + "=" * 70)
        print("CONEXIÓN CON EUROPE PMC EXITOSA")
        print("=" * 70)

    except httpx.HTTPStatusError as e:

        print("\nERROR HTTP:")
        print(e)

        print(
            "\nRespuesta del servidor:",
            e.response.text[:1000]
        )

    except httpx.RequestError as e:

        print("\nERROR DE CONEXIÓN:")
        print(e)

    except Exception as e:

        print("\nERROR INESPERADO:")
        print(type(e).__name__, e)


if __name__ == "__main__":
    asyncio.run(test_europe_pmc())