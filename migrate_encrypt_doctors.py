"""
migrate_encrypt_doctors.py
==========================
Script de migracion ONE-SHOT para cifrar datos PHI existentes en la BD.

INSTRUCCIONES:
1. Asegurate de que PHI_ENCRYPTION_KEY esta en tu .env
2. Ejecuta este script UNA SOLA VEZ antes de arrancar el servidor con los nuevos modelos:

   cd backend
   .venv\\Scripts\\activate
   python migrate_encrypt_doctors.py

El script es IDEMPOTENTE: detecta valores ya cifrados y los omite de forma segura.
"""

import os
import sys
import base64
import logging
from pathlib import Path

# ---------------------------------------------------------------------------
# Setup de paths y entorno
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent))

# Cargar .env manualmente si no esta cargado
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("migrate_encrypt")

# ---------------------------------------------------------------------------
# Imports de la aplicacion (despues de cargar env)
# ---------------------------------------------------------------------------
from sqlalchemy import create_engine, text as sql_text
from sqlalchemy.orm import sessionmaker

from app.core.encryption import encrypt_value, is_encrypted

# ---------------------------------------------------------------------------
# Configuracion de BD (conexion directa sin ORM para evitar el TypeDecorator)
# ---------------------------------------------------------------------------
DATABASE_URL = os.environ.get("DATABASE_URL", "")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if not DATABASE_URL:
    logger.error("DATABASE_URL no configurada en .env")
    sys.exit(1)

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

# ---------------------------------------------------------------------------
# Campos a migrar por tabla
# ---------------------------------------------------------------------------
TABLES_FIELDS = {
    "doctors": [
        "first_name",
        "last_name",
        "phone",
        "medical_license",
        "identity_document_url",
        "professional_registration_number",
        "professional_college",
        "professional_registration_certificate_url",
        "address",
        "consultation_phone",
        "professional_description",
    ],
    "doctor_educations": [
        "institution",
        "degree",
        "field_of_study",
        "description",
    ],
    "doctor_media": [
        "file_url",
        "file_name",
    ],
}


def migrate_table(session, table: str, fields: list[str]) -> dict:
    """
    Recorre todos los registros de 'table' y cifra los campos en 'fields'
    que todavia esten en texto plano.
    """
    stats = {"migrated": 0, "skipped_already_encrypted": 0, "skipped_null": 0, "errors": 0}

    rows = session.execute(sql_text(f"SELECT id FROM {table} ORDER BY id")).fetchall()
    logger.info("  Tabla %-25s -> %d registros", table, len(rows))

    for (row_id,) in rows:
        updates = {}
        row_data = session.execute(
            sql_text(f"SELECT {', '.join(fields)} FROM {table} WHERE id = :id"),
            {"id": row_id}
        ).fetchone()

        if row_data is None:
            continue

        for i, field in enumerate(fields):
            value = row_data[i]
            if value is None:
                stats["skipped_null"] += 1
                continue
            if is_encrypted(str(value)):
                stats["skipped_already_encrypted"] += 1
                continue
            try:
                updates[field] = encrypt_value(str(value))
                stats["migrated"] += 1
            except Exception as exc:
                logger.error("    ERROR cifrando %s.id=%d.%s: %s", table, row_id, field, exc)
                stats["errors"] += 1

        if updates:
            set_clause = ", ".join(f"{k} = :{k}" for k in updates)
            updates["id"] = row_id
            session.execute(
                sql_text(f"UPDATE {table} SET {set_clause} WHERE id = :id"),
                updates
            )

    session.commit()
    return stats


def main():
    logger.info("=" * 60)
    logger.info("MIGRACION DE CIFRADO PHI (AES-256-GCM)  HIPAA / GDPR")
    logger.info("=" * 60)

    # Verificar que la clave esta configurada
    phi_key = os.environ.get("PHI_ENCRYPTION_KEY", "")
    if not phi_key:
        logger.error(
            "PHI_ENCRYPTION_KEY no encontrada en entorno.\n"
            "Genera una clave con:\n"
            "  python -c \"import os,base64; print(base64.b64encode(os.urandom(32)).decode())\"\n"
            "y agregala al archivo .env"
        )
        sys.exit(1)

    try:
        key_bytes = base64.b64decode(phi_key)
        if len(key_bytes) != 32:
            raise ValueError(f"La clave tiene {len(key_bytes)} bytes, se requieren 32")
        logger.info("Clave AES-256 verificada correctamente (%d bytes)", len(key_bytes))
    except Exception as exc:
        logger.error("PHI_ENCRYPTION_KEY invalida: %s", exc)
        sys.exit(1)

    total_migrated = 0
    total_errors = 0

    for table, fields in TABLES_FIELDS.items():
        logger.info("")
        logger.info("Procesando tabla: %s", table)
        # Sesion independiente por tabla para evitar contaminacion de transacciones
        with Session() as session:
            try:
                stats = migrate_table(session, table, fields)
                logger.info(
                    "  Cifrados: %d | Ya cifrados: %d | Nulos omitidos: %d | Errores: %d",
                    stats["migrated"],
                    stats["skipped_already_encrypted"],
                    stats["skipped_null"],
                    stats["errors"],
                )
                total_migrated += stats["migrated"]
                total_errors += stats["errors"]
            except Exception as exc:
                session.rollback()
                logger.error("  ERROR CRITICO en tabla %s: %s", table, exc, exc_info=True)
                total_errors += 1


    logger.info("")
    logger.info("=" * 60)
    logger.info("MIGRACION COMPLETADA")
    logger.info("  Total cifrados  : %d campos", total_migrated)
    logger.info("  Total errores   : %d", total_errors)
    logger.info("=" * 60)

    if total_errors > 0:
        logger.warning("Hubo errores durante la migracion. Revisa los logs.")
        sys.exit(1)
    else:
        logger.info("Todos los datos PHI han sido cifrados correctamente.")


if __name__ == "__main__":
    main()
