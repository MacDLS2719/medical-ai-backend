from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.medical_query import MedicalQuery


class MedicalQueryService:

    def __init__(self, db: Session):
        self.db = db

    # ---------------------------------------------------------
    # CREAR CONSULTA
    # ---------------------------------------------------------

    def create_query(
        self,
        user_id: int,
        query: str,
        query_type: str = "medical",
        status: str = "pending",
    ) -> MedicalQuery:

        medical_query = MedicalQuery(
            user_id=user_id,
            query=query,
            query_type=query_type,
            status=status,
        )

        self.db.add(medical_query)
        self.db.flush()

        return medical_query

    # ---------------------------------------------------------
    # OBTENER CONSULTA POR ID
    # ---------------------------------------------------------

    def get_by_id(
        self,
        query_id: int
    ) -> Optional[MedicalQuery]:

        statement = select(MedicalQuery).where(
            MedicalQuery.id == query_id
        )

        return self.db.execute(statement).scalar_one_or_none()

    # ---------------------------------------------------------
    # OBTENER CONSULTAS DE UN USUARIO
    # ---------------------------------------------------------

    def get_by_user(
        self,
        user_id: int,
        limit: int = 20
    ) -> List[MedicalQuery]:

        statement = (
            select(MedicalQuery)
            .where(
                MedicalQuery.user_id == user_id
            )
            .order_by(
                MedicalQuery.created_at.desc()
            )
            .limit(limit)
        )

        return list(
            self.db.execute(statement).scalars().all()
        )

    # ---------------------------------------------------------
    # ACTUALIZAR ESTADO
    # ---------------------------------------------------------

    def update_status(
        self,
        query_id: int,
        status: str
    ) -> Optional[MedicalQuery]:

        medical_query = self.get_by_id(query_id)

        if not medical_query:
            return None

        medical_query.status = status

        self.db.flush()

        return medical_query

    # ---------------------------------------------------------
    # ACTUALIZAR CONSULTA
    # ---------------------------------------------------------

    def update_query(
        self,
        query_id: int,
        query: Optional[str] = None,
        query_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Optional[MedicalQuery]:

        medical_query = self.get_by_id(query_id)

        if not medical_query:
            return None

        if query is not None:
            medical_query.query = query

        if query_type is not None:
            medical_query.query_type = query_type

        if status is not None:
            medical_query.status = status

        self.db.flush()

        return medical_query

    # ---------------------------------------------------------
    # GUARDAR CAMBIOS
    # ---------------------------------------------------------

    def commit(self) -> None:
        self.db.commit()

    # ---------------------------------------------------------
    # ELIMINAR CONSULTA
    # ---------------------------------------------------------

    def delete_query(
        self,
        query_id: int
    ) -> bool:

        medical_query = self.get_by_id(query_id)

        if not medical_query:
            return False

        self.db.delete(medical_query)
        self.db.flush()

        return True