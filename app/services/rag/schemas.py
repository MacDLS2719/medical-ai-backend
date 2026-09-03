from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class NormalizedDocument(BaseModel):
    source_id: str          # Ej: "34567890" (PMID)
    source_type: str        # "pubmed"
    title: str
    abstract: str
    authors: List[str] = []
    publication_date: Optional[str] = None
    url: str
    metadata: dict = {}     # Journal, MeSH terms, etc.


class MedicalSearchRequest(BaseModel):
    query: str = ""
    max_results: int = 10
    user_id: int
    # Biblioteca seleccionada desde el frontend.
    # Valores: 'all' | 'pubmed' | 'cochrane' | 'europepmc' |
    #          'openfda' | 'whoictrp' | 'clinicaltrials'
    source: Optional[str] = None


class SourceResults(BaseModel):
    count: int
    results: List[NormalizedDocument]


class MedicalSearchResponse(BaseModel):
    query: str
    search_query: str
    target_lang: str
    total_results: int
    sources: Dict[str, SourceResults]
    results: List[NormalizedDocument]
