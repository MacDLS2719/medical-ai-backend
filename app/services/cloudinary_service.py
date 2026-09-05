import cloudinary
import cloudinary.uploader
import logging
from fastapi import UploadFile, HTTPException
from app.core.config import settings

logger = logging.getLogger(__name__)

# Inicializamos la configuración de Cloudinary desde la clase Settings
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True
)

class CloudinaryService:
    @staticmethod
    async def upload_file(file: UploadFile, folder: str = "medical_app", resource_type: str = "auto") -> str:
        """
        Sube un archivo a Cloudinary y retorna la URL pública.
        """
        details = await CloudinaryService.upload_file_with_details(file, folder=folder, resource_type=resource_type)
        return details.get("secure_url")

    @staticmethod
    async def upload_file_with_details(file: UploadFile, folder: str = "medical_app", resource_type: str = "auto") -> dict:
        """
        Sube un archivo a Cloudinary y retorna un diccionario con metadata completa.
        """
        try:
            await file.seek(0)
            result = cloudinary.uploader.upload(
                file.file,
                folder=folder,
                resource_type=resource_type
            )
            return {
                "public_id": result.get("public_id"),
                "file_url": result.get("secure_url"),
                "secure_url": result.get("secure_url"),
                "file_name": file.filename or "file",
                "mime_type": file.content_type or "application/octet-stream",
                "file_size": result.get("bytes", 0),
                "resource_type": result.get("resource_type", resource_type),
            }
        except Exception as e:
            logger.warning(f"Error inicial al subir a Cloudinary (resource_type={resource_type}): {str(e)}")
            # Fallback automático a 'video' si 'auto' falló para un archivo de audio/video
            if resource_type != "video" and (
                (file.content_type and ("audio" in file.content_type or "video" in file.content_type)) or
                (file.filename and any(file.filename.lower().endswith(ext) for ext in [".webm", ".mp4", ".m4a", ".ogg", ".wav", ".mp3", ".aac"]))
            ):
                try:
                    await file.seek(0)
                    result = cloudinary.uploader.upload(
                        file.file,
                        folder=folder,
                        resource_type="video"
                    )
                    return {
                        "public_id": result.get("public_id"),
                        "file_url": result.get("secure_url"),
                        "secure_url": result.get("secure_url"),
                        "file_name": file.filename or "file",
                        "mime_type": file.content_type or "audio/webm",
                        "file_size": result.get("bytes", 0),
                        "resource_type": result.get("resource_type", "video"),
                    }
                except Exception as inner_e:
                    logger.error(f"Error en fallback Cloudinary con resource_type=video: {str(inner_e)}", exc_info=True)
                    raise HTTPException(
                        status_code=500,
                        detail=f"Error al subir el archivo de audio/video a Cloudinary: {str(inner_e)}"
                    )
            
            logger.error(f"Error al subir el archivo a Cloudinary: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500, 
                detail=f"Error al subir el archivo a Cloudinary: {str(e)}"
            )

    @staticmethod
    def extract_public_id(file_url: str) -> str:
        """
        Extrae el public_id de Cloudinary desde una URL pública.
        """
        if not file_url:
            return ""
        if not file_url.startswith("http://") and not file_url.startswith("https://"):
            return file_url
        try:
            if "/upload/" in file_url:
                path_after_upload = file_url.split("/upload/")[1]
                parts = path_after_upload.split("/")
                if parts[0].startswith("v") and parts[0][1:].isdigit():
                    parts = parts[1:]
                full_path = "/".join(parts)
                public_id = full_path.rsplit(".", 1)[0]
                return public_id
        except Exception:
            pass
        return file_url

    @staticmethod
    def delete_file(public_id_or_url: str, resource_type: str = "image") -> bool:
        """
        Elimina un archivo de Cloudinary usando su public_id o URL.
        """
        try:
            public_id = CloudinaryService.extract_public_id(public_id_or_url)
            result = cloudinary.uploader.destroy(public_id, resource_type=resource_type)
            if result.get("result") != "ok" and resource_type == "image":
                result = cloudinary.uploader.destroy(public_id, resource_type="video")
            return result.get("result") == "ok"
        except Exception as e:
            logger.error(f"Error al eliminar el archivo de Cloudinary: {str(e)}")
            return False

cloudinary_service = CloudinaryService()