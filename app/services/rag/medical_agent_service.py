import json
import os
from typing import List, Optional

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

    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

        if not self.api_key:
            raise RuntimeError(
                "GROQ_API_KEY no está configurada en las variables de entorno."
            )

        self.client = AsyncGroq(api_key=self.api_key)

    # ============================================================
    # BÚSQUEDA PRINCIPAL — retorna artículos estructurados
    # ============================================================

    async def search(
        self,
        query: str,
        source_slug: str = "all",
        max_results: int = 10,
    ) -> List[dict]:
        """
        Busca artículos científicos publicados en las fuentes autorizadas
        usando el LLM como agente de recuperación de conocimiento.

        Retorna una lista de dicts con:
          - source    : nombre de la revista / fuente
          - title     : título del artículo
          - abstract  : resumen del artículo
          - url       : URL original
          - published_at : fecha de publicación (YYYY-MM-DD)
        ordenados del más reciente al más antiguo.
        """

        # ── Determinar fuentes a usar ──
        if source_slug == "all":
            sources_text = "\n".join(
                f"- {name}" for name in self.ALLOWED_SOURCES.values()
            )
            source_instruction = (
                "Busca en TODAS las fuentes autorizadas listadas a continuación."
            )
        else:
            source_name = self.ALLOWED_SOURCES.get(source_slug, source_slug)
            sources_text = f"- {source_name}"
            source_instruction = (
                f"Busca ÚNICAMENTE en la fuente: {source_name}."
            )

        system_prompt = f"""Eres el Medical Agent de MIVOR.ai.
Tu función es recuperar artículos científicos reales y publicados sobre el tema consultado.

INSTRUCCIÓN: {source_instruction}

FUENTES AUTORIZADAS:
{sources_text}

REGLAS:
1. Devuelve EXCLUSIVAMENTE artículos que existan realmente en las fuentes autorizadas.
2. NO inventes títulos, autores, fechas ni URLs.
3. Si no conoces un artículo con certeza, NO lo incluyas.
4. Devuelve la respuesta en formato JSON válido con esta estructura exacta:

{{
  "results": [
    {{
      "source": "nombre exacto de la revista o fuente",
      "title": "título completo del artículo",
      "abstract": "resumen o descripción del artículo (mínimo 2 oraciones)",
      "url": "URL real del artículo o de la fuente",
      "published_at": "YYYY-MM-DD"
    }}
  ]
}}

5. Ordena los resultados del más reciente al más antiguo.
6. Devuelve entre 3 y {max_results} artículos relevantes.
7. Responde SOLAMENTE con el JSON, sin texto adicional antes ni después."""

        user_prompt = f"Busca artículos científicos publicados sobre: {query}"

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                max_completion_tokens=4096,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content or "{}"
            data = json.loads(content)
            results = data.get("results", [])

            # Validar y limpiar cada resultado
            clean = []
            for item in results:
                if not isinstance(item, dict):
                    continue
                title = (item.get("title") or "").strip()
                source = (item.get("source") or "").strip()
                if not title or not source:
                    continue
                clean.append({
                    "source": source,
                    "title": title,
                    "abstract": (item.get("abstract") or "Sin resumen disponible.").strip(),
                    "url": (item.get("url") or None),
                    "published_at": (item.get("published_at") or None),
                })

            return clean

        except json.JSONDecodeError as e:
            print(f"[MedicalAgent] JSON parse error: {e}")
            return []
        except Exception as e:
            print(f"[MedicalAgent] Error: {e}")
            raise