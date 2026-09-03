import asyncio
from dotenv import load_dotenv
from typing import List, Optional
from schemas.medical import NormalizedDocument

# Cargar variables de entorno desde el archivo .env
load_dotenv()

from services.pubmed_service import PubMedService


async def main():
    print("🔬 Iniciando prueba de conexión con PubMed API...")

    service = PubMedService()

    # 1. Patología o término de prueba
    query_term = "Diabetes Type 2 treatment"
    max_results = 3

    print(f"\n🔍 Buscando artículos sobre: '{query_term}' (Máximo {max_results} resultados)\n")

    try:
        # Ejecutar la búsqueda y extracción
        documents = await service.search_and_fetch(query=query_term, max_results=max_results)

        if not documents:
            print("⚠️ No se encontraron resultados o hubo un problema en el parseo.")
            return

        print(f"✅ ¡Éxito! Se obtuvieron {len(documents)} documentos normalizados:\n")

        for i, doc in enumerate(documents, start=1):
            print(f"--- Documento #{i} ---")
            print(f"📌 ID (PMID): {doc.source_id}")
            print(f"📄 Título: {doc.title}")
            print(f"📅 Fecha de Pub: {doc.publication_date}")
            print(f"👥 Autores: {', '.join(doc.authors[:3]) if doc.authors else 'No especificados'}")
            print(f"🔗 URL: {doc.url}")
            print(f"📚 Revista: {doc.metadata.get('journal')}")
            print(f"📝 Resumen (primeros 200 caracteres):")
            print(f"   {doc.abstract[:200]}...\n")

    except Exception as e:
        print(f"❌ Error al ejecutar la prueba: {e}")


if __name__ == "__main__":
    asyncio.run(main())
