import os
import uuid
from pathlib import Path

from fastapi import UploadFile


class AudioStorageService:
    """
    Servicio encargado de almacenar archivos de audio.

    Actualmente:
        - Almacenamiento local.

    Futuro:
        - AWS S3 u otro almacenamiento en la nube.

    La idea es que el resto de la aplicación no tenga
    que preocuparse por dónde está almacenado físicamente
    el archivo.
    """

    # ==========================================================
    # CONFIGURACIÓN
    # ==========================================================

    STORAGE_DISK = os.getenv(
        "AUDIO_STORAGE_DISK",
        "local"
    )

    STORAGE_ROOT = Path(
        os.getenv(
            "AUDIO_STORAGE_ROOT",
            "storage/medical-chat"
        )
    )

    # Extensiones permitidas
    ALLOWED_EXTENSIONS = {
        ".webm",
        ".mp3",
        ".wav",
        ".ogg",
        ".m4a",
        ".mp4",
    }

    # MIME types permitidos
    ALLOWED_MIME_TYPES = {
        "audio/webm",
        "audio/mpeg",
        "audio/mp3",
        "audio/wav",
        "audio/x-wav",
        "audio/ogg",
        "audio/mp4",
        "audio/x-m4a",
        "video/mp4",
    }

    # Máximo 10 MB
    MAX_FILE_SIZE = 10 * 1024 * 1024

    # ==========================================================
    # GUARDAR AUDIO
    # ==========================================================

    async def save_audio(
        self,
        audio: UploadFile,
        message_id: int,
    ) -> dict:

        # ------------------------------------------------------
        # Validar MIME type
        # ------------------------------------------------------

        if audio.content_type not in self.ALLOWED_MIME_TYPES:
            raise ValueError(
                f"Tipo de audio no permitido: "
                f"{audio.content_type}"
            )

        # ------------------------------------------------------
        # Obtener extensión
        # ------------------------------------------------------

        original_filename = audio.filename or "audio.webm"

        extension = Path(
            original_filename
        ).suffix.lower()

        if extension not in self.ALLOWED_EXTENSIONS:

            # Algunos navegadores pueden enviar WebM
            # sin una extensión confiable.
            if audio.content_type == "audio/webm":
                extension = ".webm"
            else:
                raise ValueError(
                    f"Extensión de archivo no permitida: "
                    f"{extension}"
                )

        # ------------------------------------------------------
        # Leer archivo
        # ------------------------------------------------------

        content = await audio.read()

        if not content:
            raise ValueError(
                "El archivo de audio está vacío."
            )

        # ------------------------------------------------------
        # Validar tamaño
        # ------------------------------------------------------

        file_size = len(content)

        if file_size > self.MAX_FILE_SIZE:
            raise ValueError(
                "El archivo de audio supera "
                "el límite máximo de 10 MB."
            )

        # ------------------------------------------------------
        # Generar nombre seguro
        # ------------------------------------------------------

        unique_name = (
            f"{uuid.uuid4().hex}"
            f"{extension}"
        )

        # ------------------------------------------------------
        # Crear directorio del mensaje
        # ------------------------------------------------------

        message_directory = (
            self.STORAGE_ROOT
            / str(message_id)
        )

        message_directory.mkdir(
            parents=True,
            exist_ok=True
        )

        # ------------------------------------------------------
        # Ruta física
        # ------------------------------------------------------

        file_path = (
            message_directory
            / unique_name
        )

        # ------------------------------------------------------
        # Guardar archivo
        # ------------------------------------------------------

        with open(
            file_path,
            "wb"
        ) as file:

            file.write(content)

        # ------------------------------------------------------
        # Ruta relativa
        # ------------------------------------------------------

        relative_path = (
            Path("medical-chat")
            / str(message_id)
            / unique_name
        )

        return {
            "file_name": original_filename,
            "file_path": str(
                relative_path
            ).replace("\\", "/"),
            "file_url": None,
            "mime_type": audio.content_type,
            "file_size": file_size,
            "storage_disk": self.STORAGE_DISK,
            "attachment_type": "audio",
        }

    # ==========================================================
    # ELIMINAR AUDIO
    # ==========================================================

    async def delete_audio(
        self,
        file_path: str,
    ) -> bool:

        try:

            # Convertimos la ruta relativa
            # a ruta física.

            relative_path = Path(file_path)

            # Esperamos:
            # medical-chat/message_id/file.webm

            parts = relative_path.parts

            if (
                len(parts) < 3
                or parts[0] != "medical-chat"
            ):
                return False

            physical_path = (
                self.STORAGE_ROOT.parent.parent
                / relative_path
            )

            if physical_path.exists():

                physical_path.unlink()

                return True

            return False

        except Exception as e:

            print(
                f"Error eliminando audio: {e}"
            )

            return False

    # ==========================================================
    # OBTENER RUTA FÍSICA
    # ==========================================================

    def get_local_path(
        self,
        file_path: str,
    ) -> Path:

        relative_path = Path(
            file_path
        )

        return (
            self.STORAGE_ROOT.parent.parent
            / relative_path
        )
