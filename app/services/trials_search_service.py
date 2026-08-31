"""
TrialsSearchService
===================
Orquestador de búsqueda para la categoría ENSAYOS CLÍNICOS.

Fuentes:
  - ClinicalTrials.gov  (registro principal de ensayos)
  - WHO ICTRP           (portal internacional de ensayos OMS)

Estrategia de búsqueda:
  Igual que EvidenceSearchService: limpieza de stopwords
  → traducción al inglés → consulta paralela → filtrado
  → ordenado → traducción de resultados al idioma del usuario.

  Nota: ClinicalTrials y WHO ICTRP trabajan bien con términos
  de condición/patología en inglés. La limpieza de stopwords
  ayuda a que la persona pueda escribir en lenguaje natural
  (ej. "quiero ver ensayos sobre diabetes tipo 2") y el
  servicio extrae el término relevante automáticamente.
"""

import asyncio
import re

from datetime import date, datetime
from typing import List

from app.schemas.medical import NormalizedDocument
from app.services.clinical_trials_service import ClinicalTrialsService
from app.services.who_ictrp_service import WHOICTRPService
from app.services.translation_service import TranslationService


class TrialsSearchService:

    # ----------------------------------------------------------
    # CONFIGURACIÓN
    # ----------------------------------------------------------

    MAX_FINAL_RESULTS = 9999
    SOURCE_RESULTS = 100
    MAX_ABSTRACT_WORDS = 40
    MAX_TITLE_CHARS = 1000

    # ----------------------------------------------------------
    # STOPWORDS genéricos (vocabulario de intención)
    # ----------------------------------------------------------

    GENERIC_STOPWORDS = {
        "ensayo", "ensayos", "ensayo clinico", "ensayos clinicos",
        "ensayo clínico", "ensayos clínicos",
        "trial", "trials", "clinical trial", "clinical trials",
        "estudio", "estudios", "estudio clinico", "estudios clinicos",
        "investigacion", "investigación", "investigaciones",
        "buscar", "busca", "búsqueda", "encuentra", "encontrar",
        "quiero", "necesito", "muestrame", "muéstrame", "puedes", "mostrar",
        "sobre", "acerca",
        "de", "del", "la", "el", "los", "las",
        "un", "una", "unos", "unas",
        "para", "por", "en", "que", "me", "con",
        "the", "a", "an", "of", "in", "on", "for",
        "search", "find", "show", "about", "regarding",
    }

    def __init__(self):
        self.clinical_trials = ClinicalTrialsService()
        self.who_ictrp = WHOICTRPService()
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
    # LIMPIAR QUERY
    # ----------------------------------------------------------

    @classmethod
    def _clean_query(cls, query: str) -> str:
        if not query:
            return query

        tokens = re.findall(
            r"\(|\)|\bAND\b|\bOR\b|\bNOT\b|[^\s()]+",
            query,
            flags=re.IGNORECASE,
        )

        cleaned = []
        for token in tokens:
            upper = token.upper()
            if upper in ("(", ")", "AND", "OR", "NOT"):
                cleaned.append(upper)
                continue
            if token.lower() not in cls.GENERIC_STOPWORDS:
                cleaned.append(token)

        result = " ".join(cleaned).strip()
        return result if result else query

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
            print(f"Translation error: {e}")
            return text

    # ----------------------------------------------------------
    # PARSEAR FECHA
    # ----------------------------------------------------------

    @staticmethod
    def _parse_date(date_str: str | None) -> date | None:
        if not date_str:
            return None
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m", "%Y"):
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue
        return None

    # ----------------------------------------------------------
    # FILTRAR FECHAS FUTURAS
    # ----------------------------------------------------------

    @classmethod
    def _filter_future(cls, docs: List[NormalizedDocument]) -> List[NormalizedDocument]:
        today = date.today()
        result = []
        for doc in docs:
            parsed = cls._parse_date(doc.publication_date)
            if parsed is None or parsed <= today:
                result.append(doc)
        return result

    # ----------------------------------------------------------
    # SORT KEY
    # ----------------------------------------------------------

    @classmethod
    def _sort_key(cls, doc: NormalizedDocument) -> date:
        parsed = cls._parse_date(doc.publication_date)
        return parsed if parsed else date.min

    # ----------------------------------------------------------
    # SAFE RESULT
    # ----------------------------------------------------------

    @staticmethod
    def _safe(result):
        if isinstance(result, Exception):
            print(f"Error consultando fuente de ensayos: {result}")
            return []
        return result

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
        print("TRIALS SEARCH (ClinicalTrials + WHO ICTRP)")
        print(f"Query original: {query}")
        print(f"Language: {target_lang}")
        print("=" * 50)

        # 1. LIMPIAR QUERY
        cleaned = self._clean_query(query)
        if cleaned != query:
            print(f"Query cleaned: {query} → {cleaned}")

        # 2. TRADUCIR QUERY A INGLÉS
        search_query = cleaned
        if target_lang != "en" and cleaned:
            try:
                translated = await self.translation.translate_query(
                    text=cleaned, source=target_lang, target="en"
                )
                if (
                    translated
                    and translated != cleaned
                    and "error" not in translated.lower()
                ):
                    search_query = translated
                    print(f"Query translated: {cleaned} → {search_query}")
                else:
                    print("⚠️ Traducción fallida, usando query original")
            except Exception as e:
                print(f"❌ Query translation error: {e}")

        # 3. CONSULTAR EN PARALELO
        print(f"Consultando fuentes con: '{search_query}'")
        raw = await asyncio.gather(
            self.clinical_trials.search_and_fetch(search_query, self.SOURCE_RESULTS),
            self.who_ictrp.search_and_fetch(search_query, self.SOURCE_RESULTS),
            return_exceptions=True,
        )

        clinical_results = self._safe(raw[0])
        who_results = self._safe(raw[1])

        print(f"ClinicalTrials: {len(clinical_results)} | WHO ICTRP: {len(who_results)}")

        # 4. FILTRAR Y ORDENAR
        all_docs: List[NormalizedDocument] = (
            self._filter_future(clinical_results)
            + self._filter_future(who_results)
        )
        all_docs.sort(key=self._sort_key, reverse=True)

        print(f"Total tras filtros: {len(all_docs)}")

        # 5. TRADUCIR RESULTADOS AL IDIOMA DEL USUARIO
        translation_status = {"attempted": False, "successful": False, "message": ""}

        if target_lang != "en" and all_docs:
            translation_status["attempted"] = True
            ok = 0
            for doc in all_docs:
                doc_ok = False
                if doc.title:
                    t = await self._translate(
                        doc.title[:self.MAX_TITLE_CHARS], "en", target_lang
                    )
                    if t and t != doc.title:
                        doc.title = t
                        doc_ok = True
                if doc.abstract:
                    words = doc.abstract.split()
                    snippet = " ".join(words[:self.MAX_ABSTRACT_WORDS])
                    t = await self._translate(snippet, "en", target_lang)
                    if t and t != snippet:
                        doc.abstract = t + " " + " ".join(words[self.MAX_ABSTRACT_WORDS:])
                        doc_ok = True
                if doc_ok:
                    ok += 1
                await asyncio.sleep(0.05)

            translation_status["successful"] = ok > 0
            translation_status["message"] = (
                f"Se tradujeron {ok} de {len(all_docs)} documentos."
                if ok > 0
                else "No fue posible traducir los documentos."
            )
        else:
            translation_status["message"] = "No se requirió traducción."

        return {
            "query": query,
            "search_query": search_query,
            "category": "trials",
            "target_lang": target_lang,
            "total_results": len(all_docs),
            "translation_status": translation_status,
            "sources": {
                "clinical_trials": {
                    "count": len(clinical_results),
                    "results": clinical_results,
                },
                "who_ictrp": {
                    "count": len(who_results),
                    "results": who_results,
                },
            },
            "results": all_docs,
        }
