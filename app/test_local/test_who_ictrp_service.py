import asyncio
import sys
from pathlib import Path

# ==========================================================
# AGREGAR LA RAÍZ DEL PROYECTO AL PYTHONPATH
# ==========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


# ==========================================================
# IMPORTAR SERVICIO
# ==========================================================

from app.services.who_ictrp_service import WHOICTRPService


# ==========================================================
# TEST
# ==========================================================

async def main():

    print("=" * 70)
    print("MEDICAL AI - TEST WHO ICTRP SERVICE")
    print("=" * 70)

    query = "leucemia"

    print()
    print(f"Consulta: {query}")
    print()

    service = WHOICTRPService()

    results = await service.search_and_fetch(
        query=query,
        max_results=5
    )

    print()
    print("=" * 70)
    print(f"RESULTADOS ENCONTRADOS: {len(results)}")
    print("=" * 70)

    if not results:
        print()
        print("⚠️ No se encontraron resultados.")
        print()
        return

    for index, document in enumerate(
        results,
        start=1
    ):

        print()
        print("-" * 70)
        print(f"[{index}]")
        print(f"ID: {document.source_id}")
        print(f"TIPO: {document.source_type}")
        print(f"TÍTULO: {document.title}")
        print(f"FECHA: {document.publication_date}")
        print(f"URL: {document.url}")

        abstract = document.abstract or ""

        print(
            f"ABSTRACT: {abstract[:300]}"
        )

        print(
            f"METADATA: {document.metadata}"
        )

    print()
    print("=" * 70)
    print("TEST WHO ICTRP COMPLETADO")
    print("=" * 70)


# ==========================================================
# EJECUTAR
# ==========================================================

if __name__ == "__main__":
    asyncio.run(main())
