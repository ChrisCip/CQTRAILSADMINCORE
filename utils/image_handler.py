# utils/image_handler.py
from typing import Dict, Optional, List
from fastapi import HTTPException

def validate_and_format_images(images: Optional[Dict[str, str]] = None) -> Optional[Dict[str, str]]:
    if images is None:
        return None
        
    # Validate maximum number of images
    if len(images) > 3:
        raise HTTPException(
            status_code=400,
            detail="Maximum 3 images allowed per vehicle"
        )
    
    # Validate image URLs
    valid_keys = ["image1", "image2", "image3"]
    formatted_images = {}
    
    for key, url in images.items():
        if key not in valid_keys:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid image key: {key}. Use image1, image2, or image3"
            )
        if not url.strip():
            raise HTTPException(
                status_code=400,
                detail="Image URL cannot be empty"
            )
        formatted_images[key] = url.strip()
    
    return formatted_images