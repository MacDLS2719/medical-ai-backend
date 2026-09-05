import httpx
import xmltodict
from typing import List, Optional
from os import getenv
from app.services.rag.schemas import NormalizedDocument

class CochraneService:
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def __init__(self):
        self.api_key = getenv("PUBMED_API_KEY", "")
        self.email = getenv("PUBMED_EMAIL", "")
        self.tool = getenv("PUBMED_TOOL", "")

    def _get_base_params(self) -> dict:
        params = {
            "email": self.email,
            "tool": self.tool,
        }
        if self.api_key:
            params["api_key"] = self.api_key
        return params

    async def search_and_fetch(self, query: str, max_results: int = 5) -> List[NormalizedDocument]:
        """Busca revisiones sistemáticas en Cochrane Library a través de NCBI."""
        # Filtro estricto para recuperar únicamente Revisiones de Cochrane
        cochrane_query = f'({query}) AND "Cochrane Database Syst Rev"[Journal]'

        pmids = await self._search_pmids(cochrane_query, max_results)
        if not pmids:
            return []

        return await self._fetch_details(pmids)

    async def _search_pmids(self, query: str, max_results: int) -> List[str]:
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

    async def _fetch_details(self, pmid_list: List[str]) -> List[NormalizedDocument]:
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

            parsed_data = xmltodict.parse(response.text)
            articles = parsed_data.get("PubmedArticleSet", {}).get("PubmedArticle", [])
            if isinstance(articles, dict):
                articles = [articles]

            normalized_docs = []
            for art in articles:
                doc = self._parse_article(art)
                if doc:
                    normalized_docs.append(doc)

            return normalized_docs

    def _parse_article(self, article: dict) -> Optional[NormalizedDocument]:
        try:
            medline = article.get("MedlineCitation", {})
            article_data = medline.get("Article", {})

            # ID y DOI
            pmid = str(medline.get("PMID", {}).get("#text", medline.get("PMID", "")))
            
            # Intentar obtener el DOI
            doi = None
            article_ids = article.get("PubmedData", {}).get("ArticleIdList", {}).get("ArticleId", [])
            if isinstance(article_ids, dict):
                article_ids = [article_ids]
            for aid in article_ids:
                if isinstance(aid, dict) and aid.get("@IdType") == "doi":
                    doi = aid.get("#text")

            # Título
            title_raw = article_data.get("ArticleTitle", "Sin título")
            if isinstance(title_raw, dict):
                title = title_raw.get("#text", "Sin título")
            elif isinstance(title_raw, list):
                title = " ".join([item.get("#text", str(item)) if isinstance(item, dict) else str(item) for item in title_raw])
            else:
                title = str(title_raw)

            # Abstract
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

            # Fecha
            pub_date_data = article_data.get("Journal", {}).get("JournalIssue", {}).get("PubDate", {})
            year = pub_date_data.get("Year", "")
            month = pub_date_data.get("Month", "01")
            pub_date = f"{year}-{month}" if year else None

            url = f"https://www.cochranelibrary.com/cdsr/doi/{doi}/full" if doi else f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"

            return NormalizedDocument(
                source_id=doi if doi else pmid,
                source_type="cochrane",
                title=title,
                abstract=abstract if abstract else "Sin resumen disponible.",
                authors=authors,
                publication_date=pub_date,
                url=url,
                metadata={
                    "pubmed_id": pmid,
                    "type": "Systematic Review"
                }
            )
        except Exception as e:
            print(f"Error procesando revisión Cochrane: {e}")
            return None
