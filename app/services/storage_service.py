import os
import shutil
from abc import ABC, abstractmethod
from fastapi import UploadFile
import uuid
from typing import Optional

class StorageService(ABC):
    @abstractmethod
    async def upload_file(self, file: UploadFile, directory_path: str) -> str:
        """
        Uploads a file to the storage service.
        Returns the file URL or path.
        """
        pass

    @abstractmethod
    def delete_file(self, file_url: str) -> bool:
        """
        Deletes a file from the storage service.
        """
        pass


class LocalStorageService(StorageService):
    def __init__(self, base_path: str = "archivos"):
        # Go up from app/services to backend folder
        current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.base_path = os.path.join(current_dir, base_path)
        
        # Ensure base directory exists
        if not os.path.exists(self.base_path):
            os.makedirs(self.base_path)

    async def upload_file(self, file: UploadFile, directory_path: str) -> str:
        """
        Uploads a file locally. directory_path could be like 'doctor_1'
        Returns the relative file URL path like '/archivos/doctor_1/filename.ext'
        """
        target_dir = os.path.join(self.base_path, directory_path)
        
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

        # Generate unique filename to avoid collisions
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        
        file_path = os.path.join(target_dir, unique_filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Return a relative URL path that can be served by FastAPI or frontend
        # e.g., /archivos/doctor_1/xxx.jpg
        return f"/archivos/{directory_path}/{unique_filename}"

    def delete_file(self, file_url: str) -> bool:
        """
        Deletes a local file.
        """
        if file_url.startswith("/archivos/"):
            # Extract relative path without leading slash
            rel_path = file_url[1:] 
            current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            full_path = os.path.join(current_dir, rel_path)
            
            if os.path.exists(full_path):
                try:
                    os.remove(full_path)
                    return True
                except Exception as e:
                    print(f"Error deleting file: {e}")
                    return False
        return False

# Dependency injection helper
def get_storage_service() -> StorageService:
    return LocalStorageService()
