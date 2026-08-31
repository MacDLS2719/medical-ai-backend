"""
DrugSearchService
=================
Orquestador de búsqueda para la categoría MEDICAMENTOS.

Fuentes:
  - openFDA  (etiquetas de medicamentos aprobados por la FDA)

Estrategia de búsqueda:
  La búsqueda de medicamentos es diferente a la de artículos:
  NO se eliminan stopwords porque el nombre del medicamento
  debe permanecer íntegro (ej. "acetaminophen" no debe limpiarse).

  Flujo:
    1. Si el query viene en español, se traduce el nombre del
       medicamento al inglés (ej. "ibuprofeno" → "ibuprofen").
    2. Se consulta openFDA con el nombre traducido.
    3. Los resultados (indications, warnings, dosage) se traducen
       de vuelta al idioma del usuario.
"""

from typing import List

from app.schemas.medical import NormalizedDocument
from app.services.openfda_service import OpenFDAService
from app.services.translation_service import TranslationService


class DrugSearchService:

    # ----------------------------------------------------------
    # CONFIGURACIÓN
    # ----------------------------------------------------------

    SOURCE_RESULTS = 100

    def __init__(self):
        self.openfda = OpenFDAService()
        self.translation = TranslationService()

    # ----------------------------------------------------------
    # NORMALIZAR IDIOMA
    # ----------------------------------------------------------

    @staticmethod
    def normalize_language(language: str | None) -> str:
        if not language:
            return "es"
        language = language.strip().lower().replace("_", "-").split("-")[0]
        return language if language in ("es", "en") else "es"

    # ----------------------------------------------------------
    # TRADUCIR TEXTO
    # ----------------------------------------------------------

    async def _translate(self, text: str, source: str, target: str) -> str:
        if not text or source == target:
            return text
        try:
            translated = await self.translation.translate(
                text=text, source=source, target=target
            )
            return translated if translated else text
        except Exception as e:
            print(f"Drug translation error: {e}")
            return text

    # ----------------------------------------------------------
    # SEARCH
    # ----------------------------------------------------------

    async def search(
        self,
        query: str,
        max_results: int = 10,
        target_lang: str = "es",
    ) -> dict:

        target_lang = self.normalize_language(target_lang)

        print("=" * 50)
        print("DRUG SEARCH (openFDA)")
        print(f"Query original: {query}")
        print(f"Language: {target_lang}")
        print("=" * 50)

        query = query.strip()

        # 1. TRADUCIR NOMBRE DEL MEDICAMENTO A INGLÉS
        # (openFDA indexa por nombres genéricos en inglés)
        search_query = query
        if target_lang != "en" and query:
            try:
                translated = await self.translation.translate_query(
                    text=query, source=target_lang, target="en"
                )
                if (
                    translated
                    and translated != query
                    and "error" not in translated.lower()
                ):
                    search_query = translated
                    print(f"Drug name translated: {query} → {search_query}")
                else:
                    print("⚠️ Traducción fallida, usando nombre original")
            except Exception as e:
                print(f"❌ Drug name translation error: {e}")

        # 2. CONSULTAR openFDA
        print(f"Consultando openFDA con: '{search_query}'")
        try:
            results: List[NormalizedDocument] = await self.openfda.search_and_fetch(
                search_query,
                max_results=min(max_results, self.SOURCE_RESULTS),
            )
        except Exception as e:
            print(f"❌ openFDA error: {e}")
            results = []

        print(f"openFDA resultados: {len(results)}")

        # 3. TRADUCIR RESULTADOS AL IDIOMA DEL USUARIO
        translation_status = {"attempted": False, "successful": False, "message": ""}

        if target_lang != "en" and results:
            translation_status["attempted"] = True
            ok = 0
            for doc in results:
                doc_ok = False
                # Traducir título
                if doc.title:
                    t = await self._translate(doc.title, "en", target_lang)
                    if t and t != doc.title:
                        doc.title = t
                        doc_ok = True
                # Traducir abstract (indicaciones + advertencias + dosificación)
                if doc.abstract:
                    words = doc.abstract.split()
                    # Para medicamentos traducimos más palabras (60) ya que
                    # las indicaciones son clave para el usuario
                    snippet = " ".join(words[:60])
                    t = await self._translate(snippet, "en", target_lang)
                    if t and t != snippet:
                        doc.abstract = t + " " + " ".join(words[60:])
                        doc_ok = True
                if doc_ok:
                    ok += 1

            translation_status["successful"] = ok > 0
            translation_status["message"] = (
                f"Se tradujeron {ok} de {len(results)} medicamentos."
                if ok > 0
                else "No fue posible traducir los resultados."
            )
        else:
            translation_status["message"] = "No se requirió traducción."

        return {
            "query": query,
            "search_query": search_query,
            "category": "drugs",
            "target_lang": target_lang,
            "total_results": len(results),
            "translation_status": translation_status,
            "sources": {
                "openfda": {
                    "count": len(results),
                    "results": results,
                },
            },
            "results": results,
        }
