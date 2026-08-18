import os
import sys
from logging.config import fileConfig

# Forzar la inclusión del directorio actual al inicio de sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

from app.core.config import settings
from app.core.database import Base

# Importar todos los modelos
from app.models.user import User
from app.models.doctor import Doctor
from app.models.patient import Patient

from app.models.specialty import Specialty
from app.models.doctor_specialty import DoctorSpecialty

from app.models.pathology import Pathology
from app.models.patient_pathology import PatientPathology

from app.models.medical_source import MedicalSource
from app.models.medical_document import MedicalDocument
from app.models.medical_query import MedicalQuery
from app.models.medical_query_pathology import MedicalQueryPathology
from app.models.medical_query_source import MedicalQuerySource
from app.models.medical_response import MedicalResponse


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


target_metadata = Base.metadata


# Usamos sync_database_url para asegurar el prefijo postgresql://
config.set_main_option(
    "sqlalchemy.url",
    settings.sync_database_url.replace("%", "%%")
)


def run_migrations_offline() -> None:

    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:

    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = settings.sync_database_url.replace("%", "%%")

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()