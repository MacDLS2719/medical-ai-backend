import json
import os

from typing import List

from groq import AsyncGroq


class MedicalAgentService:

    # ============================================================
    # FUENTES MÉDICAS AUTORIZADAS
    # ============================================================

    ALLOWED_SOURCES = {
        "nejm": "NEJM",
        "lancet": "The Lancet",
        "lancet_global_health": "The Lancet Global Health",
        "lancet_public_health": "The Lancet Public Health",
        "jama": "JAMA",
        "jama_network_open": "JAMA Network Open",
        "bmj": "BMJ",
        "nature_medicine": "Nature Medicine",
        "annals_internal_medicine": "Annals of Internal Medicine",
        "nature": "Nature",
        "science": "Science",
        "science_translational_medicine": "Science Translational Medicine",
        "ctis": "EU Clinical Trials Register / CTIS",
        "who": "WHO",
        "nih": "NIH",
        "ema": "EMA",
        "fda": "FDA",
        "cdc": "CDC",
        "ecdc": "ECDC",
    }

    # ============================================================
    # LIMITES DE CONSUMO
    # ============================================================

    # Para pruebas:
    MAX_RESULTS = 5

    # Máximo de tokens generados por la búsqueda.
    SEARCH_MAX_COMPLETION_TOKENS = 1200

    # Máximo de tokens generados por la normalización.
    NORMALIZE_MAX_COMPLETION_TOKENS = 1800

    # Límite del texto que pasamos de la búsqueda
    # a la segunda llamada.
    MAX_SEARCH_CONTEXT_CHARS = 14000

    # Límites de contenido por resultado.
    MAX_ABSTRACT_CHARS = 1200
    MAX_SUMMARY_CHARS = 500
    MAX_TITLE_CHARS = 500

    def __init__(self):

        self.api_key = os.getenv("GROQ_API_KEY")

        self.model = os.getenv(
            "GROQ_MODEL",
            "openai/gpt-oss-120b",
        )

        if not self.api_key:
            raise RuntimeError(
                "GROQ_API_KEY no está configurada "
                "en las variables de entorno."
            )

        self.client = AsyncGroq(
            api_key=self.api_key
        )

    # ============================================================
    # OBTENER FUENTES
    # ============================================================

    def _get_sources(
        self,
        source_slug: str,
    ) -> str:

        if source_slug == "all":

            return "\n".join(
                f"- {name}"
                for name in self.ALLOWED_SOURCES.values()
            )

        source_name = self.ALLOWED_SOURCES.get(
            source_slug
        )

        if not source_name:
            raise ValueError(
                f"Fuente médica no autorizada: {source_slug}"
            )

        return f"- {source_name}"

    # ============================================================
    # 1. BÚSQUEDA REAL
    # ============================================================

    async def _search_web(
        self,
        query: str,
        source_slug: str,
        max_results: int,
    ) -> str:

        sources_text = self._get_sources(
            source_slug
        )

        if source_slug == "all":

            source_instruction = (
                "Busca únicamente en las fuentes médicas "
                "autorizadas que sean relevantes."
            )

        else:

            source_name = self.ALLOWED_SOURCES[
                source_slug
            ]

            source_instruction = (
                f"Busca únicamente en {source_name}."
            )

        search_prompt = f"""
Eres el agente de búsqueda médica de MIVOR.ai.

Realiza una búsqueda REAL utilizando browser_search.

CONSULTA:
{query}

{source_instruction}

FUENTES AUTORIZADAS:
{sources_text}

OBJETIVO:
Encontrar como máximo {max_results} resultados médicos
reales y relevantes.

REGLAS:

1. Usa búsqueda web real.
2. No respondas usando únicamente conocimiento interno.
3. No inventes artículos.
4. No inventes títulos.
5. No inventes URLs.
6. No inventes fechas.
7. Utiliza únicamente fuentes autorizadas.
8. Prioriza relevancia y publicaciones recientes.
9. Busca como máximo {max_results} resultados.
10. Sé conciso.
11. No hagas análisis médico.
12. No generes explicaciones extensas.
13. Devuelve solamente la información necesaria para
    que otro proceso pueda normalizar los resultados.

Para cada resultado intenta proporcionar:

- source
- title
- abstract o fragmento disponible
- url
- published_at

No agregues información que no haya sido encontrada.
"""

        response = await self.client.chat.completions.create(

            model=self.model,

            messages=[
                {
                    "role": "system",
                    "content": search_prompt,
                },
                {
                    "role": "user",
                    "content": query,
                },
            ],

            temperature=0.1,

            # ====================================================
            # LIMITACIÓN 1:
            # TOKENS MÁXIMOS DE LA BÚSQUEDA
            # ====================================================

            max_completion_tokens=(
                self.SEARCH_MAX_COMPLETION_TOKENS
            ),

            # ====================================================
            # LIMITACIÓN 2:
            # RAZONAMIENTO BAJO PARA LA BÚSQUEDA
            # ====================================================

            reasoning_effort="low",

            tools=[
                {
                    "type": "browser_search"
                }
            ],

            tool_choice="required",
        )

        message = response.choices[0].message

        content = message.content or ""

        print(
            "[MedicalAgent] Búsqueda completada."
        )

        print(
            "[MedicalAgent] Caracteres obtenidos:",
            len(content),
        )

        return content

    # ============================================================
    # REDUCIR CONTEXTO DE BÚSQUEDA
    # ============================================================

    def _limit_search_context(
        self,
        search_results: str,
    ) -> str:

        if not search_results:
            return ""

        if len(search_results) <= self.MAX_SEARCH_CONTEXT_CHARS:
            return search_results

        print(
            "[MedicalAgent] Contexto de búsqueda demasiado "
            "grande. Aplicando límite:",
            self.MAX_SEARCH_CONTEXT_CHARS,
            "caracteres.",
        )

        return search_results[
            :self.MAX_SEARCH_CONTEXT_CHARS
        ]

    # ============================================================
    # 2. NORMALIZAR RESULTADOS CON GROQ
    # ============================================================

    async def _normalize_results(
        self,
        query: str,
        search_results: str,
        source_slug: str,
        max_results: int,
    ) -> List[dict]:

        if source_slug == "all":

            sources_text = "\n".join(
                f"- {name}"
                for name in self.ALLOWED_SOURCES.values()
            )

        else:

            sources_text = (
                f"- {self.ALLOWED_SOURCES[source_slug]}"
            )

        # ========================================================
        # LIMITACIÓN 3:
        # REDUCIR EL CONTEXTO ANTES DE MANDARLO A GROQ
        # ========================================================

        search_results = self._limit_search_context(
            search_results
        )

        normalization_prompt = f"""
Eres el Medical Agent de MIVOR.ai.

NO realices una nueva búsqueda.

Debes normalizar exclusivamente los resultados
obtenidos previamente.

CONSULTA:
{query}

FUENTES AUTORIZADAS:
{sources_text}

RESULTADOS ENCONTRADOS:
{search_results}

TAREA:

Selecciona como máximo {max_results} resultados
relevantes.

REGLAS:

1. Utiliza únicamente información encontrada.
2. No inventes artículos.
3. No inventes títulos.
4. No inventes fechas.
5. No inventes URLs.
6. Conserva exactamente las URLs encontradas.
7. Si no existe URL utiliza null.
8. No agregues fuentes nuevas.
9. Elimina duplicados.
10. Prioriza relevancia.
11. Prioriza publicaciones recientes.
12. El abstract debe proceder de la información encontrada.
13. El summary debe ser muy breve.
14. No agregues explicaciones fuera del JSON.
15. Devuelve máximo {max_results} resultados.

FORMATO:

{{
    "results": [
        {{
            "source": "nombre de la fuente",
            "title": "título real",
            "abstract": "abstract disponible",
            "summary": "resumen breve",
            "url": "URL REAL o null",
            "published_at": "YYYY-MM-DD o null"
        }}
    ]
}}
"""

        response = await self.client.chat.completions.create(

            model=self.model,

            messages=[
                {
                    "role": "system",
                    "content": normalization_prompt,
                },
                {
                    "role": "user",
                    "content": (
                        "Normaliza únicamente los resultados "
                        "en formato JSON."
                    ),
                },
            ],

            temperature=0.1,

            # ====================================================
            # LIMITACIÓN 4:
            # TOKENS MÁXIMOS PARA NORMALIZACIÓN
            # ====================================================

            max_completion_tokens=(
                self.NORMALIZE_MAX_COMPLETION_TOKENS
            ),

            # ====================================================
            # LIMITACIÓN 5:
            # RAZONAMIENTO BAJO
            # ====================================================

            reasoning_effort="low",

            # ====================================================
            # JSON STRUCTURED OUTPUT
            # ====================================================

            response_format={
                "type": "json_object"
            },
        )

        content = (
            response.choices[0].message.content
            or "{}"
        )

        try:

            data = json.loads(content)

        except json.JSONDecodeError as e:

            print(
                "[MedicalAgent] Error parseando JSON:",
                e,
            )

            return []

        results = data.get(
            "results",
            []
        )

        if not isinstance(results, list):
            return []

        return results[:max_results]

    # ============================================================
    # LIMPIEZA FINAL
    # ============================================================

    def _clean_results(
        self,
        results: List[dict],
        max_results: int,
    ) -> List[dict]:

        clean = []

        seen_urls = set()
        seen_titles = set()

        for item in results:

            if not isinstance(item, dict):
                continue

            source = (
                item.get("source")
                or ""
            ).strip()

            title = (
                item.get("title")
                or ""
            ).strip()

            abstract = (
                item.get("abstract")
                or "Sin resumen disponible."
            ).strip()

            summary = (
                item.get("summary")
                or ""
            ).strip()

            url = (
                item.get("url")
                or None
            )

            published_at = (
                item.get("published_at")
                or None
            )

            if not source or not title:
                continue

            # ====================================================
            # LIMITACIÓN 6:
            # EVITAR DUPLICADOS
            # ====================================================

            normalized_title = title.lower()

            if normalized_title in seen_titles:
                continue

            if url and url in seen_urls:
                continue

            seen_titles.add(
                normalized_title
            )

            if url:
                seen_urls.add(url)

            # ====================================================
            # LIMITACIÓN 7:
            # REDUCIR EL TAMAÑO DE LOS CAMPOS
            # ====================================================

            title = title[
                :self.MAX_TITLE_CHARS
            ]

            abstract = abstract[
                :self.MAX_ABSTRACT_CHARS
            ]

            summary = summary[
                :self.MAX_SUMMARY_CHARS
            ]

            clean.append(
                {
                    "source": source,
                    "title": title,
                    "abstract": abstract,
                    "summary": summary,
                    "url": url,
                    "published_at": published_at,
                }
            )

            # ====================================================
            # LIMITACIÓN 8:
            # CORTAR INMEDIATAMENTE EN 5
            # ====================================================

            if len(clean) >= max_results:
                break

        # ========================================================
        # ORDENAR POR FECHA
        # ========================================================

        clean.sort(
            key=lambda item: (
                item.get("published_at")
                or ""
            ),
            reverse=True,
        )

        return clean[:max_results]

    # ============================================================
    # BÚSQUEDA PRINCIPAL
    # ============================================================

    async def search(
        self,
        query: str,
        source_slug: str = "all",
        max_results: int = 5,
    ) -> List[dict]:

        # ========================================================
        # VALIDACIÓN
        # ========================================================

        if not query or not query.strip():
            return []

        if source_slug != "all":

            if source_slug not in self.ALLOWED_SOURCES:

                raise ValueError(
                    f"Fuente médica no autorizada: {source_slug}"
                )

        # ========================================================
        # LIMITACIÓN 9:
        # MÁXIMO ABSOLUTO DE 5 RESULTADOS
        # ========================================================

        max_results = max(
            1,
            min(
                max_results,
                self.MAX_RESULTS,
            ),
        )

        print(
            "[MedicalAgent] ================================="
        )

        print(
            "[MedicalAgent] Iniciando búsqueda médica"
        )

        print(
            "[MedicalAgent] Máximo resultados:",
            max_results,
        )

        print(
            "[MedicalAgent] Modelo:",
            self.model,
        )

        print(
            "[MedicalAgent] ================================="
        )

        # ========================================================
        # PASO 1
        # BÚSQUEDA REAL
        # ========================================================

        print(
            "[MedicalAgent] Paso 1/3 - Búsqueda real..."
        )

        search_results = await self._search_web(
            query=query,
            source_slug=source_slug,
            max_results=max_results,
        )

        if not search_results:

            print(
                "[MedicalAgent] No se obtuvieron "
                "resultados de búsqueda."
            )

            return []

        # ========================================================
        # PASO 2
        # NORMALIZACIÓN
        # ========================================================

        print(
            "[MedicalAgent] Paso 2/3 - Normalizando..."
        )

        normalized_results = (
            await self._normalize_results(
                query=query,
                search_results=search_results,
                source_slug=source_slug,
                max_results=max_results,
            )
        )

        if not normalized_results:

            print(
                "[MedicalAgent] La normalización "
                "no produjo resultados."
            )

            return []

        # ========================================================
        # PASO 3
        # LIMPIEZA
        # ========================================================

        print(
            "[MedicalAgent] Paso 3/3 - Limpieza final..."
        )

        clean = self._clean_results(
            results=normalized_results,
            max_results=max_results,
        )

        print(
            "[MedicalAgent] ================================="
        )

        print(
            "[MedicalAgent] Resultados finales:",
            len(clean),
        )

        print(
            "[MedicalAgent] ================================="
        )

        return clean