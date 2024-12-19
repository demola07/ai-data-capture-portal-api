from fastapi import FastAPI, HTTPException, UploadFile, File, APIRouter, Depends, status
from pydantic import BaseModel
import boto3
from botocore.exceptions import NoCredentialsError
import uuid
from typing import List
from ..config import settings
from .. import schemas, oauth2

router = APIRouter(
    prefix="/uploads",
    tags=['Uploads']
)

s3_client = boto3.client(
    "s3",
    aws_access_key_id=settings.AWS_ACCESS_KEY,
    aws_secret_access_key=settings.AWS_SECRET_KEY,
    region_name=settings.AWS_REGION,
)

@router.post("/generate-presigned-urls", response_model=schemas.PresignedURLResponse)
def generate_presigned_urls(files: List[UploadFile], current_user: schemas.UserCreate = Depends(oauth2.get_current_user)):
     
    if current_user.role not in ("admin", "super-admin", "user"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this resource"
        )
     
    """
    Generate presigned URLs for uploading multiple files to S3.
    """

    upload_urls = []
    try:
        for file in files:
            unique_file_name = f"{uuid.uuid4()}-{file.filename}"
            presigned_url = s3_client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": settings.S3_BUCKET,
                    "Key": unique_file_name,
                    "ContentType": file.content_type,
                },
                ExpiresIn=3600,  # URL expires in 1 hour
            )
            upload_urls.append({"file_key": unique_file_name, "upload_url": presigned_url})

        return {"upload_urls": upload_urls}

    except NoCredentialsError:
        raise HTTPException(status_code=500, detail="AWS credentials not found.")