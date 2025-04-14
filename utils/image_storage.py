# utils/image_storage.py
import os
import shutil
from fastapi import UploadFile, HTTPException
from typing import Dict, Optional, List
import uuid

class ImageStorage:
    UPLOAD_DIR = "static/images/vehicles"
    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif"}
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

    def __init__(self):
        # Create upload directory if it doesn't exist
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)

    def _validate_file(self, file: UploadFile):
        # Check file extension
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in self.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed types: {', '.join(self.ALLOWED_EXTENSIONS)}"
            )

    async def save_images(self, files: List[UploadFile], vehiculo_id: int) -> Dict[str, str]:
        if len(files) > 3:
            raise HTTPException(status_code=400, detail="Maximum 3 images allowed")

        saved_images = {}
        for i, file in enumerate(files, 1):
            self._validate_file(file)
            
            # Generate unique filename
            file_ext = os.path.splitext(file.filename)[1].lower()
            filename = f"vehicle_{vehiculo_id}_{uuid.uuid4()}{file_ext}"
            filepath = os.path.join(self.UPLOAD_DIR, filename)

            # Save file
            try:
                with open(filepath, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                saved_images[f"image{i}"] = f"/static/images/vehicles/{filename}"
            finally:
                file.file.close()

        return saved_images

    def delete_images(self, image_urls: Dict[str, str]):
        for url in image_urls.values():
            if url:
                filepath = os.path.join("static", url.lstrip("/"))
                if os.path.exists(filepath):
                    os.remove(filepath)