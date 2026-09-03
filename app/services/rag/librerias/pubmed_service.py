import httpx
import xmltodict
from typing import List, Optional
from os import getenv
from app.services.rag.schemas import NormalizedDocument

class PubMedService:
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def __init__(self):
        self.api_key = getenv("PUBMED_API_KEY", "")
        self.email = getenv("PUBMED_EMAIL", "developer@example.com")
        self.tool = getenv("PUBMED_TOOL", "rag_app")

    def _get_base_params(self) -> dict:
        params = {
            "email": self.email,
            "tool": self.tool,
        }
        if self.api_key:
            params["api_key"] = self.api_key
        return params

    async def search_pmids(self, query: str, max_results: int = 5) -> List[str]:
        """Paso 1: Buscar artículos y retornar lista de PMIDs."""
        url = f"{self.BASE_URL}/esearch.fcgi"
        params = {
            **self._get_base_params(),
            "db": "pubmed",
            "term": query,
            "retmode": "json",
            "retmax": max_results,
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("esearchresult", {}).get("idlist", [])

    async def fetch_details(self, pmid_list: List[str]) -> List[NormalizedDocument]:
        """Paso 2: Obtener detalles del artículo y normalizar estructura."""
        if not pmid_list:
            return []

        url = f"{self.BASE_URL}/efetch.fcgi"
        params = {
            **self._get_base_params(),
            "db": "pubmed",
            "id": ",".join(pmid_list),
            "retmode": "xml",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            
            # Convertir XML a Diccionario de Python
            parsed_data = xmltodict.parse(response.text)
            
            articles = parsed_data.get("PubmedArticleSet", {}).get("PubmedArticle", [])
            # Asegurar que siempre sea una lista cuando hay 1 solo resultado
            if isinstance(articles, dict):
                articles = [articles]

            normalized_docs = []
            for art in articles:
                doc = self._parse_article(art)
                if doc:
                    normalized_docs.append(doc)

            return normalized_docs

    def _parse_article(self, article: dict) -> Optional[NormalizedDocument]:
        """Procesar y limpiar los campos del diccionario XML."""
        try:
            medline = article.get("MedlineCitation", {})
            article_data = medline.get("Article", {})

            # ID (PMID)
            pmid = str(medline.get("PMID", {}).get("#text", medline.get("PMID", "")))

            # Título
            title = article_data.get("ArticleTitle", "Sin título")

            # Abstract (Manejar casos de abstracts estructurados o texto simple)
            abstract_raw = article_data.get("Abstract", {}).get("AbstractText", "")
            if isinstance(abstract_raw, list):
                abstract = " ".join([item.get("#text", str(item)) if isinstance(item, dict) else str(item) for item in abstract_raw])
            elif isinstance(abstract_raw, dict):
                abstract = abstract_raw.get("#text", "")
            else:
                abstract = str(abstract_raw)

            # Autores
            authors = []
            author_list = article_data.get("AuthorList", {}).get("Author", [])
            if isinstance(author_list, dict):
                author_list = [author_list]
            for auth in author_list:
                last_name = auth.get("LastName", "")
                fore_name = auth.get("ForeName", "")
                if last_name:
                    authors.append(f"{fore_name} {last_name}".strip())

            # Fecha de publicación
            pub_date_data = article_data.get("Journal", {}).get("JournalIssue", {}).get("PubDate", {})
            year = pub_date_data.get("Year", "")
            month = pub_date_data.get("Month", "01")
            pub_date = f"{year}-{month}" if year else None

            # Revista
            journal_title = article_data.get("Journal", {}).get("Title", "")

            return NormalizedDocument(
                source_id=pmid,
                source_type="pubmed",
                title=title,
                abstract=abstract if abstract else "Sin resumen disponible.",
                authors=authors,
                publication_date=pub_date,
                url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                metadata={"journal": journal_title}
            )
        except Exception as e:
            print(f"Error procesando artículo: {e}")
            return None

    async def search_and_fetch(self, query: str, max_results: int = 5) -> List[NormalizedDocument]:
        """Método unificado de consulta completa."""
        pmids = await self.search_pmids(query, max_results=max_results)
        return await self.fetch_details(pmids)
