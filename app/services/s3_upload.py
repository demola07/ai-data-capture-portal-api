"""
S3 file upload service for handling profile images and certificates.
"""
import boto3
from botocore.exceptions import ClientError
from fastapi import UploadFile, HTTPException, status
import uuid
import os
from typing import Optional, List
import logging

from app.config import settings

logger = logging.getLogger(__name__)

# Allowed file types
ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


class S3UploadService:
    """Service for uploading files to S3"""
    
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY,
            aws_secret_access_key=settings.AWS_SECRET_KEY,
            region_name=settings.AWS_REGION
        )
        self.bucket_name = settings.BUCKET_NAME
    
    def validate_image(self, file: UploadFile) -> None:
        """
        Validate image file type and size.
        
        Args:
            file: Uploaded file
            
        Raises:
            HTTPException: If file is invalid
        """
        # Check file type
        if file.content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type. Allowed types: PNG, JPEG. Got: {file.content_type}"
            )
        
        # Check file size
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset to beginning
        
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Max size: 5MB. Got: {file_size / 1024 / 1024:.2f}MB"
            )
    
    async def upload_file(
        self,
        file: UploadFile,
        folder: str = "counsellors"
    ) -> str:
        """
        Upload file to S3 and return the URL.
        
        Args:
            file: File to upload
            folder: S3 folder/prefix
            
        Returns:
            S3 URL of uploaded file
            
        Raises:
            HTTPException: If upload fails
        """
        try:
            # Validate file
            self.validate_image(file)
            
            # Generate unique filename
            file_extension = os.path.splitext(file.filename)[1]
            unique_filename = f"{folder}/{uuid.uuid4()}{file_extension}"
            
            # Read file content
            content = await file.read()
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=unique_filename,
                Body=content,
                ContentType=file.content_type
            )
            
            # Generate URL
            url = f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{unique_filename}"
            
            logger.info(f"File uploaded successfully: {url}")
            return url
            
        except ClientError as e:
            logger.error(f"S3 upload error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload file: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error during upload: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Upload failed: {str(e)}"
            )
    
    async def upload_multiple_files(
        self,
        files: List[UploadFile],
        folder: str = "counsellors/certificates"
    ) -> List[str]:
        """
        Upload multiple files to S3.
        
        Args:
            files: List of files to upload
            folder: S3 folder/prefix
            
        Returns:
            List of S3 URLs
        """
        urls = []
        for file in files:
            url = await self.upload_file(file, folder)
            urls.append(url)
        return urls
    
    def delete_file(self, url: str) -> None:
        """
        Delete file from S3.
        
        Args:
            url: S3 URL of file to delete
        """
        try:
            # Extract key from URL
            key = url.split(f"{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/")[1]
            
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )
            
            logger.info(f"File deleted successfully: {url}")
            
        except Exception as e:
            logger.error(f"Error deleting file: {str(e)}")
            # Don't raise exception, just log the error


# Singleton instance
s3_service = S3UploadService()
