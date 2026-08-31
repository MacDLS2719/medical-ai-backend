"""
EvidenceSearchService
=====================
Orquestador de búsqueda para la categoría EVIDENCIA CIENTÍFICA.

Fuentes:
  - PubMed      (artículos científicos indexados)
  - Cochrane    (revisiones sistemáticas)
  - Europe PMC  (literatura biomédica europea)

Estrategia de búsqueda:
  Búsqueda amplia tipo "Google" sobre los artículos:
  limpieza de stopwords genéricos → traducción al inglés
  → consulta paralela a las 3 fuentes → filtrado de fechas
  futuras → ordenado por fecha descendente → traducción
  de títulos/abstracts al idioma del usuario.
"""

import asyncio
import re

from datetime import date, datetime
from typing import List

from app.schemas.medical import NormalizedDocument
from app.services.pubmed_service import PubMedService
from app.services.cochrane_service import CochraneService
from app.services.europe_pmc_service import EuropePMCService
from app.services.translation_service import TranslationService


class EvidenceSearchService:

    # ----------------------------------------------------------
    # CONFIGURACIÓN
    # ----------------------------------------------------------

    MAX_FINAL_RESULTS = 9999
    SOURCE_RESULTS = 100
    MAX_ABSTRACT_WORDS = 40
    MAX_TITLE_CHARS = 1000

    # ----------------------------------------------------------
    # STOPWORDS genéricos (vocabulario de intención, no médico)
    # ----------------------------------------------------------

    GENERIC_STOPWORDS = {
        "articulo", "artículo", "articulos", "artículos",
        "revista", "revistas",
        "investigacion", "investigación", "investigaciones",
        "estudio", "estudios",
        "publicacion", "publicación", "publicaciones",
        "trabajo", "trabajos",
        "informacion", "información",
        "buscar", "busca", "búsqueda", "encuentra", "encontrar",
        "quiero", "necesito", "muestrame", "muéstrame", "puedes", "mostrar",
        "sobre", "acerca",
        "relacionado", "relacionados", "relacionada", "relacionadas",
        "algo", "algunos", "algunas",
        "de", "del", "la", "el", "los", "las",
        "un", "una", "unos", "unas",
        "para", "por", "en", "que", "me", "con",
        "article", "articles", "journal", "journals", "research",
        "study", "studies", "paper", "papers", "publication", "publications",
        "search", "find", "show", "about", "regarding", "related",
        "the", "a", "an", "of", "in", "on", "for",
    }

    def __init__(self):
        self.pubmed = PubMedService()
        self.cochrane = CochraneService()
        self.europe_pmc = EuropePMCService()
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
    # LIMPIAR QUERY (elimina stopwords de intención)
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
            print(f"Error consultando fuente: {result}")
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
        print("EVIDENCE SEARCH (PubMed + Cochrane + EuropePMC)")
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
            self.pubmed.search_and_fetch(search_query, self.SOURCE_RESULTS),
            self.cochrane.search_and_fetch(search_query, self.SOURCE_RESULTS),
            self.europe_pmc.search_and_fetch(search_query, self.SOURCE_RESULTS),
            return_exceptions=True,
        )

        pubmed_results = self._safe(raw[0])
        cochrane_results = self._safe(raw[1])
        europe_pmc_results = self._safe(raw[2])

        print(f"PubMed: {len(pubmed_results)} | Cochrane: {len(cochrane_results)} | EuropePMC: {len(europe_pmc_results)}")

        # 4. FILTRAR Y ORDENAR
        all_docs: List[NormalizedDocument] = (
            self._filter_future(pubmed_results)
            + self._filter_future(cochrane_results)
            + self._filter_future(europe_pmc_results)
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
            "category": "evidence",
            "target_lang": target_lang,
            "total_results": len(all_docs),
            "translation_status": translation_status,
            "sources": {
                "pubmed": {
                    "count": len(pubmed_results),
                    "results": pubmed_results,
                },
                "cochrane": {
                    "count": len(cochrane_results),
                    "results": cochrane_results,
                },
                "europe_pmc": {
                    "count": len(europe_pmc_results),
                    "results": europe_pmc_results,
                },
            },
            "results": all_docs,
        }
