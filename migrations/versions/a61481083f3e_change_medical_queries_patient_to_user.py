"""change medical queries patient to user

Revision ID: a61481083f3e
Revises: 66dae21f88c0
Create Date: 2026-08-17
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# Revision identifiers
revision: str = "a61481083f3e"
down_revision: Union[str, Sequence[str], None] = "66dae21f88c0"
branch_labels = None
depends_on = None


def upgrade() -> None:

    # 1. Crear user_id temporalmente como nullable
    op.add_column(
        "medical_queries",
        sa.Column(
            "user_id",
            sa.Integer(),
            nullable=True
        )
    )

    # 2. Copiar el user_id desde patients
    #
    # PostgreSQL utiliza UPDATE ... FROM
    op.execute("""
        UPDATE medical_queries AS mq
        SET user_id = p.user_id
        FROM patients AS p
        WHERE p.id = mq.patient_id
    """)

    # 3. Crear la FK hacia users
    op.create_foreign_key(
        "fk_medical_queries_user_id",
        "medical_queries",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE"
    )

    # 4. Hacer user_id obligatorio
    op.alter_column(
        "medical_queries",
        "user_id",
        existing_type=sa.Integer(),
        nullable=False
    )

    # 5. Crear índice para user_id
    op.create_index(
        "ix_medical_queries_user_id",
        "medical_queries",
        ["user_id"],
        unique=False
    )

    # 6. Eliminar FK anterior hacia patients
    op.drop_constraint(
        "medical_queries_patient_id_fkey",
        "medical_queries",
        type_="foreignkey"
    )

    # 7. Eliminar índice anterior
    op.drop_index(
        "ix_medical_queries_patient_id",
        table_name="medical_queries"
    )

    # 8. Eliminar patient_id
    op.drop_column(
        "medical_queries",
        "patient_id"
    )


def downgrade() -> None:

    # 1. Crear nuevamente patient_id temporalmente como nullable
    op.add_column(
        "medical_queries",
        sa.Column(
            "patient_id",
            sa.Integer(),
            nullable=True
        )
    )

    # 2. Recuperar patient_id a partir del user_id
    #
    # PostgreSQL utiliza UPDATE ... FROM
    op.execute("""
        UPDATE medical_queries AS mq
        SET patient_id = p.id
        FROM patients AS p
        WHERE p.user_id = mq.user_id
    """)

    # 3. Crear FK hacia patients
    op.create_foreign_key(
        "fk_medical_queries_patient_id",
        "medical_queries",
        "patients",
        ["patient_id"],
        ["id"],
        ondelete="CASCADE"
    )

    # 4. Hacer patient_id obligatorio
    op.alter_column(
        "medical_queries",
        "patient_id",
        existing_type=sa.Integer(),
        nullable=False
    )

    # 5. Crear índice para patient_id
    op.create_index(
        "ix_medical_queries_patient_id",
        "medical_queries",
        ["patient_id"],
        unique=False
    )

    # 6. Eliminar FK hacia users
    op.drop_constraint(
        "fk_medical_queries_user_id",
        "medical_queries",
        type_="foreignkey"
    )

    # 7. Eliminar índice de user_id
    op.drop_index(
        "ix_medical_queries_user_id",
        table_name="medical_queries"
    )

    # 8. Eliminar user_id
    op.drop_column(
        "medical_queries",
        "user_id"
    )