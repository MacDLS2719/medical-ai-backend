"""
alter_phi_columns_to_text.py
Convierte las columnas PHI de VARCHAR a TEXT para alojar el ciphertext AES-256-GCM.
Ejecutar UNA VEZ antes de migrate_encrypt_doctors.py.
"""
import os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

env_path = Path(__file__).parent / ".env"
if env_path.exists():
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

DATABASE_URL = os.environ.get("DATABASE_URL", "")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

from sqlalchemy import create_engine, text

engine = create_engine(DATABASE_URL)

ALTER_STATEMENTS = [
    "ALTER TABLE doctors ALTER COLUMN first_name TYPE TEXT",
    "ALTER TABLE doctors ALTER COLUMN last_name TYPE TEXT",
    "ALTER TABLE doctors ALTER COLUMN phone TYPE TEXT",
    "ALTER TABLE doctors ALTER COLUMN medical_license TYPE TEXT",
    "ALTER TABLE doctors ALTER COLUMN identity_document_url TYPE TEXT",
    "ALTER TABLE doctors ALTER COLUMN professional_registration_number TYPE TEXT",
    "ALTER TABLE doctors ALTER COLUMN professional_college TYPE TEXT",
    "ALTER TABLE doctors ALTER COLUMN professional_registration_certificate_url TYPE TEXT",
    "ALTER TABLE doctors ALTER COLUMN address TYPE TEXT",
    "ALTER TABLE doctors ALTER COLUMN consultation_phone TYPE TEXT",
    "ALTER TABLE doctor_educations ALTER COLUMN institution TYPE TEXT",
    "ALTER TABLE doctor_educations ALTER COLUMN degree TYPE TEXT",
    "ALTER TABLE doctor_educations ALTER COLUMN field_of_study TYPE TEXT",
    "ALTER TABLE doctor_media ALTER COLUMN file_url TYPE TEXT",
    "ALTER TABLE doctor_media ALTER COLUMN file_name TYPE TEXT",
]

with engine.connect() as conn:
    for stmt in ALTER_STATEMENTS:
        try:
            conn.execute(text(stmt))
            print(f"OK  : {stmt}")
        except Exception as e:
            print(f"SKIP: {stmt} -> {e}")
    conn.commit()

print("\nALTER TABLE completados. Ahora ejecuta: python migrate_encrypt_doctors.py")
