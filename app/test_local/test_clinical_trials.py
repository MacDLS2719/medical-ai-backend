import asyncio
from dotenv import load_dotenv

load_dotenv()

from services.clinical_trials_service import ClinicalTrialsService


async def main():
    print("🔬 Iniciando prueba de conexión con ClinicalTrials.gov API v2...")

    service = ClinicalTrialsService()
    query_term = "Diabetes Type 2"
    max_results = 3

    print(f"\n🔍 Buscando ensayos clínicos sobre: '{query_term}' (Máximo {max_results} resultados)\n")

    try:
        documents = await service.search_and_fetch(query=query_term, max_results=max_results)

        if not documents:
            print("⚠️ No se encontraron resultados.")
            return

        print(f"✅ ¡Éxito! Se obtuvieron {len(documents)} ensayos clínicos normalizados:\n")

        for i, doc in enumerate(documents, start=1):
            print(f"--- Ensayo Clínico #{i} ---")
            print(f"📌 ID (NCT): {doc.source_id}")
            print(f"📄 Título: {doc.title}")
            print(f"🚦 Estado del ensayo: {doc.metadata.get('status')}")
            print(f"🧪 Intervenciones: {', '.join(doc.metadata.get('interventions', [])) or 'No especificadas'}")
            print(f"📅 Fecha inicio: {doc.publication_date}")
            print(f"🔗 URL: {doc.url}")
            print(f"📝 Resumen (primeros 200 caracteres):")
            print(f"   {doc.abstract[:200]}...\n")

    except Exception as e:
        print(f"❌ Error al ejecutar la prueba: {e}")


if __name__ == "__main__":
    asyncio.run(main())