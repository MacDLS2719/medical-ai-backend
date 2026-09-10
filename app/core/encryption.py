"""
encryption.py — Cifrado AES-256-GCM para campos PHI/ePHI (HIPAA + GDPR)

Estándar aplicado:
  - Algoritmo  : AES-256-GCM (authenticated encryption)
  - Clave      : 256 bits (32 bytes) derivada de PHI_ENCRYPTION_KEY (base64 en .env)
  - Nonce/IV   : 12 bytes aleatorios por operación (GCM estándar)
  - Tag        : 16 bytes de autenticación (detecta manipulación)
  - Formato BD : base64url( nonce[12] || ciphertext || tag[16] ) como Text

Uso en modelos SQLAlchemy:
    from app.core.encryption import EncryptedString, EncryptedText

    class Doctor(Base):
        first_name: Mapped[str] = mapped_column(EncryptedString(100))
        description: Mapped[str | None] = mapped_column(EncryptedText())
"""

import base64
import os
import logging
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import Text
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Clave maestra de cifrado
# ---------------------------------------------------------------------------

def _load_encryption_key() -> bytes:
    """
    Carga la clave AES-256 desde la variable de entorno PHI_ENCRYPTION_KEY.
    La clave debe estar codificada en base64 y representar exactamente 32 bytes.

    Para generar una clave valida (ejecutalo UNA vez y guarda el resultado en .env):
        python -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"
    """
    raw = os.environ.get("PHI_ENCRYPTION_KEY", "")
    if not raw:
        raise RuntimeError(
            "[HIPAA/GDPR] La variable de entorno PHI_ENCRYPTION_KEY no esta configurada. "
            "Genera una clave con: "
            "python -c \"import os, base64; print(base64.b64encode(os.urandom(32)).decode())\""
        )
    try:
        key_bytes = base64.b64decode(raw)
    except Exception as exc:
        raise RuntimeError(
            "[HIPAA/GDPR] PHI_ENCRYPTION_KEY no es un valor base64 valido."
        ) from exc

    if len(key_bytes) != 32:
        raise RuntimeError(
            f"[HIPAA/GDPR] PHI_ENCRYPTION_KEY debe representar exactamente 32 bytes "
            f"(AES-256), pero tiene {len(key_bytes)} bytes."
        )
    return key_bytes


def _get_aesgcm() -> AESGCM:
    """Retorna una instancia AESGCM cargada con la clave maestra."""
    return AESGCM(_load_encryption_key())


# ---------------------------------------------------------------------------
# Funciones de cifrado / descifrado
# ---------------------------------------------------------------------------

NONCE_SIZE = 12   # bytes — estandar GCM
TAG_SIZE   = 16   # bytes — autenticacion GCM (incluido automaticamente por cryptography)


def encrypt_value(plaintext: str) -> str:
    """
    Cifra un string con AES-256-GCM.

    Retorna:
        str — base64url(nonce[12] || ciphertext || tag[16])
    """
    aesgcm = _get_aesgcm()
    nonce = os.urandom(NONCE_SIZE)
    # encrypt() de AESGCM incluye el tag de autenticacion al final del ciphertext
    ciphertext_with_tag = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    payload = nonce + ciphertext_with_tag
    return base64.urlsafe_b64encode(payload).decode("ascii")


def decrypt_value(encrypted_b64: str) -> str:
    """
    Descifra un valor cifrado con encrypt_value().

    Lanza:
        cryptography.exceptions.InvalidTag — si el ciphertext fue manipulado
        ValueError — si el formato es invalido
    """
    try:
        payload = base64.urlsafe_b64decode(encrypted_b64.encode("ascii") + b"==")
    except Exception as exc:
        raise ValueError(f"[Encryption] Formato base64 invalido: {exc}") from exc

    if len(payload) < NONCE_SIZE + TAG_SIZE:
        raise ValueError(
            f"[Encryption] Payload demasiado corto ({len(payload)} bytes). "
            "El valor puede no estar cifrado."
        )

    nonce = payload[:NONCE_SIZE]
    ciphertext_with_tag = payload[NONCE_SIZE:]

    aesgcm = _get_aesgcm()
    plaintext_bytes = aesgcm.decrypt(nonce, ciphertext_with_tag, None)
    return plaintext_bytes.decode("utf-8")


def is_encrypted(value: str) -> bool:
    """
    Heuristica para detectar si un valor ya esta cifrado (util en migracion).
    Un valor cifrado es base64url y tiene al menos NONCE_SIZE + TAG_SIZE bytes.
    """
    try:
        payload = base64.urlsafe_b64decode(value.encode("ascii") + b"==")
        return len(payload) >= NONCE_SIZE + TAG_SIZE
    except Exception:
        return False


# ---------------------------------------------------------------------------
# SQLAlchemy TypeDecorators
# ---------------------------------------------------------------------------

class EncryptedString(TypeDecorator):
    """
    TypeDecorator para campos String que deben cifrarse en reposo (HIPAA/GDPR PHI).

    Almacena el ciphertext como Text en la BD (el cifrado expande el tamano ~1.4x
    mas overhead del nonce y tag, por lo que String(N) no alcanza).

    Uso:
        first_name: Mapped[str] = mapped_column(EncryptedString(100))
    """
    impl = Text
    cache_ok = True

    def __init__(self, length: int | None = None, *args: Any, **kwargs: Any):
        # 'length' se ignora para el almacenamiento (siempre Text),
        # pero se mantiene por compatibilidad con definiciones de modelos.
        super().__init__(*args, **kwargs)
        self.length = length

    def process_bind_param(self, value: str | None, dialect: Dialect) -> str | None:
        """Cifra al escribir en la BD."""
        if value is None:
            return None
        if not isinstance(value, str):
            value = str(value)
        try:
            return encrypt_value(value)
        except Exception as exc:
            logger.error("[Encryption] Error al cifrar campo PHI: %s", exc)
            raise

    def process_result_value(self, value: str | None, dialect: Dialect) -> str | None:
        """Descifra al leer de la BD."""
        if value is None:
            return None
        try:
            return decrypt_value(value)
        except Exception as exc:
            # Si falla el descifrado (datos previos no cifrados o pre-migracion),
            # se loguea y se retorna el valor raw para no romper la app.
            logger.warning(
                "[Encryption] No se pudo descifrar valor — puede ser dato pre-migracion: %s",
                exc
            )
            return value


class EncryptedText(EncryptedString):
    """
    Alias semantico de EncryptedString para campos Text.

    Uso:
        description: Mapped[str | None] = mapped_column(EncryptedText())
    """
    pass
