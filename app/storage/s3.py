import boto3
from botocore.client import Config
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class S3Storage:
    def __init__(self):
        self.s3 = boto3.client(
            's3',
            endpoint_url=f"http://{settings.minio_endpoint}" if not settings.minio_endpoint.startswith('http') else settings.minio_endpoint,
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key,
            config=Config(signature_version='s3v4'),
            region_name='us-east-1' # MinIO usually doesn't care
        )
        self.bucket = settings.minio_bucket
        # self._ensure_bucket_exists()  # Removed from init to prevent startup failure

    def _ensure_bucket_exists(self):
        try:
            self.s3.head_bucket(Bucket=self.bucket)
        except Exception:
            logger.info(f"Bucket {self.bucket} does not exist. Creating it.")
            self.s3.create_bucket(Bucket=self.bucket)

    def upload_raw_log(self, file_name: str, content: str):
        try:
            self.s3.put_object(
                Bucket=self.bucket,
                Key=file_name,
                Body=content,
                ContentType='text/plain'
            )
            logger.info(f"Successfully uploaded {file_name} to {self.bucket}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload log to S3: {str(e)}")
            return False

storage = S3Storage()
