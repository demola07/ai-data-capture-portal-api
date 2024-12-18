from fastapi import FastAPI, HTTPException, UploadFile, File, APIRouter
from pydantic import BaseModel
import boto3
from botocore.exceptions import NoCredentialsError
import uuid
from typing import List
from ..config import settings
from .. import schemas

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
def generate_presigned_urls(files: List[schemas.FileInfo]):
    """
    Generate presigned URLs for uploading multiple files to S3.
    """
    upload_urls = []
    try:
        for file in files:
            unique_file_name = f"{uuid.uuid4()}-{file.file_name}"
            presigned_url = s3_client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": settings.S3_BUCKET,
                    "Key": unique_file_name,
                    "ContentType": file.file_type,
                },
                ExpiresIn=3600,  # URL expires in 1 hour
            )
            upload_urls.append({"file_key": unique_file_name, "upload_url": presigned_url})

        return {"upload_urls": upload_urls}

    except NoCredentialsError:
        raise HTTPException(status_code=500, detail="AWS credentials not found.")