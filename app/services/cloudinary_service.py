import cloudinary
import cloudinary.uploader
from fastapi import UploadFile, HTTPException
from app.core.config import settings

# Inicializamos la configuración de Cloudinary desde tu clase Settings
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True
)

class CloudinaryService:
    @staticmethod
    async def upload_file(file: UploadFile, folder: str = "medical_app") -> str:
        """
        Sube un archivo a Cloudinary y retorna la URL pública.
        """
        details = await CloudinaryService.upload_file_with_details(file, folder=folder)
        return details.get("secure_url")

    @staticmethod
    async def upload_file_with_details(file: UploadFile, folder: str = "medical_app") -> dict:
        """
        Sube un archivo a Cloudinary y retorna un diccionario con metadata completa.
        """
        try:
            # Subimos el archivo directamente desde los bytes de FastAPI
            result = cloudinary.uploader.upload(
                file.file,
                folder=folder,
                resource_type="auto"  # Detecta si es imagen, pdf, audio, etc.
            )
            return {
                "public_id": result.get("public_id"),
                "file_url": result.get("secure_url"),
                "secure_url": result.get("secure_url"),
                "file_name": file.filename or "file",
                "mime_type": file.content_type or "application/octet-stream",
                "file_size": result.get("bytes", 0),
                "resource_type": result.get("resource_type", "auto"),
            }
        except Exception as e:
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
    def delete_file(public_id_or_url: str) -> bool:
        """
        Elimina un archivo de Cloudinary usando su public_id o URL.
        """
        try:
            public_id = CloudinaryService.extract_public_id(public_id_or_url)
            result = cloudinary.uploader.destroy(public_id)
            return result.get("result") == "ok"
        except Exception as e:
            print(f"Error al eliminar el archivo de Cloudinary: {str(e)}")
            return False

cloudinary_service = CloudinaryService()