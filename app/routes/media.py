import os
import tempfile

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.schemas.schemas import MediaUploadResponse
from app.services.cloudinary_service import CloudinaryService
from app.utils.dependencies import require_roles

router = APIRouter(prefix="/media", tags=["media"])

ALLOWED_CONTENT_TYPES = {
    "image/jpeg": "image",
    "image/png": "image",
    "image/webp": "image",
    "video/mp4": "video",
    "video/quicktime": "video",
    "application/pdf": "document",
    "application/msword": "document",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "document",
}


@router.post("/upload", response_model=MediaUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_media(
    file: UploadFile = File(...),
    current_user: dict = Depends(require_roles("student", "cr", "college_admin", "system_admin")),
):
    media_type = ALLOWED_CONTENT_TYPES.get(file.content_type)
    if not media_type:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    suffix = os.path.splitext(file.filename or "")[-1] or ".bin"
    temp_file_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(await file.read())
            temp_file_path = temp_file.name

        result = await CloudinaryService.upload_file(
            temp_file_path,
            file_type=media_type,
            resource_type="auto",
        )
        if not result or not result.get("url"):
            raise HTTPException(status_code=500, detail="Cloudinary upload failed")

        return MediaUploadResponse(
            url=result["url"],
            media_type=result["media_type"],
            public_id=result.get("public_id"),
        )
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
