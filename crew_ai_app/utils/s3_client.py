"""
S3 client for uploading and managing dispute documents.
"""

import boto3
import logging
from typing import List, Dict, Any, Optional
from botocore.exceptions import ClientError, NoCredentialsError
from datetime import datetime, timedelta
import os
import uuid

logger = logging.getLogger(__name__)


class S3Client:
    """Client for managing document uploads to S3."""

    def __init__(self, region: str = "us-east-1", bucket_name: str = None):
        """Initialize S3 client.

        Args:
            region: AWS region for S3 access
            bucket_name: S3 bucket name (if None, will try to get from environment)
        """
        self.region = region
        self.bucket_name = bucket_name or os.getenv('S3_BUCKET_NAME')

        if not self.bucket_name:
            raise ValueError("Bucket name must be provided either as parameter or S3_BUCKET_NAME environment variable")

        try:
            self.s3_client = boto3.client('s3', region_name=region)
            logger.info(f"S3 client initialized for region: {region}, bucket: {self.bucket_name}")
        except NoCredentialsError:
            logger.error("AWS credentials not configured")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            raise
    
    
    def upload_document(
        self,
        file_content: bytes,
        filename: str,
        case_id: str,
        content_type: str = "application/octet-stream"
    ) -> Dict[str, Any]:
        """Upload a document to S3 for a specific case.
        
        Args:
            file_content: Binary content of the file
            filename: Original filename
            case_id: Case ID for organizing documents
            content_type: MIME type of the file
            
        Returns:
            Dict with success status, S3 key, and URL
        """
        try:
            # Generate unique filename to prevent collisions
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            file_extension = os.path.splitext(filename)[1]
            
            # S3 key structure: cases/{case_id}/documents/{timestamp}_{unique_id}_{filename}
            s3_key = f"cases/{case_id}/documents/{timestamp}_{unique_id}_{filename}"
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_content,
                ContentType=content_type,
                Metadata={
                    'case_id': case_id,
                    'original_filename': filename,
                    'upload_timestamp': timestamp
                }
            )
            
            # Generate S3 URL
            s3_url = f"s3://{self.bucket_name}/{s3_key}"
            
            logger.info(f"Document uploaded successfully: {s3_key}")
            
            return {
                'success': True,
                'key': s3_key,
                'url': s3_url,
                'bucket': self.bucket_name,
                'original_filename': filename
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"S3 upload failed with error {error_code}: {e}")
            return {
                'success': False,
                'error': f"S3 upload failed: {error_code}"
            }
        except Exception as e:
            logger.error(f"Document upload failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

    def generate_presigned_url(
        self,
        s3_key: str,
        expiration: int = 3600
    ) -> Optional[str]:
        """Generate a presigned URL for downloading a document.
        
        Args:
            s3_key: S3 object key
            expiration: URL expiration time in seconds (default 1 hour)
            
        Returns:
            Presigned URL or None if failed
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key
                },
                ExpiresIn=expiration
            )
            
            logger.info(f"Generated presigned URL for {s3_key}")
            return url
            
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            return None
        except Exception as e:
            logger.error(f"Error generating presigned URL: {e}")
            return None

    def list_case_documents(self, case_id: str) -> List[Dict[str, Any]]:
        """List all documents for a specific case.
        
        Args:
            case_id: Case ID to retrieve documents for
            
        Returns:
            List of document metadata
        """
        try:
            prefix = f"cases/{case_id}/documents/"
            
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            documents = []
            for obj in response.get('Contents', []):
                # Get object metadata
                metadata_response = self.s3_client.head_object(
                    Bucket=self.bucket_name,
                    Key=obj['Key']
                )
                
                documents.append({
                    'key': obj['Key'],
                    'url': f"s3://{self.bucket_name}/{obj['Key']}",
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat(),
                    'original_filename': metadata_response.get('Metadata', {}).get('original_filename', 'Unknown'),
                    'upload_timestamp': metadata_response.get('Metadata', {}).get('upload_timestamp', 'Unknown')
                })
            
            logger.info(f"Found {len(documents)} documents for case {case_id}")
            return documents
            
        except ClientError as e:
            logger.error(f"Failed to list case documents: {e}")
            return []
        except Exception as e:
            logger.error(f"Error listing case documents: {e}")
            return []

    def delete_document(self, s3_key: str) -> bool:
        """Delete a document from S3.
        
        Args:
            s3_key: S3 object key to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            logger.info(f"Document deleted: {s3_key}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to delete document: {e}")
            return False
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            return False
