import httpx
from typing import List, Optional
from app.schemas.medical import NormalizedDocument

class EuropePMCService:
    BASE_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

    def __init__(self):
        self.api_key = ""  # Europe PMC no requiere API key para uso básico

    async def search_and_fetch(self, query: str, max_results: int = 5) -> List[NormalizedDocument]:
        """
        Busca artículos en Europe PMC y retorna documentos normalizados.
        Europe PMC es un servicio de la European Bioinformatics Institute
        que proporciona acceso a literatura biomédica y de ciencias de la vida.
        """
        params = {
            "query": query,
            "resultType": "core",
            "format": "json",
            "pageSize": max_results,
            "cursor": "*"  # Para obtener resultados desde el inicio
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.BASE_URL, params=params)
                response.raise_for_status()
                data = response.json()

                result_list = data.get("resultList", {}).get("result", [])
                
                # Manejo robusto si result_list no es una lista
                if not isinstance(result_list, list):
                    print(f"Europe PMC devolvió formato inesperado: {type(result_list)}")
                    result_list = []

                normalized_docs = []

                for item in result_list:
                    if isinstance(item, dict):
                        doc = self._parse_article(item)
                        if doc:
                            normalized_docs.append(doc)

                print(f"Europe PMC: {len(normalized_docs)} documentos normalizados de {len(result_list)} resultados")
                return normalized_docs

        except Exception as e:
            print(f"Error en Europe PMC search: {e}")
            return []

    def _parse_article(self, item: dict) -> Optional[NormalizedDocument]:
        """Procesa un artículo de Europe PMC al formato normalizado."""
        try:
            # ID del artículo (PMCID o PMID)
            pmcid = item.get("pmcid", "") if item else ""
            pmid = item.get("pmid", "") if item else ""
            source_id = pmcid if pmcid else pmid

            if not source_id:
                return None

            # Título - normalizar
            title = item.get("title", "") if item else ""
            if not title or not isinstance(title, str):
                title = "Sin título"
            else:
                title = title.strip() if title.strip() else "Sin título"

            # Abstract - normalizar
            abstract_raw = item.get("abstractText", "") if item else ""
            if not abstract_raw or not isinstance(abstract_raw, str):
                abstract = "Sin resumen disponible."
            else:
                abstract = abstract_raw.strip() if abstract_raw.strip() else "Sin resumen disponible."

            # Autores - normalizar
            authors = []
            author_list = item.get("authorList", {}).get("author", []) if item else []
            
            if not isinstance(author_list, list):
                author_list = []

            for auth in author_list:
                if isinstance(auth, dict):
                    full_name = auth.get("fullName", "")
                    if full_name and isinstance(full_name, str):
                        authors.append(full_name.strip())
                elif isinstance(auth, str):
                    authors.append(auth.strip())

            # Si no hay autores, poner un valor por defecto
            if not authors:
                authors = ["Autores no especificados"]

            # Fecha de publicación - normalizar
            pub_date = None
            pub_date_str = item.get("firstPublicationDate", "") if item else ""
            
            if pub_date_str and isinstance(pub_date_str, str):
                try:
                    # Formato esperado: YYYY-MM-DD o YYYY-MM
                    cleaned_date = pub_date_str.strip()
                    if len(cleaned_date) >= 4:
                        pub_date = cleaned_date[:7]  # YYYY-MM
                except:
                    pub_date = None

            # Revista/Fuente - normalizar
            journal_title = item.get("journalTitle", "") if item else ""
            if not journal_title or not isinstance(journal_title, str):
                journal_title = ""
            else:
                journal_title = journal_title.strip()

            publisher = item.get("publisher", "") if item else ""
            if not publisher or not isinstance(publisher, str):
                publisher = ""
            else:
                publisher = publisher.strip()

            # URL - normalizar
            url = f"https://europepmc.org/article/{source_id}" if source_id else ""

            return NormalizedDocument(
                source_id=source_id,
                source_type="europe_pmc",
                title=title,
                abstract=abstract,
                authors=authors,
                publication_date=pub_date,
                url=url,
                metadata={
                    "journal": journal_title,
                    "publisher": publisher,
                    "pmcid": pmcid,
                    "pmid": pmid
                }
            )
        except Exception as e:
            print(f"Error procesando artículo Europe PMC: {e}")
            return None