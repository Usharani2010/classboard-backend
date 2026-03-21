"""
Cloudinary Service for Media Uploads
Handles image and document uploads for announcements and assignments
"""
from typing import Optional
from app.config import settings


class CloudinaryService:
    """Service for uploading files to Cloudinary"""
    
    @staticmethod
    async def upload_file(
        file_path: str, 
        file_type: str,  # "image" or "document"
        resource_type: str = "auto"
    ) -> Optional[dict]:
        """
        Upload file to Cloudinary
        
        Returns:
            dict with keys: url, public_id, media_type
            or None if upload failed
        """
        if not settings.CLOUDINARY_CLOUD_NAME:
            return None
        
        try:
            import cloudinary
            import cloudinary.uploader
            
            cloudinary.config(
                cloud_name=settings.CLOUDINARY_CLOUD_NAME,
                api_key=settings.CLOUDINARY_API_KEY,
                api_secret=settings.CLOUDINARY_API_SECRET,
            )
            
            result = cloudinary.uploader.upload_large(
                file_path,
                resource_type=resource_type,
                folder="classboard",
            )
            
            return {
                "url": result.get("secure_url"),
                "public_id": result.get("public_id"),
                "media_type": file_type,
            }
        except Exception as e:
            print(f"Error uploading to Cloudinary: {str(e)}")
            return None
    
    @staticmethod
    async def delete_file(public_id: str) -> bool:
        """Delete file from Cloudinary"""
        if not settings.CLOUDINARY_CLOUD_NAME:
            return False
        
        try:
            import cloudinary
            import cloudinary.uploader
            
            cloudinary.config(
                cloud_name=settings.CLOUDINARY_CLOUD_NAME,
                api_key=settings.CLOUDINARY_API_KEY,
                api_secret=settings.CLOUDINARY_API_SECRET,
            )
            
            result = cloudinary.uploader.destroy(public_id)
            return result.get("result") == "ok"
        except Exception as e:
            print(f"Error deleting from Cloudinary: {str(e)}")
            return False
