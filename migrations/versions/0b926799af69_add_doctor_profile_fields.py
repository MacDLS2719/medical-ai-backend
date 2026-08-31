"""add doctor profile fields

Revision ID: 0b926799af69
Revises: 2aa1bbbbda50
Create Date: 2026-08-31 10:11:52.422692

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0b926799af69"
down_revision: Union[str, Sequence[str], None] = "2aa1bbbbda50"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # ==========================================================
    # DATOS PERSONALES DEL DOCTOR
    # ==========================================================

    op.add_column(
        "doctors",
        sa.Column(
            "date_of_birth",
            sa.Date(),
            nullable=True
        )
    )

    op.add_column(
        "doctors",
        sa.Column(
            "residence_country",
            sa.String(length=100),
            nullable=True
        )
    )

    op.add_column(
        "doctors",
        sa.Column(
            "phone",
            sa.String(length=30),
            nullable=True
        )
    )

    # Documento de identidad del médico
    # Se almacena la referencia/URL del archivo,
    # no el archivo directamente en PostgreSQL.
    op.add_column(
        "doctors",
        sa.Column(
            "identity_document_url",
            sa.String(length=500),
            nullable=True
        )
    )

    # ==========================================================
    # INFORMACIÓN DE COLEGIACIÓN PROFESIONAL
    # ==========================================================

    op.add_column(
        "doctors",
        sa.Column(
            "professional_registration_number",
            sa.String(length=100),
            nullable=True
        )
    )

    op.add_column(
        "doctors",
        sa.Column(
            "professional_college",
            sa.String(length=255),
            nullable=True
        )
    )

    op.add_column(
        "doctors",
        sa.Column(
            "college_country",
            sa.String(length=100),
            nullable=True
        )
    )

    # Certificación de colegiación
    op.add_column(
        "doctors",
        sa.Column(
            "professional_registration_certificate_url",
            sa.String(length=500),
            nullable=True
        )
    )

    # ==========================================================
    # INFORMACIÓN PROFESIONAL
    # ==========================================================

    # Años de experiencia profesional
    op.add_column(
        "doctors",
        sa.Column(
            "years_of_experience",
            sa.Integer(),
            nullable=True
        )
    )

    # Descripción profesional que se mostrará en el perfil
    op.add_column(
        "doctors",
        sa.Column(
            "professional_description",
            sa.Text(),
            nullable=True
        )
    )

    # ==========================================================
    # UBICACIÓN
    # ==========================================================
    #
    # address
    # latitude
    # longitude
    #
    # YA EXISTEN desde la migración:
    #
    # 667482117c47
    #
    # Aquí solamente agregamos los nuevos campos.
    # ==========================================================

    op.add_column(
        "doctors",
        sa.Column(
            "country",
            sa.String(length=100),
            nullable=True
        )
    )

    op.add_column(
        "doctors",
        sa.Column(
            "city",
            sa.String(length=150),
            nullable=True
        )
    )

    op.add_column(
        "doctors",
        sa.Column(
            "postal_code",
            sa.String(length=20),
            nullable=True
        )
    )

    # ==========================================================
    # INFORMACIÓN DE CONSULTA
    # ==========================================================

    op.add_column(
        "doctors",
        sa.Column(
            "consultation_phone",
            sa.String(length=30),
            nullable=True
        )
    )

    op.add_column(
        "doctors",
        sa.Column(
            "website",
            sa.String(length=500),
            nullable=True
        )
    )

    # ==========================================================
    # ACEPTACIÓN DE POLÍTICA DE TRATAMIENTO DE DATOS
    # ==========================================================

    op.add_column(
        "doctors",
        sa.Column(
            "data_policy_accepted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false()
        )
    )

    op.add_column(
        "doctors",
        sa.Column(
            "data_policy_accepted_at",
            sa.DateTime(),
            nullable=True
        )
    )

    # ==========================================================
    # EDUCACIÓN DEL DOCTOR
    # ==========================================================
    #
    # Permite diferenciar:
    #
    # pregrado
    # especializacion
    # subespecializacion
    # maestria
    # doctorado
    # otro
    #
    # La especialidad principal NO se guarda aquí.
    # Se mantiene en doctor_specialties mediante is_primary.
    # ==========================================================

    op.add_column(
        "doctor_educations",
        sa.Column(
            "education_type",
            sa.String(length=50),
            nullable=True
        )
    )


def downgrade() -> None:

    # ==========================================================
    # EDUCACIÓN DEL DOCTOR
    # ==========================================================

    op.drop_column(
        "doctor_educations",
        "education_type"
    )

    # ==========================================================
    # POLÍTICA DE TRATAMIENTO DE DATOS
    # ==========================================================

    op.drop_column(
        "doctors",
        "data_policy_accepted_at"
    )

    op.drop_column(
        "doctors",
        "data_policy_accepted"
    )

    # ==========================================================
    # INFORMACIÓN DE CONSULTA
    # ==========================================================

    op.drop_column(
        "doctors",
        "website"
    )

    op.drop_column(
        "doctors",
        "consultation_phone"
    )

    # ==========================================================
    # UBICACIÓN
    # ==========================================================

    op.drop_column(
        "doctors",
        "postal_code"
    )

    op.drop_column(
        "doctors",
        "city"
    )

    op.drop_column(
        "doctors",
        "country"
    )

    # ==========================================================
    # INFORMACIÓN PROFESIONAL
    # ==========================================================

    op.drop_column(
        "doctors",
        "professional_description"
    )

    op.drop_column(
        "doctors",
        "years_of_experience"
    )

    # ==========================================================
    # COLEGIACIÓN PROFESIONAL
    # ==========================================================

    op.drop_column(
        "doctors",
        "professional_registration_certificate_url"
    )

    op.drop_column(
        "doctors",
        "college_country"
    )

    op.drop_column(
        "doctors",
        "professional_college"
    )

    op.drop_column(
        "doctors",
        "professional_registration_number"
    )

    # ==========================================================
    # DATOS PERSONALES
    # ==========================================================

    op.drop_column(
        "doctors",
        "identity_document_url"
    )

    op.drop_column(
        "doctors",
        "phone"
    )

    op.drop_column(
        "doctors",
        "residence_country"
    )

    op.drop_column(
        "doctors",
        "date_of_birth"
    )