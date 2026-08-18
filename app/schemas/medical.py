from pydantic import BaseModel
from typing import List, Optional

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

class MedicalSearchResponse(BaseModel):
    results: List[NormalizedDocument]