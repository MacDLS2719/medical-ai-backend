from typing import Optional, List

from sqlalchemy.orm import Session

from app.models.medical_response import MedicalResponse


class MedicalResponseService:

    def __init__(self, db: Session):
        self.db = db

    def create_response(
        self,
        query_id: int,
        response: str,
        model: Optional[str] = None,
        tokens_used: Optional[int] = None,
        response_type: Optional[str] = None,
    ) -> MedicalResponse:
        """
        Guarda una respuesta generada para una consulta médica.
        """

        medical_response = MedicalResponse(
            query_id=query_id,
            response=response,
            model=model,
        )

        self.db.add(medical_response)
        self.db.commit()
        self.db.refresh(medical_response)

        return medical_response

    def get_by_query(
        self,
        query_id: int
    ) -> List[MedicalResponse]:
        """
        Obtiene todas las respuestas asociadas
        a una consulta médica.
        """

        return (
            self.db.query(MedicalResponse)
            .filter(
                MedicalResponse.query_id == query_id
            )
            .order_by(
                MedicalResponse.created_at.desc()
            )
            .all()
        )

    def get_by_id(
        self,
        response_id: int
    ) -> Optional[MedicalResponse]:
        """
        Obtiene una respuesta específica.
        """

        return (
            self.db.query(MedicalResponse)
            .filter(
                MedicalResponse.id == response_id
            )
            .first()
        )

    def delete(
        self,
        response_id: int
    ) -> bool:
        """
        Elimina una respuesta médica.
        """

        medical_response = self.get_by_id(response_id)

        if not medical_response:
            return False

        self.db.delete(medical_response)
        self.db.commit()

        return True
