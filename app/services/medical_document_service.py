from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.medical_document import MedicalDocument
from app.schemas.medical import NormalizedDocument


class MedicalDocumentService:

    def __init__(self, db: Session):
        self.db = db

    def get_by_external_id(
        self,
        source_id: int,
        external_id: str
    ) -> Optional[MedicalDocument]:

        statement = select(MedicalDocument).where(
            MedicalDocument.source_id == source_id,
            MedicalDocument.external_id == external_id
        )

        return self.db.execute(statement).scalar_one_or_none()

    def save_document(
        self,
        document: NormalizedDocument,
        source_id: int,
        language: Optional[str] = None,
        document_type: Optional[str] = None,
    ) -> MedicalDocument:

        existing_document = self.get_by_external_id(
            source_id=source_id,
            external_id=document.source_id
        )

        if existing_document:

            existing_document.title = document.title
            existing_document.abstract = document.abstract
            existing_document.url = document.url
            existing_document.authors = document.authors
            existing_document.publication_date = document.publication_date

            if language is not None:
                existing_document.language = language

            if document_type is not None:
                existing_document.document_type = document_type

            self.db.flush()

            return existing_document

        medical_document = MedicalDocument(
            source_id=source_id,
            external_id=document.source_id,
            title=document.title,
            abstract=document.abstract,
            url=document.url,
            publication_date=document.publication_date,
            authors=document.authors,
            document_type=document_type,
            language=language,
        )

        self.db.add(medical_document)
        self.db.flush()

        return medical_document

    def save_documents(
        self,
        documents: List[NormalizedDocument],
        source_id: int,
        language: Optional[str] = None,
        document_type: Optional[str] = None,
    ) -> List[MedicalDocument]:

        saved_documents = []

        for document in documents:

            saved_document = self.save_document(
                document=document,
                source_id=source_id,
                language=language,
                document_type=document_type,
            )

            saved_documents.append(saved_document)

        self.db.commit()

        return saved_documents

    def get_by_id(
        self,
        document_id: int
    ) -> Optional[MedicalDocument]:

        statement = select(MedicalDocument).where(
            MedicalDocument.id == document_id
        )

        return self.db.execute(statement).scalar_one_or_none()

    def get_by_source(
        self,
        source_id: int,
        limit: int = 20
    ) -> List[MedicalDocument]:

        statement = (
            select(MedicalDocument)
            .where(MedicalDocument.source_id == source_id)
            .order_by(MedicalDocument.publication_date.desc())
            .limit(limit)
        )

        return list(
            self.db.execute(statement).scalars().all()
        )

    def search_by_title(
        self,
        query: str,
        limit: int = 20
    ) -> List[MedicalDocument]:

        statement = (
            select(MedicalDocument)
            .where(
                MedicalDocument.title.ilike(f"%{query}%")
            )
            .limit(limit)
        )

        return list(
            self.db.execute(statement).scalars().all()
        )