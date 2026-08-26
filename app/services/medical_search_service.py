import asyncio
import re

from datetime import date, datetime
from typing import List

from app.schemas.medical import NormalizedDocument

from app.services.pubmed_service import PubMedService
from app.services.clinical_trials_service import ClinicalTrialsService
from app.services.cochrane_service import CochraneService
from app.services.translation_service import TranslationService


class MedicalSearchService:

    # ==========================================================
    # CONFIGURACIÓN
    # ==========================================================

    # Queremos devolver mínimo/hasta 10 resultados.
    MAX_FINAL_RESULTS = 10

    # Tamaño máximo del abstract enviado al traductor.
    MAX_ABSTRACT_CHARS = 1800

    # Tamaño máximo del título.
    MAX_TITLE_CHARS = 500

    # ==========================================================
    # STOPWORDS
    # ==========================================================

    GENERIC_STOPWORDS = {
        "articulo",
        "artículo",
        "articulos",
        "artículos",

        "revista",
        "revistas",

        "investigacion",
        "investigación",
        "investigaciones",

        "estudio",
        "estudios",

        "publicacion",
        "publicación",
        "publicaciones",

        "trabajo",
        "trabajos",

        "informacion",
        "información",

        "buscar",
        "busca",
        "búsqueda",
        "encuentra",
        "encontrar",

        "quiero",
        "necesito",
        "muestrame",
        "muéstrame",
        "puedes",
        "mostrar",

        "sobre",
        "acerca",

        "relacionado",
        "relacionados",
        "relacionada",
        "relacionadas",

        "algo",
        "algunos",
        "algunas",

        "de",
        "del",
        "la",
        "el",
        "los",
        "las",

        "un",
        "una",
        "unos",
        "unas",

        "para",
        "por",
        "en",
        "que",
        "me",
        "con",

        "article",
        "articles",

        "journal",
        "journals",

        "research",
        "study",
        "studies",

        "paper",
        "papers",

        "publication",
        "publications",

        "search",
        "find",
        "show",

        "about",
        "regarding",
        "related",

        "the",
        "a",
        "an",
        "of",
        "in",
        "on",
        "for",
    }

    # ==========================================================
    # INIT
    # ==========================================================

    def __init__(
        self,
        pubmed_service: PubMedService,
        clinical_trials_service: ClinicalTrialsService,
        cochrane_service: CochraneService,
    ):

        self.pubmed_service = pubmed_service

        self.clinical_trials_service = (
            clinical_trials_service
        )

        self.cochrane_service = (
            cochrane_service
        )

        self.translation_service = (
            TranslationService()
        )

    # ==========================================================
    # NORMALIZAR IDIOMA
    # ==========================================================

    @staticmethod
    def normalize_language(
        language: str | None
    ) -> str:

        if not language:
            return "es"

        language = language.strip().lower()

        language = language.replace(
            "_",
            "-"
        )

        language = language.split("-")[0]

        if language not in (
            "es",
            "en",
        ):

            return "es"

        return language

    # ==========================================================
    # LIMPIAR CONSULTA
    # ==========================================================

    @classmethod
    def _clean_search_terms(
        cls,
        query: str
    ) -> str:

        if not query:
            return query

        tokens = re.findall(
            r"\(|\)|\bAND\b|\bOR\b|\bNOT\b|[^\s()]+",
            query,
            flags=re.IGNORECASE,
        )

        cleaned_tokens = []

        for token in tokens:

            upper_token = token.upper()

            if upper_token in (
                "(",
                ")",
                "AND",
                "OR",
                "NOT",
            ):

                cleaned_tokens.append(
                    upper_token
                )

                continue

            if (
                token.lower()
                in cls.GENERIC_STOPWORDS
            ):

                continue

            cleaned_tokens.append(
                token
            )

        cleaned_query = (
            " ".join(cleaned_tokens)
            .strip()
        )

        return (
            cleaned_query
            if cleaned_query
            else query
        )

    # ==========================================================
    # TRADUCIR TEXTO
    # ==========================================================

    async def translate_text(
        self,
        text: str,
        source_lang: str,
        target_lang: str
    ) -> str:

        if not text:
            return text

        source_lang = (
            self.normalize_language(
                source_lang
            )
        )

        target_lang = (
            self.normalize_language(
                target_lang
            )
        )

        if source_lang == target_lang:
            return text

        try:

            return await (
                self.translation_service
                .translate(
                    text=text,
                    source=source_lang,
                    target=target_lang,
                )
            )

        except Exception as e:

            print(
                f"Translation error: {e}"
            )

            return text

    # ==========================================================
    # PARSEAR FECHA
    # ==========================================================

    @staticmethod
    def _parse_date(
        date_str: str | None
    ) -> date | None:

        if not date_str:
            return None

        date_str = date_str.strip()

        formats = [
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m",
            "%Y",
        ]

        for fmt in formats:

            try:

                return datetime.strptime(
                    date_str,
                    fmt
                ).date()

            except ValueError:

                continue

        return None

    # ==========================================================
    # FILTRAR FECHAS FUTURAS
    # ==========================================================

    @classmethod
    def _filter_future_dates(
        cls,
        docs: List[NormalizedDocument]
    ) -> List[NormalizedDocument]:

        today = date.today()

        filtered = []

        for doc in docs:

            parsed = cls._parse_date(
                doc.publication_date
            )

            if parsed is None:

                filtered.append(doc)

                continue

            if parsed <= today:

                filtered.append(doc)

            else:

                print(
                    "Documento descartado por "
                    f"fecha futura "
                    f"({doc.publication_date}): "
                    f"{doc.title}"
                )

        return filtered

    # ==========================================================
    # ORDENAR POR FECHA
    # ==========================================================

    @classmethod
    def _get_sort_key(
        cls,
        doc: NormalizedDocument
    ) -> date:

        parsed = cls._parse_date(
            doc.publication_date
        )

        return (
            parsed
            if parsed
            else date.min
        )

    # ==========================================================
    # BUSCAR
    # ==========================================================

    async def search(
        self,
        query: str,
        max_results: int = 10,
        target_lang: str = "es"
    ) -> dict:

        target_lang = (
            self.normalize_language(
                target_lang
            )
        )

        # ------------------------------------------------------
        # SIEMPRE BUSCAR HASTA 10 POR FUENTE
        # ------------------------------------------------------

        source_limit = max(
            10,
            min(
                max_results,
                10
            )
        )

        print(
            "=========================================="
        )

        print(
            "MEDICAL SEARCH"
        )

        print(
            f"TARGET LANGUAGE: {target_lang}"
        )

        print(
            f"QUERY ORIGINAL: {query}"
        )

        print(
            "RESULTADOS POR FUENTE: 10"
        )

        print(
            "RESULTADOS FINALES: 10"
        )

        print(
            "=========================================="
        )

        # ======================================================
        # LIMPIAR CONSULTA
        # ======================================================

        cleaned_query = (
            self._clean_search_terms(
                query
            )
        )

        if cleaned_query != query:

            print(
                f"QUERY CLEANED: "
                f"{query} -> "
                f"{cleaned_query}"
            )

        # ======================================================
        # TRADUCIR CONSULTA
        # ======================================================

        search_query = cleaned_query

        if (
            target_lang != "en"
            and cleaned_query
        ):

            print(
                "Translating search query..."
            )

            search_query = (
                await self.translation_service
                .translate_query(
                    text=cleaned_query,
                    source=target_lang,
                    target="en",
                )
            )

            print(
                f"QUERY TRANSLATED: "
                f"{cleaned_query} -> "
                f"{search_query}"
            )

        # ======================================================
        # CONSULTAR LAS 3 FUENTES EN PARALELO
        # ======================================================

        results = await asyncio.gather(

            self.pubmed_service
            .search_and_fetch(
                search_query,
                source_limit,
            ),

            self.clinical_trials_service
            .search_and_fetch(
                search_query,
                source_limit,
            ),

            self.cochrane_service
            .search_and_fetch(
                search_query,
                source_limit,
            ),

            return_exceptions=True,
        )

        # ======================================================
        # PROTEGER RESULTADOS
        # ======================================================

        pubmed_results = (
            self._safe_result(
                results[0]
            )
        )

        clinical_trials_results = (
            self._safe_result(
                results[1]
            )
        )

        cochrane_results = (
            self._safe_result(
                results[2]
            )
        )

        # ======================================================
        # FILTRAR FECHAS
        # ======================================================

        pubmed_results = (
            self._filter_future_dates(
                pubmed_results
            )
        )

        clinical_trials_results = (
            self._filter_future_dates(
                clinical_trials_results
            )
        )

        cochrane_results = (
            self._filter_future_dates(
                cochrane_results
            )
        )

        # ======================================================
        # ORDENAR CADA FUENTE
        # ======================================================

        pubmed_results.sort(
            key=self._get_sort_key,
            reverse=True
        )

        clinical_trials_results.sort(
            key=self._get_sort_key,
            reverse=True
        )

        cochrane_results.sort(
            key=self._get_sort_key,
            reverse=True
        )

        # ======================================================
        # UNIFICAR
        # ======================================================

        all_results = (
            pubmed_results
            + clinical_trials_results
            + cochrane_results
        )

        # ======================================================
        # ORDENAR TODO
        # ======================================================

        all_results.sort(
            key=self._get_sort_key,
            reverse=True
        )

        # ======================================================
        # TOMAR 10 RESULTADOS
        # ======================================================

        final_results = all_results[
            :self.MAX_FINAL_RESULTS
        ]

        print(
            "=========================================="
        )

        print(
            f"RESULTADOS OBTENIDOS: "
            f"{len(all_results)}"
        )

        print(
            f"RESULTADOS FINALES: "
            f"{len(final_results)}"
        )

        print(
            "=========================================="
        )

        # ======================================================
        # TRADUCIR LOS 10 RESULTADOS
        # ======================================================

        if (
            target_lang != "en"
            and final_results
        ):

            print(
                "=========================================="
            )

            print(
                f"TRANSLATING "
                f"{len(final_results)} DOCUMENTS"
            )

            print(
                "FROM: en"
            )

            print(
                f"TO: {target_lang}"
            )

            print(
                "=========================================="
            )

            # --------------------------------------------------
            # SECUENCIAL
            #
            # TranslationService ya tiene Semaphore(1).
            # Aquí también mantenemos procesamiento secuencial
            # para reducir presión sobre Render.
            # --------------------------------------------------

            for index, doc in enumerate(
                final_results,
                start=1
            ):

                print(
                    f"TRADUCIENDO DOCUMENTO "
                    f"{index}/"
                    f"{len(final_results)}"
                )

                # ==============================================
                # TÍTULO
                # ==============================================

                if doc.title:

                    original_title = (
                        doc.title
                    )

                    title_to_translate = (
                        original_title[
                            :self.MAX_TITLE_CHARS
                        ]
                    )

                    translated_title = (
                        await self.translate_text(
                            text=title_to_translate,
                            source_lang="en",
                            target_lang=target_lang,
                        )
                    )

                    if translated_title:

                        doc.title = (
                            translated_title
                        )

                # ==============================================
                # ABSTRACT
                # ==============================================

                if doc.abstract:

                    original_abstract = (
                        doc.abstract
                    )

                    abstract_to_translate = (
                        original_abstract[
                            :self.MAX_ABSTRACT_CHARS
                        ]
                    )

                    translated_abstract = (
                        await self.translate_text(
                            text=abstract_to_translate,
                            source_lang="en",
                            target_lang=target_lang,
                        )
                    )

                    if translated_abstract:

                        doc.abstract = (
                            translated_abstract
                        )

                # ------------------------------------------------
                # Pequeña pausa
                # ------------------------------------------------

                await asyncio.sleep(0.05)

            print(
                "=========================================="
            )

            print(
                "TRADUCCIÓN COMPLETADA"
            )

            print(
                "=========================================="

            )

        else:

            print(
                "Translation not required."
            )

        # ======================================================
        # RESULTADO FINAL
        # ======================================================

        print(
            "=========================================="
        )

        print(
            "Medical search completed."
        )

        print(
            f"Language: {target_lang}"
        )

        print(
            f"Total documents returned: "
            f"{len(final_results)}"
        )

        print(
            "=========================================="
        )

        # ======================================================
        # RESPUESTA
        # ======================================================

        return {

            "query": query,

            "search_query": search_query,

            "target_lang": target_lang,

            "total_results": len(
                final_results
            ),

            "sources": {

                "pubmed": {

                    "count": len(
                        pubmed_results
                    ),

                    "results": pubmed_results,
                },

                "clinical_trials": {

                    "count": len(
                        clinical_trials_results
                    ),

                    "results": (
                        clinical_trials_results
                    ),
                },

                "cochrane": {

                    "count": len(
                        cochrane_results
                    ),

                    "results": (
                        cochrane_results
                    ),
                },
            },

            "results": final_results,
        }

    # ==========================================================
    # PROTEGER RESULTADO
    # ==========================================================

    @staticmethod
    def _safe_result(
        result
    ):

        if isinstance(
            result,
            Exception
        ):

            print(
                "ERROR consultando "
                f"fuente médica: {result}"
            )

            return []

        return result