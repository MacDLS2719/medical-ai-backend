import json
import asyncio
import urllib.parse
from typing import Any
import aiohttp
from openai import AsyncOpenAI
from app.core.config import settings

# ============================================================
# MAPEO DE NOMBRES
# ============================================================
SOURCE_NAME_MAP = {
    "nejm": "nejm",
    "new england journal of medicine": "nejm",
    "the lancet": "lancet",
    "lancet": "lancet",
    "lancet global health": "lancet_global_health",
    "the lancet global health": "lancet_global_health",
    "lancet public health": "lancet_public_health",
    "the lancet public health": "lancet_public_health",
    "jama": "jama",
    "jama network open": "jama_network_open",
    "bmj": "bmj",
    "british medical journal": "bmj",
    "nature medicine": "nature_medicine",
    "nature": "nature",
    "annals of internal medicine": "annals_internal_medicine",
    "science": "science",
    "science translational medicine": "science_translational_medicine",
    "who": "who",
    "world health organization": "who",
    "nih": "nih",
    "nih/pubmed": "pubmed",
    "pubmed": "pubmed",
    "ema": "ema",
    "fda": "fda",
    "cdc": "cdc",
    "ecdc": "ecdc",
    "clinicaltrials": "clinicaltrials",
    "clinicaltrials.gov": "clinicaltrials",
    "cochrane": "cochrane",
    "europepmc": "europepmc",
    "europe pmc": "europepmc",
}

# ============================================================
# UTILIDADES
# ============================================================

def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()

def _normalize_doi(doi: str) -> str:
    doi = _clean(doi)
    if not doi:
        return ""
    prefixes = [
        "https://doi.org/", "http://doi.org/",
        "https://dx.doi.org/", "http://dx.doi.org/",
        "doi:", "DOI:",
    ]
    for prefix in prefixes:
        if doi.lower().startswith(prefix.lower()):
            doi = doi[len(prefix):]
            break
    return doi.strip()

# ============================================================
# PROMPT PRINCIPAL
# ============================================================
SYSTEM_PROMPT = """
Eres un investigador médico experto de MIVOR.ai.

Tu tarea es analizar evidencia médica y devolver exclusivamente JSON válido.

IMPORTANTE:
1. RESUMEN MÁS AMPLIO: No te limites solo a los artículos provistos. Aporta de tu propio conocimiento médico sobre la enfermedad o condición consultada. Desarrolla un análisis exhaustivo y detallado.
2. CITAS EN TEXTO: A medida que construyas tu resumen bien amplio sobre lo que el usuario te pregunto, debes citar explícitamente las referencias dentro del texto usando corchetes numéricos (ej. [1], [2]).
3. MÍNIMO DE REFERENCIAS REALES Y CON CONTENIDO: Proporciona al menos 15 referencias médicas de alta calidad. SOLO INCLUYE ARTÍCULOS SI ESTÁS 100% SEGURO DE QUE EL ENLACE FUNCIONA, EL TÍTULO ES EXACTO, Y EL ARTÍCULO TIENE UN ABSTRACT (RESUMEN) O TEXTO COMPLETO PÚBLICAMENTE DISPONIBLE. No incluyas enlaces a páginas vacías o donde no se pueda leer nada del contenido.
4. ENLACES VARIADOS Y EXACTOS: No uses solo PubMed. Usa enlaces directos a las revistas y organizaciones (WHO, CDC, NEJM, Lancet, Nature, etc.) en el campo "url". EL TÍTULO DEL ARTÍCULO DEBE COINCIDIR EXACTAMENTE CON EL ARTÍCULO QUE SE ABRE EN EL ENLACE. No pongas un título falso para un enlace real que lleva a otro tema.
5. FUENTES VERIFICADAS: Si la fuente proviene de las principales revistas médicas o bases científicas de primer nivel (NEJM, Lancet, JAMA, BMJ, Nature, PubMed, NIH, Europe PMC, WHO, CDC), clasifícala como verificada (verified: true). Si viene de otros repositorios, márcalas como (verified: false).
8. CERO ALUCINACIONES EN ENLACES: NO INVENTES PMIDs, DOIs NI URLs. Si no tienes certeza absoluta del identificador real de un artículo y su título exacto, omítelo por completo. ¡Prohibido generar identificadores al azar!
9. IDIOMA DE RESPUESTA: Responde y redacta el resumen íntegramente en el MISMO IDIOMA en el que el usuario formuló su pregunta.

FORMATO JSON OBLIGATORIO:
{
    "summary": "Resumen general y amplio de la evidencia, incluyendo tu conocimiento clínico sobre la condición. Incluye citas [1], [2]...",
    "references": [
        {
            "title": "Título EXACTO del artículo que se abre en el enlace",
            "source": "Nombre exacto de revista u organización",
            "year": "2024",
            "abstract": "Resumen detallado de los hallazgos (OBLIGATORIO: no dejar vacío, el enlace debe contener esta info)",
            "pmid": "",
            "doi": "10.xxxx/xxxxx",
            "url": "https://www.who.int/... (enlace directo y real)",
            "verified": true
        }
    ]
}
"""

PRESTIGIOUS_SOURCES_CONTEXT = """
Fuentes OBLIGATORIAS y ALTERNATIVAS para complementar y dar variedad:
1. FUENTES VERIFICADAS (verified: true): NEJM, The Lancet, JAMA, BMJ, Nature Medicine, Annals of Internal Medicine, PubMed, NIH, Europe PMC (europepmc.org).
   IMPORTANTE: Europe PMC es una fuente verificada — si aparece un artículo de Europe PMC, síempre ponlo como verified: true.
2. OTRAS FUENTES (verified: false): Puedes aportar investigaciones de centros de investigación universitarios, repositorios de universidades, y bases de datos independientes.
Asegúrate de incluir siempre sus DOIs si los conoces.
"""

# ============================================================
# PROMPT UNIVERSITARIO (modo especializado)
# ============================================================
UNIVERSITY_SYSTEM_PROMPT = """
Eres un investigador académico especialista en literatura científica universitaria de MIVOR.ai.

Tu tarea es analizar investigación académica y devolver exclusivamente JSON válido.

IMPORTANTE — MODO UNIVERSITARIO:
1. FUENTES EXCLUSIVAMENTE UNIVERSITARIAS Y DE CENTROS DE INVESTIGACIÓN: Prioriza artículos de:
   - Repositorios universitarios (Harvard, MIT, Oxford, Stanford, Johns Hopkins, Mayo Clinic, UNAM, etc.)
   - Preprints verificados: bioRxiv, medRxiv
   - Bases académicas: Semantic Scholar, Europe PMC, SSRN, ResearchGate (solo DOI verificados)
   - Centros de investigación: NIH, WHO, CDC, INSERM, Max Planck, Karolinska
   - Tesis doctorales y working papers de universidades de prestigio
2. CITAS EN TEXTO: A medida que construyas tu resumen bien amplio sobre lo que el usuario te pregunto, Cita referencias dentro del resumen usando [1], [2], etc.
3. MÍNIMO 15 REFERENCIAS Y CON CONTENIDO: Todas con DOI o URL real verificado. Nunca inventes identificadores. SOLO INCLUYE ARTÍCULOS QUE TENGAN UN ABSTRACT O TEXTO COMPLETO PÚBLICO. No incluyas enlaces de páginas sin información.
4. ENLACES VARIADOS Y EXACTOS: Usa los enlaces directos a los repositorios o centros. EL TÍTULO DEL ARTÍCULO DEBE COINCIDIR EXACTAMENTE CON EL ENLACE QUE SE ABRE. No inventes títulos para enlaces que van a otros documentos.
5. CLASIFICACIÓN: verified: false para todo (son fuentes académicas no clínicas peer-reviewed de primer nivel). Excepción: si aparece un artículo de revista top, verified: true.
6. CERO ALUCINACIONES: NO inventes PMIDs, DOIs ni URLs. Si no conoces el enlace exacto, omite ese campo.
7. SÍNTESIS EXTENSA: El resumen académico debe ser considerablemente MÁS LARGO, detallado y estructurado como una síntesis de nivel universitario (tipo ensayo o artículo de revisión).
8. IDIOMA DE RESPUESTA: Responde y redacta la síntesis íntegramente en el MISMO IDIOMA en el que el usuario formuló su consulta.

FORMATO JSON OBLIGATORIO:
{{
    "summary": "Síntesis académica muy extensa, profunda y detallada (tipo revisión bibliográfica), enfocada en investigación universitaria. Incluye citas [1], [2]...",
    "references": [
        {{
            "title": "Título EXACTO del artículo que se abre en el enlace",
            "source": "Universidad o centro de investigación",
            "year": "2024",
            "abstract": "Resumen detallado de los hallazgos (OBLIGATORIO: no dejar vacío, el enlace debe contener esta info)",
            "pmid": "",
            "doi": "10.xxxx/xxxxx",
            "url": "https://... (enlace directo prioritario)",
            "verified": false
        }}
    ]
}}
"""

UNIVERSITY_SOURCES_CONTEXT = """
Fuentes PRIORITARIAS para la búsqueda universitaria:
1. Repositorios universitarios: Harvard Dataverse, MIT DSpace, Oxford Research Archive, Stanford PURL
2. Preprints académicos: bioRxiv (biorxiv.org), medRxiv (medrxiv.org)
3. Bases académicas: Europe PMC (europepmc.org), Semantic Scholar, PubMed Central (PMC)
4. Centros de investigación internacionales: NIH (nih.gov), WHO (who.int), CDC (cdc.gov), INSERM, Karolinska Institute
5. Redes de investigación: ResearchGate (solo artículos con DOI real), Academia.edu
Incluye el nombre de la universidad o centro en el campo "source".
"""

# ============================================================
# SERVICIO
# ============================================================
class OpenAIService:
    def __init__(self):
        api_key = settings.OPENAI_API_KEY
        self.client = AsyncOpenAI(api_key=api_key) if api_key else None
        self.model = settings.OPENAI_MODEL

    async def _spot_check_url(self, session: aiohttp.ClientSession, url: str, allow_403: bool = True) -> tuple[bool, str]:
        if not url or not url.startswith("http"):
            return False, url
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
            # Usar GET en vez de HEAD porque algunos servidores devuelven 403 a HEAD pero 404 a GET
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=8), allow_redirects=True, headers=headers) as response:
                final_redirected_url = str(response.url)
                if response.status == 404:
                    return False, final_redirected_url
                html_preview = await response.text()
                html_preview = html_preview.lower()
                # Catch fake 200 OK pages that son en realidad 404s (Lancet, Nature, Elsevier, BMJ, etc.)
                error_phrases = [
                    "404 not found", "page not found", "article not found", 
                    "the page you are looking for", "error 404", "could not be found",
                    "we can't find", "no results were found", "page unavailable"
                ]
                if any(phrase in html_preview for phrase in error_phrases):
                    return False, final_redirected_url
                
                if response.status < 400:
                    return True, final_redirected_url
                if allow_403 and response.status in (401, 403):
                    return True, final_redirected_url
                return False, final_redirected_url
        except Exception:
            return False, url

    async def _search_crossref_doi(self, session: aiohttp.ClientSession, title: str) -> str:
        """Busca el título en Crossref para encontrar el DOI exacto."""
        if not title:
            return ""
        
        query = urllib.parse.quote(title)
        url = f"https://api.crossref.org/works?query.title={query}&select=DOI,title&rows=3"
        
        try:
            headers = {"User-Agent": "MIVOR.ai (mailto:contact@mivor.ai)"}
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=8), headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    items = data.get("message", {}).get("items", [])
                    for item in items:
                        # Verificación flexible: comparar primeras palabras significativas del título
                        item_title = item.get("title", [""])[0].lower()
                        query_words = set(title.lower().split()[:6])  # primeras 6 palabras
                        item_words = set(item_title.split()[:8])
                        overlap = len(query_words & item_words)
                        if overlap >= 3 or title.lower()[:40] in item_title or item_title[:40] in title.lower():
                            return item.get("DOI", "")
        except Exception:
            pass
        return ""

    async def _call_openai(self, user_prompt: str) -> dict:
        if not self.client:
            raise RuntimeError("OPENAI_API_KEY no está configurada.")
        
        response = await self.client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
        content = response.choices[0].message.content
        if not content:
            return {"summary": "", "references": []}
            
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            cleaned = content.strip()
            if cleaned.startswith("```json"): cleaned = cleaned[7:]
            if cleaned.startswith("```"): cleaned = cleaned[3:]
            if cleaned.endswith("```"): cleaned = cleaned[:-3]
            return json.loads(cleaned.strip())
    def _get_source_from_url(self, final_url: str, fallback: str) -> str:
        """Extrae el nombre real de la revista u organización desde el dominio de la URL."""
        if not final_url:
            return fallback or "Medical Journal"
            
        domain_names = {
            'nejm.org': 'NEJM',
            'thelancet.com': 'The Lancet',
            'jamanetwork.com': 'JAMA',
            'bmj.com': 'BMJ',
            'nature.com': 'Nature',
            'science.org': 'Science',
            'annals.org': 'Annals of Internal Medicine',
            'pubmed.ncbi.nlm.nih.gov': 'PubMed',
            'ncbi.nlm.nih.gov': 'PubMed / NIH',
            'pmc.ncbi.nlm.nih.gov': 'PubMed Central',
            'europepmc.org': 'Europe PMC',
            'cochranelibrary.com': 'Cochrane Library',
            'who.int': 'OMS / WHO',
            'cdc.gov': 'CDC',
            'nih.gov': 'NIH',
            'fda.gov': 'FDA',
            'ema.europa.eu': 'EMA',
            'clinicaltrials.gov': 'ClinicalTrials.gov',
            'medrxiv.org': 'medRxiv',
            'biorxiv.org': 'bioRxiv',
            'scielo.org': 'SciELO',
            'scielo.br': 'SciELO Brasil',
            'scielo.cl': 'SciELO Chile',
            'scielo.conicyt.cl': 'SciELO Chile',
            'scielo.isciii.es': 'SciELO España',
            'redalyc.org': 'Redalyc',
            'researchgate.net': 'ResearchGate',
            'semanticscholar.org': 'Semantic Scholar',
            'springer.com': 'Springer',
            'springerlink.com': 'SpringerLink',
            'link.springer.com': 'Springer',
            'wiley.com': 'Wiley',
            'onlinelibrary.wiley.com': 'Wiley Online Library',
            'elsevier.com': 'Elsevier',
            'sciencedirect.com': 'ScienceDirect',
            'cell.com': 'Cell',
            'jci.org': 'Journal of Clinical Investigation',
            'ahajournals.org': 'AHA Journals',
            'academic.oup.com': 'Oxford Academic',
            'karger.com': 'Karger',
            'mdpi.com': 'MDPI',
            'frontiersin.org': 'Frontiers',
            'plos.org': 'PLOS',
            'plosone.org': 'PLOS ONE',
            'plosmedicine.org': 'PLOS Medicine',
        }
        
        try:
            parsed = urllib.parse.urlparse(final_url)
            host = parsed.netloc.lower()
            if host.startswith("www."):
                host = host[4:]
                
            if host in ("doi.org", "dx.doi.org"):
                path_parts = [p for p in parsed.path.split("/") if p]
                if path_parts:
                    prefix = path_parts[0]
                    doi_prefixes = {
                        '10.1056': 'NEJM',
                        '10.1016': 'Elsevier / ScienceDirect',
                        '10.1001': 'JAMA',
                        '10.1136': 'BMJ',
                        '10.1038': 'Nature',
                        '10.1126': 'Science',
                        '10.7326': 'Annals of Internal Medicine',
                        '10.1182': 'Blood (ASH)',
                        '10.1200': 'JCO (ASCO)',
                        '10.1093': 'Oxford University Press',
                        '10.1002': 'Wiley',
                        '10.1007': 'Springer',
                        '10.3389': 'Frontiers',
                        '10.1371': 'PLOS',
                        '10.3390': 'MDPI',
                    }
                    if prefix in doi_prefixes:
                        return doi_prefixes[prefix]
                return fallback or "DOI"

            if host in domain_names:
                return domain_names[host]
                
            for k, v in domain_names.items():
                if host.endswith(k):
                    return v
                    
            parts = host.split('.')
            base = parts[-2] if len(parts) >= 2 else parts[0]
            return base.capitalize()
            
        except Exception:
            return fallback or "Medical Journal"

    async def _resolve_references(self, references: list) -> list:
        """
        Garantiza que la URL abre DIRECTAMENTE el artículo verificando que no dé 404.
        Prioridad: Validado(URL) > Validado(DOI) > Validado(PMID) > Validado(Crossref).
        """
        if not references:
            return []

        resolved = []
        async with aiohttp.ClientSession() as session:
            for ref in references:
                pmid = _clean(ref.get("pmid"))
                doi = _normalize_doi(ref.get("doi"))
                url = _clean(ref.get("url"))
                title = _clean(ref.get("title"))
                abstract = _clean(ref.get("abstract"))

                # Filtro de abstract más permisivo: solo descartamos si está completamente vacío
                # o contiene frases explícitas de ausencia. Abstracts cortos son válidos.
                if not abstract or "sin resumen" in abstract.lower() or "no abstract available" in abstract.lower():
                    print(f"Referencia descartada por falta de abstract: {title}")
                    continue

                final_url = ""

                # 1. CROSSREF PRIMERO: Garantiza que el Enlace corresponde al Título.
                # Ignoramos el DOI inventado por la IA y buscamos el título real.
                if title:
                    crossref_doi = await self._search_crossref_doi(session, title)
                    if crossref_doi:
                        candidate = f"https://doi.org/{crossref_doi}"
                        is_valid, resolved_url = await self._spot_check_url(session, candidate)
                        if is_valid:
                            final_url = resolved_url

                # 2. DOI proporcionado por GPT: si Crossref no lo encontró y hay DOI
                if not final_url and doi:
                    candidate = f"https://doi.org/{doi}"
                    is_valid, resolved_url = await self._spot_check_url(session, candidate)
                    if is_valid:
                        final_url = resolved_url

                # 3. URL DIRECTA: para organizaciones como OMS, CDC, preprints, etc.
                # allow_403=True porque NEJM, Lancet, Nature y Elsevier devuelven 403
                # a bots aunque el artículo existe realmente.
                if not final_url and url.startswith("http"):
                    is_valid, resolved_url = await self._spot_check_url(session, url, allow_403=True)
                    if is_valid:
                        final_url = resolved_url

                # 4. PMID: Último recurso
                if not final_url and pmid.isdigit():
                    candidate = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                    try:
                        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}
                        async with session.get(candidate, timeout=aiohttp.ClientTimeout(total=8), allow_redirects=True, headers=headers) as response:
                            if response.status < 400:
                                html_text = await response.text()
                                if "is not available" not in html_text and "No results were found" not in html_text:
                                    final_url = str(response.url)
                    except Exception:
                        pass

                # Descartar si no hay un enlace validado
                if not final_url:
                    print(f"Referencia descartada (sin URL válida): {title}")
                    continue

                # Guardar solo si encontramos un enlace válido real
                if final_url:
                    ref["_final_url"] = final_url
                    ref["source"] = self._get_source_from_url(final_url, ref.get("source"))
                    resolved.append(ref)

        return resolved

    def _deduplicate_references(self, references: list) -> list:
        unique = []
        seen = set()
        for ref in references:
            pmid = _clean(ref.get("pmid"))
            doi = _normalize_doi(ref.get("doi"))
            title = _clean(ref.get("title")).lower()
            key = f"pmid:{pmid}" if pmid else (f"doi:{doi}" if doi else f"title:{title}")
            
            if not key or key in seen:
                continue
            seen.add(key)
            unique.append(ref)
        return unique

    def _fix_summary_citations(self, summary: str, original_refs: list, final_refs: list) -> str:
        """
        Corrige los números de cita en el texto del resumen para que coincidan
        con la lista final de referencias, después de haber eliminado duplicados o descartado enlaces.
        """
        import re
        
        def _get_key(ref):
            return _clean(ref.get("title")).lower()
            
        final_keys = [_get_key(r) for r in final_refs]
        
        old_to_new = {}
        for i, ref in enumerate(original_refs, 1):
            k = _get_key(ref)
            if k in final_keys:
                old_to_new[i] = final_keys.index(k) + 1
            else:
                old_to_new[i] = None

        def replace_match(match):
            try:
                idx = int(match.group(1))
                if idx in old_to_new:
                    new_idx = old_to_new[idx]
                    if new_idx is not None:
                        return f"[{new_idx}]"
                    else:
                        return ""
            except ValueError:
                pass
            return match.group(0)

        # Reemplazar citas del tipo [1], [2]
        new_summary = re.sub(r'\[(\d+)\]', replace_match, summary)
        
        # Limpiar posibles espacios extra que queden al eliminar citas: "Hola . " -> "Hola."
        new_summary = new_summary.replace(" []", "").replace("[]", "")
        new_summary = re.sub(r'\s+\.', '.', new_summary)
        new_summary = re.sub(r'\s+,', ',', new_summary)
        
        return new_summary

    def _build_response(self, summary: str, references: list) -> dict:
        """Devuelve un objeto estructurado en lugar de un string markdown."""
        return {
            "summary": summary,
            "references": references
        }

    def _build_context(self, documents: list) -> str:
        if not documents:
            return "No hay artículos disponibles en las librerías locales."
        
        docs_sorted = sorted(documents, key=lambda doc: doc.publication_date or "0000-00-00", reverse=True)
        context_parts = []
        for index, doc in enumerate(docs_sorted, 1):
            title = _clean(getattr(doc, "title", ""))
            source = _clean(getattr(doc, "source_type", ""))
            date = _clean(getattr(doc, "publication_date", ""))
            abstract = _clean(getattr(doc, "abstract", ""))
            url = _clean(getattr(doc, "url", ""))
            
            context_parts.append(
                f"--- Artículo {index} ---\nTítulo: {title}\nFuente: {source}\nFecha: {date}\nResumen: {abstract[:800]}\nURL original garantizada: {url}\n"
            )
        return "\n".join(context_parts)

    async def generate_research_summary(self, query: str, documents: list) -> dict:
        if not self.client:
            return {"summary": "Error: OPENAI_API_KEY no está configurada.", "references": []}

        try:
            context_str = self._build_context(documents)

            user_prompt = f"Pregunta clínica: {query}\n\nARTÍCULOS LOCALES (úsalos obligatoriamente como base):\n{context_str}\n\nFUENTES ADICIONALES:\n{PRESTIGIOUS_SOURCES_CONTEXT}"

            data = await self._call_openai(user_prompt)
            summary = _clean(data.get("summary", ""))
            references = data.get("references", [])
            
            if not isinstance(references, list):
                references = []

            # Deduplicar inicial
            normalized = self._deduplicate_references(references)
            
            # Resolver enlaces exactos
            resolved = await self._resolve_references(normalized)

            # Fallback estricto
            if len(resolved) < 15:
                needed = 15 - len(resolved)
                print(f"[OpenAIService] Faltan {needed} referencias. Ejecutando fallback...")
                
                fb_prompt = f"Pregunta: {query}\nTenemos {len(resolved)} referencias. Necesito EXACTAMENTE {needed} referencias médicas más de fuentes de alto prestigio. Usa artículos reales y muy conocidos. Asegúrate de incluir URLs o DOIs funcionales."
                
                try:
                    fb_data = await self._call_openai(fb_prompt)
                    fb_refs = fb_data.get("references", [])
                    fb_normalized = self._deduplicate_references(fb_refs)
                    fb_resolved = await self._resolve_references(fb_normalized)
                    
                    resolved.extend(fb_resolved)
                except Exception as e:
                    print(f"Error en fallback: {e}")

            resolved = self._deduplicate_references(resolved)
            
            # Corregir la numeración de las citas en el texto
            summary = self._fix_summary_citations(summary, references, resolved)
            
            # Devolver objeto JSON estructurado para el frontend
            return self._build_response(summary, resolved)

        except Exception as e:
            print(f"[OpenAIService] Error general: {e}")
            return {"summary": f"Error al generar el resumen: {str(e)}", "references": []}

    async def generate_university_summary(self, query: str, documents: list) -> dict:
        """
        Modo universitario: especializado en investigación académica de universidades
        y centros de investigación.
        """
        if not self.client:
            return {"summary": "Error: OPENAI_API_KEY no está configurada.", "references": []}

        try:
            context_str = self._build_context(documents)
            user_prompt = (
                f"Consulta académica: {query}\n\n"
                f"ARTÍCULOS LOCALES (base de referencia):\n{context_str}\n\n"
                f"FUENTES UNIVERSITARIAS PRIORITARIAS:\n{UNIVERSITY_SOURCES_CONTEXT}"
            )

            # Llamada con el prompt universitario especializado
            if not self.client:
                raise RuntimeError("OPENAI_API_KEY no está configurada.")

            response = await self.client.chat.completions.create(
                model=self.model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": UNIVERSITY_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
            )
            content = response.choices[0].message.content or ""
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                cleaned = content.strip().strip("```json").strip("```").strip()
                data = json.loads(cleaned)

            summary = _clean(data.get("summary", ""))
            references = data.get("references", [])
            if not isinstance(references, list):
                references = []

            normalized = self._deduplicate_references(references)
            resolved = await self._resolve_references(normalized)

            # Fallback si faltan referencias
            if len(resolved) < 15:
                needed = 15 - len(resolved)
                print(f"[OpenAIService-University] Faltan {needed} referencias. Ejecutando fallback...")
                fb_prompt = (
                    f"Consulta: {query}\nTenemos {len(resolved)} referencias universitarias. "
                    f"Necesito EXACTAMENTE {needed} referencias más de universidades o centros de investigación "
                    f"con DOIs o URLs verificadas reales."
                )
                try:
                    fb_resp = await self.client.chat.completions.create(
                        model=self.model,
                        response_format={"type": "json_object"},
                        messages=[
                            {"role": "system", "content": UNIVERSITY_SYSTEM_PROMPT},
                            {"role": "user", "content": fb_prompt},
                        ],
                        temperature=0.2,
                    )
                    fb_data = json.loads(fb_resp.choices[0].message.content or "{}")
                    fb_resolved = await self._resolve_references(
                        self._deduplicate_references(fb_data.get("references", []))
                    )
                    resolved.extend(fb_resolved)
                except Exception as e:
                    print(f"Error en fallback universitario: {e}")

            resolved = self._deduplicate_references(resolved)
            
            # Corregir la numeración de las citas en el texto
            summary = self._fix_summary_citations(summary, references, resolved)
            
            return self._build_response(summary, resolved)

        except Exception as e:
            print(f"[OpenAIService-University] Error: {e}")
            return {"summary": f"Error al generar el resumen universitario: {str(e)}", "references": []}

openai_service = OpenAIService()