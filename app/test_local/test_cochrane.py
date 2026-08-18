import asyncio
from dotenv import load_dotenv

load_dotenv()

from services.cochrane_service import CochraneService


async def main():
    print("🔬 Iniciando prueba de conexión con Cochrane Library (vía NCBI)...")

    service = CochraneService()
    query_term = "Diabetes Type 2"
    max_results = 3

    print(f"\n🔍 Buscando Revisiones Sistemáticas de Cochrane sobre: '{query_term}' (Máximo {max_results} resultados)\n")

    try:
        documents = await service.search_and_fetch(query=query_term, max_results=max_results)

        if not documents:
            print("⚠️ No se encontraron revisiones de Cochrane.")
            return

        print(f"✅ ¡Éxito! Se obtuvieron {len(documents)} revisiones de Cochrane normalizadas:\n")

        for i, doc in enumerate(documents, start=1):
            print(f"--- Revisión Cochrane #{i} ---")
            print(f"📌 ID / DOI: {doc.source_id}")
            print(f"📄 Título: {doc.title}")
            print(f"👥 Autores: {', '.join(doc.authors[:3]) if doc.authors else 'No especificados'}")
            print(f"📅 Fecha: {doc.publication_date}")
            print(f"🔗 URL: {doc.url}")
            print(f"📝 Resumen (primeros 200 caracteres):")
            print(f"   {doc.abstract[:200]}...\n")

    except Exception as e:
        print(f"❌ Error al ejecutar la prueba: {e}")


if __name__ == "__main__":
    asyncio.run(main())