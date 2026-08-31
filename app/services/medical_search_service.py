import asyncio
import re

from datetime import date, datetime
from typing import List

from app.schemas.medical import NormalizedDocument

from app.services.pubmed_service import PubMedService
from app.services.clinical_trials_service import ClinicalTrialsService
from app.services.cochrane_service import CochraneService
from app.services.europe_pmc_service import EuropePMCService
from app.services.who_ictrp_service import WHOICTRPService
from app.services.translation_service import TranslationService


class MedicalSearchService:

    # ==========================================================
    # CONFIGURACIÓN
    # ==========================================================

    # Cantidad máxima de resultados que devolvemos al frontend
    # Eliminado límite para mostrar todos los resultados encontrados
    MAX_FINAL_RESULTS = 9999  # Practicamente sin límite

    # Cantidad máxima que solicitamos a cada fuente
    SOURCE_RESULTS = 100  # Aumentado para obtener muchos más resultados

    # SOLO 40 palabras del abstract serán enviadas al traductor
    MAX_ABSTRACT_WORDS = 40

    # Límite de seguridad para títulos (traducir completo)
    MAX_TITLE_CHARS = 1000

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
        europe_pmc_service = None,
        who_ictrp_service = None,
    ):

        self.pubmed_service = pubmed_service

        self.clinical_trials_service = (
            clinical_trials_service
        )

        self.cochrane_service = (
            cochrane_service
        )

        # Inicializar servicios opcionales de forma segura
        try:
            self.europe_pmc_service = europe_pmc_service if europe_pmc_service else EuropePMCService()
        except Exception as e:
            print(f"Error inicializando EuropePMCService: {e}")
            self.europe_pmc_service = None

        try:
            self.who_ictrp_service = who_ictrp_service if who_ictrp_service else WHOICTRPService()
        except Exception as e:
            print(f"Error inicializando WHOICTRPService: {e}")
            self.who_ictrp_service = None

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

            # --------------------------------------------------
            # CONSERVAR OPERADORES BOOLEANOS
            # --------------------------------------------------

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

            # --------------------------------------------------
            # ELIMINAR PALABRAS GENÉRICAS (solo si hay otros términos)
            # --------------------------------------------------

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

        # Si la limpieza elimina todo, devolver la original
        if not cleaned_query:
            print("⚠️ La limpieza eliminó todos los términos, usando consulta original")
            return query

        return cleaned_query

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

        # ------------------------------------------------------
        # NO TRADUCIR SI YA ESTÁ EN EL IDIOMA DESTINO
        # ------------------------------------------------------

        if source_lang == target_lang:
            return text

        try:

            translated = await (
                self.translation_service
                .translate(
                    text=text,
                    source=source_lang,
                    target=target_lang,
                )
            )

            # --------------------------------------------------
            # SI EL TRADUCTOR DEVUELVE VACÍO
            # --------------------------------------------------

            if not translated:

                return text

            return translated

        except Exception as e:

            print(
                f"Translation error: {e}"
            )

            # --------------------------------------------------
            # SI FALLA, CONSERVAMOS EL ORIGINAL
            # --------------------------------------------------

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

            # --------------------------------------------------
            # SI NO SE PUEDE PARSEAR LA FECHA
            # --------------------------------------------------

            if parsed is None:

                filtered.append(doc)

                continue

            # --------------------------------------------------
            # SOLO DOCUMENTOS HASTA HOY
            # --------------------------------------------------

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
    # BUSCAR (NO STREAMING - Versión original)
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
            "RESULTADOS POR FUENTE: 100"
        )

        print(
            "RESULTADOS FINALES: Sin límite"
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

            try:

                translated_query = (
                    await self.translation_service
                    .translate_query(
                        text=cleaned_query,
                        source=target_lang,
                        target="en",
                    )
                )

                # Validar que la traducción sea válida
                if (
                    translated_query
                    and translated_query != cleaned_query
                    and "Error" not in translated_query
                    and "error" not in translated_query.lower()
                ):
                    search_query = translated_query
                    print(
                        f"QUERY TRANSLATED: "
                        f"{cleaned_query} -> "
                        f"{search_query}"
                    )
                else:
                    print(
                        "⚠️ Traducción falló, devolvió error o es igual al original"
                    )
                    print("Usando consulta original sin traducir")
                    search_query = cleaned_query

            except Exception as e:

                print(
                    f"❌ Query translation error: {e}"
                )

                print("Usando consulta original sin traducir")
                search_query = cleaned_query

        # ======================================================
        # CONSULTAR LAS 5 FUENTES EN PARALELO (con manejo seguro)
        # ======================================================

        print(
            "Consultando PubMed, ClinicalTrials, Cochrane, Europe PMC y WHO ICTRP en paralelo..."
        )

        print(f"Query a buscar: '{search_query}'")
        print(f"Resultados por fuente: {self.SOURCE_RESULTS}")

        # Crear lista de tareas de forma segura
        tasks = [
            self.pubmed_service.search_and_fetch(search_query, self.SOURCE_RESULTS),
            self.clinical_trials_service.search_and_fetch(search_query, self.SOURCE_RESULTS),
            self.cochrane_service.search_and_fetch(search_query, self.SOURCE_RESULTS),
        ]

        # Agregar servicios opcionales solo si existen
        if self.europe_pmc_service:
            tasks.append(self.europe_pmc_service.search_and_fetch(search_query, self.SOURCE_RESULTS))
        else:
            print("Europe PMC service no disponible, usando placeholder")
            tasks.append(asyncio.sleep(0))  # Placeholder

        if self.who_ictrp_service:
            tasks.append(self.who_ictrp_service.search_and_fetch(search_query, self.SOURCE_RESULTS))
        else:
            print("WHO ICTRP service no disponible, usando placeholder")
            tasks.append(asyncio.sleep(0))  # Placeholder

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # ======================================================
        # PROTEGER RESULTADOS (con manejo de placeholders)
        # ======================================================

        pubmed_results = self._safe_result(results[0])
        clinical_trials_results = self._safe_result(results[1])
        cochrane_results = self._safe_result(results[2])

        # Manejo seguro de servicios opcionales
        europe_pmc_results = []
        who_ictrp_results = []

        if len(results) > 3 and self.europe_pmc_service:
            europe_pmc_results = self._safe_result(results[3])
        else:
            print("Europe PMC: usando lista vacía (servicio no disponible)")

        if len(results) > 4 and self.who_ictrp_service:
            who_ictrp_results = self._safe_result(results[4])
        else:
            print("WHO ICTRP: usando lista vacía (servicio no disponible)")

        print(
            f"PubMed resultados: "
            f"{len(pubmed_results)}"
        )

        print(
            f"ClinicalTrials resultados: "
            f"{len(clinical_trials_results)}"
        )

        print(
            f"Cochrane resultados: "
            f"{len(cochrane_results)}"
        )

        print(
            f"Europe PMC resultados: "
            f"{len(europe_pmc_results)}"
        )

        print(
            f"WHO ICTRP resultados: "
            f"{len(who_ictrp_results)}"
        )

        # ======================================================
        # FILTRAR FECHAS FUTURAS
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

        europe_pmc_results = (
            self._filter_future_dates(
                europe_pmc_results
            )
        )

        who_ictrp_results = (
            self._filter_future_dates(
                who_ictrp_results
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

        europe_pmc_results.sort(
            key=self._get_sort_key,
            reverse=True
        )

        who_ictrp_results.sort(
            key=self._get_sort_key,
            reverse=True
        )

        # ======================================================
        # UNIFICAR
        # ======================================================

        all_results: List[
            NormalizedDocument
        ] = (
            pubmed_results
            + clinical_trials_results
            + cochrane_results
            + europe_pmc_results
            + who_ictrp_results
        )

        # ======================================================
        # ORDENAR TODOS LOS RESULTADOS
        # ======================================================

        all_results.sort(
            key=self._get_sort_key,
            reverse=True
        )

        print(
            f"TOTAL RESULTADOS DISPONIBLES: "
            f"{len(all_results)}"
        )

        # ======================================================
        # TOMAR TODOS LOS RESULTADOS (sin límite)
        # ======================================================

        final_results = all_results  # Ya ordenados por fecha

        print(
            f"RESULTADOS FINALES: "
            f"{len(final_results)} (todos los resultados encontrados)"
        )

        # ======================================================
        # TRADUCCIÓN (OPCIONAL - NO BLOQUEA RESULTADOS)
        # ======================================================

        translation_status = {
            "attempted": False,
            "successful": False,
            "message": "",
            "language": target_lang
        }

        if (
            target_lang != "en"
            and final_results
        ):

            translation_status["attempted"] = True

            print(
                "=========================================="
            )

            print(
                f"TRADUCIENDO "
                f"{len(final_results)} DOCUMENTOS"
            )

            print(
                "TÍTULOS COMPLETOS + "
                f"PRIMEROS {self.MAX_ABSTRACT_WORDS} "
                "PALABRAS DEL ABSTRACT"
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

            successful_translations = 0
            failed_translations = 0

            # --------------------------------------------------
            # PROCESAMIENTO SECUENCIAL CON TIMEOUT
            #
            # Esto es intencional para reducir consumo
            # de memoria/CPU en Render.
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

                doc_translated = False

                # ==================================================
                # TÍTULO
                # ==================================================

                if doc.title:

                    original_title = (
                        doc.title
                    )

                    title_to_translate = (
                        original_title[
                            :self.MAX_TITLE_CHARS
                        ]
                    )

                    print(
                        "  -> Traduciendo título..."
                    )

                    try:
                        translated_title = (
                            await self.translate_text(
                                text=title_to_translate,
                                source_lang="en",
                                target_lang=target_lang,
                            )
                        )

                        if translated_title and translated_title != original_title:

                            # ------------------------------------------
                            # Si el título supera el límite,
                            # conservamos el resto.
                            # ------------------------------------------

                            if len(original_title) > self.MAX_TITLE_CHARS:

                                doc.title = (
                                    translated_title
                                    + original_title[
                                        self.MAX_TITLE_CHARS:
                                    ]
                                )

                            else:

                                doc.title = (
                                    translated_title
                                )

                            doc_translated = True

                    except Exception as e:
                        print(f"  ⚠️ Error traduciendo título: {e}")
                        failed_translations += 1

                # ==================================================
                # ABSTRACT
                # ==================================================

                if doc.abstract:

                    original_abstract = (
                        doc.abstract
                    )

                    # ----------------------------------------------
                    # SOLO PRIMERAS 40 PALABRAS
                    # ----------------------------------------------

                    words = original_abstract.split()
                    abstract_words_to_translate = words[:self.MAX_ABSTRACT_WORDS]
                    abstract_to_translate = " ".join(abstract_words_to_translate)

                    if abstract_to_translate:

                        print(
                            "  -> Traduciendo primeras "
                            f"{self.MAX_ABSTRACT_WORDS} "
                            "palabras del abstract..."
                        )

                        try:
                            translated_abstract = (
                                await self.translate_text(
                                    text=abstract_to_translate,
                                    source_lang="en",
                                    target_lang=target_lang,
                                )
                            )

                            if translated_abstract and translated_abstract != abstract_to_translate:

                                # --------------------------------------
                                # IMPORTANTE:
                                #
                                # NO reemplazamos todo el abstract.
                                # Traducimos únicamente las primeras
                                # 40 palabras y dejamos el resto
                                # original.
                                # --------------------------------------

                                remaining_words = words[self.MAX_ABSTRACT_WORDS:]
                                doc.abstract = (
                                    translated_abstract
                                    + " "
                                    + " ".join(remaining_words)
                                )

                                doc_translated = True

                        except Exception as e:
                            print(f"  ⚠️ Error traduciendo abstract: {e}")
                            failed_translations += 1

                if doc_translated:
                    successful_translations += 1

                # --------------------------------------------------
                # Pequeña pausa para reducir presión sobre CPU
                # --------------------------------------------------

                await asyncio.sleep(0.05)

            # --------------------------------------------------
            # ESTADO FINAL DE TRADUCCIÓN
            # --------------------------------------------------

            translation_status["successful"] = successful_translations > 0

            if successful_translations == len(final_results):
                translation_status["message"] = "Todos los documentos fueron traducidos exitosamente."
            elif successful_translations > 0:
                translation_status["message"] = f"Se tradujeron {successful_translations} de {len(final_results)} documentos. Algunos resultados pueden estar en inglés."
            else:
                translation_status["message"] = "No fue posible traducir los documentos. Los resultados se muestran en inglés debido a problemas con el servicio de traducción."

            print(
                "=========================================="
            )

            print(
                f"TRADUCCIÓN COMPLETADA: {successful_translations}/{len(final_results)} exitosas"
            )

            print(
                "=========================================="
            )

        else:

            translation_status["message"] = "No se requirió traducción (idioma original: inglés)."
            print("Translation not required.")

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

            "translation_status": translation_status,

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

                "europe_pmc": {

                    "count": len(
                        europe_pmc_results
                    ),

                    "results": (
                        europe_pmc_results
                    ),

                },

                "who_ictrp": {

                    "count": len(
                        who_ictrp_results
                    ),

                    "results": (
                        who_ictrp_results
                    ),

                },
            },

            "results": final_results,
        }

    # ==========================================================
    # BUSCAR Y TRANSMITIR (STREAMING)
    # ==========================================================

    async def search_stream(
        self,
        query: str,
        max_results: int = 10,
        target_lang: str = "es"
    ):
        """
        Generador asíncrono que cede (yield) resultados a medida que
        se van obteniendo de las distintas fuentes.
        Formato de salida: NDJSON (Newline Delimited JSON).
        """
        import json

        target_lang = self.normalize_language(target_lang)

        print("==========================================")
        print("MEDICAL SEARCH STREAMING")
        print(f"TARGET LANGUAGE: {target_lang}")
        print(f"QUERY ORIGINAL: {query}")
        print("==========================================")

        cleaned_query = self._clean_search_terms(query)
        if cleaned_query != query:
            print(f"QUERY CLEANED: {query} -> {cleaned_query}")

        search_query = cleaned_query

        if target_lang != "en" and cleaned_query:
            try:
                translated_query = await self.translation_service.translate_query(
                    text=cleaned_query,
                    source=target_lang,
                    target="en",
                )
                if (translated_query and translated_query != cleaned_query and 
                    "error" not in translated_query.lower()):
                    search_query = translated_query
                    print(f"QUERY TRANSLATED: {cleaned_query} -> {search_query}")
                else:
                    search_query = cleaned_query
            except Exception as e:
                print(f"❌ Query translation error: {e}")
                search_query = cleaned_query

        # Enviar primer chunk: metadatos de inicio
        yield json.dumps({
            "type": "meta",
            "query": query,
            "search_query": search_query,
            "target_lang": target_lang
        }) + "\n"

        print(f"Consultando fuentes con: '{search_query}'")

        # Wrapper para mantener el nombre de la fuente
        async def fetch_source(name: str, coro):
            res = await coro
            return name, res

        # Lanzar tareas en paralelo
        tasks = [
            fetch_source("pubmed", self.pubmed_service.search_and_fetch(search_query, self.SOURCE_RESULTS)),
            fetch_source("clinical_trials", self.clinical_trials_service.search_and_fetch(search_query, self.SOURCE_RESULTS)),
            fetch_source("cochrane", self.cochrane_service.search_and_fetch(search_query, self.SOURCE_RESULTS)),
            fetch_source("europe_pmc", self.europe_pmc_service.search_and_fetch(search_query, self.SOURCE_RESULTS)),
            fetch_source("who_ictrp", self.who_ictrp_service.search_and_fetch(search_query, self.SOURCE_RESULTS))
        ]

        for future in asyncio.as_completed(tasks):
            try:
                source_name, source_results = await future
                source_results = self._safe_result(source_results)
                source_results = self._filter_future_dates(source_results)
                
                print(f"[{source_name.upper()}] devolvió {len(source_results)} resultados.")

                # Traducir los resultados si es necesario
                if target_lang != "en" and source_results:
                    for doc in source_results:
                        if doc.title:
                            try:
                                t = await self.translate_text(
                                    doc.title[:self.MAX_TITLE_CHARS], "en", target_lang
                                )
                                if t and t != doc.title:
                                    doc.title = t
                            except:
                                pass
                        if doc.abstract:
                            try:
                                words = doc.abstract.split()
                                snippet = " ".join(words[:self.MAX_ABSTRACT_WORDS])
                                t = await self.translate_text(snippet, "en", target_lang)
                                if t and t != snippet:
                                    doc.abstract = t + " " + " ".join(words[self.MAX_ABSTRACT_WORDS:])
                            except:
                                pass
                        # Ceder espacio al event loop
                        await asyncio.sleep(0.01)

                # Ceder los resultados de esta fuente al cliente
                yield json.dumps({
                    "type": "results",
                    "source": source_name,
                    "count": len(source_results),
                    "data": [doc.model_dump() for doc in source_results]
                }) + "\n"

            except Exception as e:
                print(f"Error procesando resultados de {source_name}: {e}")
                yield json.dumps({
                    "type": "error",
                    "source": source_name,
                    "message": str(e)
                }) + "\n"

        # Señal de fin
        yield json.dumps({
            "type": "done"
        }) + "\n"
        print("Búsqueda streaming finalizada.")


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