import uuid
from fastapi import APIRouter, HTTPException, Query,Response, logger,status
from typing import Any, Dict,List,Tuple
from google.cloud import storage
from google.api_core.exceptions import GoogleAPIError,Conflict
import re
import logging
import io
import zipfile
from fastapi.responses import StreamingResponse
import os
from schemas.bucket import BucketMetadataResponse
from schemas.storage import FileResponse, FolderWithContentResponse
import logging
from .config import project,_GS_URI_RE
logger = logging.getLogger(__name__)


def parse_bucket_uri(bucket_uri: str) -> storage.Bucket:
    
    m = _GS_URI_RE.match(bucket_uri)
    if not m:
        raise ValueError(f"Invalid GCS URI: {bucket_uri!r}")
    bucket_name = m.group(1)
    client = storage.Client(project=project)
    return client.bucket(bucket_name)

def process_path(path: str) -> list:
    
    return [seg for seg in path.split("/") if seg]

def get_gcs_folder_path(folder_path: str) -> str:

    segments = process_path(folder_path)
    return "/".join(segments) if segments else ""

def upload_file_to_gcs(
    bucket_uri: str,
    folder_path: str,
    file_name: str,
    data: bytes,
    content_type: str = "application/octet-stream"
) -> bool:
    bucket = parse_bucket_uri(bucket_uri)
    
    
    normalized_folder = get_gcs_folder_path(folder_path)
    prefix = normalized_folder.rstrip("/") + "/" if normalized_folder else ""
    blob_name = f"{prefix}{file_name}"
    
    try:
        blob = bucket.blob(blob_name)
        blob.upload_from_string(data, content_type=content_type)
        logger.info(f"Uploaded file '{blob_name}' to bucket '{bucket_uri}'.")
        return True
    except GoogleAPIError as e:
        logger.exception("Failed to upload file to GCS.")
        raise

def create_bucket(tenant_id) -> str:
    if not tenant_id:
        raise RuntimeError("Environment variable TENANT_ID is not set")

    
    suffix = uuid.uuid4().hex[:8]
    bucket_name = f"{tenant_id}-{suffix}"

    
    client = storage.Client()
    bucket = client.create_bucket(bucket_name)  
    
    return f"gs://{bucket.name}"
   
def list_files_in_gcs(bucket_uri: str, folder_path: str) -> list:
    
    bucket = parse_bucket_uri(bucket_uri)
    
    # Normalize folder path
    normalized_folder = get_gcs_folder_path(folder_path)
    prefix = normalized_folder.rstrip("/") + "/" if normalized_folder else ""
    
    try:
        blobs = bucket.list_blobs(prefix=prefix)
        # Return a list of blob names
        return [blob.name for blob in blobs]
    except GoogleAPIError as e:
        logger.exception("Failed to list files in GCS.")
        raise

def create_folder_in_gcs(bucket_uri: str, folder_path: str) -> bool:
    
    bucket = parse_bucket_uri(bucket_uri)
    
    # Normalize folder path
    normalized_folder = get_gcs_folder_path(folder_path)
    folder_blob_name = normalized_folder.rstrip("/") + "/" if normalized_folder else "root/"
    
    try:
        blob = bucket.blob(folder_blob_name)
        # Upload an empty string to create the object
        blob.upload_from_string("", content_type="application/x-directory")
        logger.info(f"Created folder '{folder_blob_name}' in bucket.")
        return True
    except GoogleAPIError as e:
        logger.exception("Failed to create folder in GCS.")
        raise

def delete_folder_in_gcs(bucket_uri: str, folder_path: str) -> None:
    bucket = parse_bucket_uri(bucket_uri)
    prefix = folder_path.rstrip("/") + "/"
    
    # 1. Check for existence: try listing one blob under prefix
    blobs = list(bucket.list_blobs(prefix=prefix, max_results=1))
    placeholder = bucket.blob(prefix)
    
    if not blobs and not placeholder.exists():
        # No blob or placeholder => folder does not exist
        raise HTTPException(status_code=404, detail=f"Folder '{folder_path}' not found")
    
    # 2. Delete all blobs under that prefix
    for blob in bucket.list_blobs(prefix=prefix):
        blob.delete()

def ensure_bucket_exists(bucket_name: str) -> Tuple[storage.Bucket, bool]:
    
    client = storage.Client(project=project)
    bucket = client.bucket(bucket_name)
    
    if bucket.exists():
        return bucket, False
    
    try:
        new_bucket = client.create_bucket(bucket_name)
        logger.info(f"Created new bucket: {bucket_name}")
        return new_bucket, True
    except Conflict:
        # Handle race condition where bucket was created between check and create
        logger.info(f"Bucket {bucket_name} already exists (race condition)")
        return bucket, False
    except GoogleAPIError as e:
        logger.exception(f"Failed to create bucket '{bucket_name}': {e}")
        raise

def transfer_bucket_contents(source_bucket_name: str, dest_bucket_name: str) -> List[str]:
    
    client = storage.Client(project=project)
    source_bucket = client.bucket(source_bucket_name)
    
    # Check if source bucket exists
    if not source_bucket.exists():
        raise ValueError(f"Source bucket '{source_bucket_name}' does not exist")
    
    # Ensure destination bucket exists, create if needed
    dest_bucket, was_created = ensure_bucket_exists(dest_bucket_name)
    
    transferred_blobs = []
    
    try:
        # List all blobs in source bucket
        blobs = client.list_blobs(source_bucket_name)
        
        # Copy each blob to destination bucket with same name/path
        for blob in blobs:
            source_bucket.copy_blob(blob, dest_bucket, blob.name)
            transferred_blobs.append(blob.name)
            logger.info(f"Transferred: {blob.name}")
    except GoogleAPIError as e:
        # If we created the bucket and transfer failed, clean up by deleting it
        if was_created:
            try:
                dest_bucket.delete(force=True)
                logger.info(f"Cleaned up destination bucket after failed transfer: {dest_bucket_name}")
            except Exception as cleanup_error:
                logger.error(f"Failed to clean up destination bucket: {cleanup_error}")
        
        logger.exception(f"Error during bucket transfer: {e}")
        raise
    
    return transferred_blobs

def ensure_directory_in_zip(zip_file: zipfile.ZipFile, directory_path: str) -> None:
    
    if not directory_path:
        return
        
    # Remove trailing slash if present
    directory_path = directory_path.rstrip("/")
    if not directory_path:
        return
        
    directory_path += "/"
    
    # Check if directory already exists in the zip
    if directory_path in [info.filename for info in zip_file.filelist]:
        return
        
    # Add directory entry
    zip_file.writestr(directory_path, "")
    
    # Also ensure parent directories exist
    if "/" in directory_path[:-1]:
        parent_dir = "/".join(directory_path.split("/")[:-2]) + "/"
        ensure_directory_in_zip(zip_file, parent_dir)

def create_zip_from_bucket(bucket_name: str) -> io.BytesIO:
    
    client = storage.Client(project=project)
    bucket = client.bucket(bucket_name)
    
    # Check if bucket exists
    if not bucket.exists():
        raise ValueError(f"Bucket '{bucket_name}' does not exist")
    
    # Create an in-memory file-like object for the ZIP
    zip_buffer = io.BytesIO()
    
    try:
        # Create a ZIP file in the buffer
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # List all blobs in the bucket
            blobs = list(client.list_blobs(bucket_name))
            
            # First pass: create folder structure
            directories = set()
            for blob in blobs:
                # Extract all parent directories
                parts = blob.name.split('/')
                for i in range(1, len(parts)):
                    dir_path = '/'.join(parts[:i]) + '/'
                    directories.add(dir_path)
            
            # Add directory entries
            for directory in sorted(directories):
                zip_file.writestr(directory, "")
                logger.info(f"Added directory to ZIP: {directory}")
            
            # Second pass: add all files
            for blob in blobs:
                # Skip directory markers (empty blobs ending with /)
                if blob.name.endswith('/') and blob.size == 0:
                    continue
                    
                # Download blob content
                content = blob.download_as_bytes()
                
                # Add content to the ZIP with the same path structure
                zip_file.writestr(blob.name, content)
                logger.info(f"Added file to ZIP: {blob.name}")
    except GoogleAPIError as e:
        logger.exception(f"Error creating ZIP from bucket '{bucket_name}': {e}")
        raise
    
    # Seek to the beginning of the buffer
    zip_buffer.seek(0)
    return zip_buffer

def build_tree_from_blobs(
    tree: Dict[str, Any],
    prefix: str = ""
) -> FolderWithContentResponse:
    
    name = prefix.rstrip("/").split("/")[-1] if prefix else "root"
    folder_path = prefix.rstrip("/")

    # Build sub‑folders
    children: List[FolderWithContentResponse] = []
    for key in sorted(tree.keys()):
        val = tree[key]
        if isinstance(val, dict):
            # nested folder
            sub_prefix = f"{prefix}{key}/"
            children.append(build_tree_from_blobs(val, sub_prefix))

    # Build files
    files: List[FileResponse] = []
    for key, val in tree.items():
        if val is None:
            # this key is a file
            file_name = key
            file_type = file_name.rsplit(".", 1)[-1] if "." in file_name else ""
            files.append(FileResponse(
                name=file_name,
                path=f"{prefix}{file_name}",
                
                file_type=file_type,
                
            ))

    return FolderWithContentResponse(
        name=name,
        path=folder_path,
        children=children,
        files=files
    )

def sanitize_bucket_name(raw: str) -> str:
    
    name = raw.lower()
    
    name = re.sub(r'[^a-z0-9\-_.]', '-', name)
    
    name = re.sub(r'[-\.]{2,}', '-', name)
    
    name = name.strip('-._')
    
    if len(name) > 63:
        name = name[:63].rstrip('-.')
    
    if len(name) < 3:
        name += uuid.uuid4().hex[: (3 - len(name))]
    
    if name.startswith('goog'):
        name = 'b-' + name
    
    if re.fullmatch(r'\d+(\.\d+){3}', name):
        name = 'b-' + name
    return name

def generate_bucket_id() -> str:
    """Generate a unique bucket ID."""
    return str(uuid.uuid4())

def ensure_bucket_exists(bucket_id: str) -> Tuple[storage.Bucket, bool]:
    
    client = storage.Client()
    bucket = client.bucket(bucket_id)
    
    if bucket.exists():
        return bucket, False
    
    try:
        new_bucket = client.create_bucket(bucket_id)
        logger.info(f"Created new bucket: {bucket_id}")
        return new_bucket, True
    except Conflict:
        
        logger.info(f"Bucket {bucket_id} already exists (race condition)")
        return bucket, False
    except GoogleAPIError as e:
        logger.exception(f"Failed to create bucket '{bucket_id}': {e}")
        raise

def transfer_bucket_contents(source_bucket_id: str, dest_bucket_id: str) -> List[str]:
    
    client = storage.Client()
    source_bucket = client.bucket(source_bucket_id)
    
    
    if not source_bucket.exists():
        raise ValueError(f"Source bucket '{source_bucket_id}' does not exist")
    
    
    dest_bucket, was_created = ensure_bucket_exists(dest_bucket_id)
    
    transferred_blobs = []
    
    try:
        
        blobs = client.list_blobs(source_bucket_id)
        
        
        for blob in blobs:
            source_bucket.copy_blob(blob, dest_bucket, blob.name)
            transferred_blobs.append(blob.name)
            logger.info(f"Transferred: {blob.name}")
    except GoogleAPIError as e:
        
        if was_created:
            try:
                dest_bucket.delete(force=True)
                logger.info(f"Cleaned up destination bucket after failed transfer: {dest_bucket_id}")
            except Exception as cleanup_error:
                logger.error(f"Failed to clean up destination bucket: {cleanup_error}")
        
        logger.exception(f"Error during bucket transfer: {e}")
        raise
    
    return transferred_blobs

def ensure_directory_in_zip(zip_file: zipfile.ZipFile, directory_path: str) -> None:
    
    if not directory_path:
        return
        
    
    directory_path = directory_path.rstrip("/")
    if not directory_path:
        return
        
    directory_path += "/"
    
    
    if directory_path in [info.filename for info in zip_file.filelist]:
        return
        
    
    zip_file.writestr(directory_path, "")
    
    
    if "/" in directory_path[:-1]:
        parent_dir = "/".join(directory_path.split("/")[:-2]) + "/"
        ensure_directory_in_zip(zip_file, parent_dir)

def create_zip_from_bucket(bucket_id: str, bucket_name: str) -> io.BytesIO:
    
    client = storage.Client()
    bucket = client.bucket(bucket_id)
    
    # Check if bucket exists
    if not bucket.exists():
        raise ValueError(f"Bucket '{bucket_name}' does not exist")
    
    
    zip_buffer = io.BytesIO()
    
    try:
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # List all blobs in the bucket
            blobs = list(client.list_blobs(bucket_id))
            
            
            directories = set()
            for blob in blobs:
                # Extract all parent directories
                parts = blob.name.split('/')
                for i in range(1, len(parts)):
                    dir_path = '/'.join(parts[:i]) + '/'
                    directories.add(dir_path)
            
            # Add directory entries
            for directory in sorted(directories):
                zip_file.writestr(directory, "")
                logger.info(f"Added directory to ZIP: {directory}")
            
            
            for blob in blobs:
                
                if blob.name.endswith('/') and blob.size == 0:
                    continue
                    
                
                content = blob.download_as_bytes()
                
                
                zip_file.writestr(blob.name, content)
                logger.info(f"Added file to ZIP: {blob.name}")
    except GoogleAPIError as e:
        logger.exception(f"Error creating ZIP from bucket '{bucket_name}': {e}")
        raise
    
    
    zip_buffer.seek(0)
    return zip_buffer

def fetch_bucket_metadata(bucket_id: str) -> BucketMetadataResponse:
    client = storage.Client()
    try:
        bucket = client.get_bucket(bucket_id)
        bucket.reload()
    except Exception as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
            detail=f"Bucket '{bucket_id}' not found: {e}")

    props = bucket._properties
    loc_type      = getattr(bucket, "location_type", None) or props.get("locationType")
    default_class = bucket.storage_class or props.get("defaultStorageClass")
    last_mod      = bucket.updated.isoformat() if bucket.updated else bucket.time_created.isoformat()
    iam           = bucket.iam_configuration
    public_access = (
        iam.public_access_prevention
        if iam and iam.public_access_prevention.lower() != "inherited"
        else ("Enforced" if iam and iam.uniform_bucket_level_access_enabled else "Subject to object ACLs")
    )
    access_ctrl   = ("Uniform bucket-level access" if iam and iam.uniform_bucket_level_access_enabled else "Fine-grained")
    
    soft_delete = None
    rules = getattr(bucket, "lifecycle_rules", props.get("lifecycle", {}).get("rule", []))
    for rule in rules:
        if rule.get("action", {}).get("type", "").lower() == "delete":
            soft_delete = "Soft Delete"
            break

    return BucketMetadataResponse(
        name=bucket.name,
        bucket_uri=f"gs://{bucket.name}",
        created=bucket.time_created.isoformat(),
        location_type=loc_type,
        location=bucket.location,
        default_storage_class=default_class,
        last_modified=last_mod,
        public_access=public_access,
        access_control=access_ctrl,
        protection=soft_delete,
    )

def update_bucket_settings(bucket_id: str, updates: dict) -> None:
    
    filtered_updates = {}
    for key, value in updates.items():
        
        if value != "string" and (not isinstance(value, str) or value.strip()):
            filtered_updates[key] = value
    
    
    if not filtered_updates:
        
        return
    
    client = storage.Client()
    try:
        bucket = client.get_bucket(bucket_id)
    except Exception as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
            detail=f"Bucket '{bucket_id}' not found: {e}")

    
    if "default_storage_class" in filtered_updates:
        storage_class = filtered_updates["default_storage_class"]
        
        valid_storage_classes = ["STANDARD", "NEARLINE", "COLDLINE", "ARCHIVE"]
        if storage_class.upper() in valid_storage_classes:
            bucket.storage_class = storage_class.upper()
        else:
            logger.warning(f"Ignoring invalid storage class: {storage_class}")
            
    if "public_access" in filtered_updates:
        val = filtered_updates["public_access"].lower()
        if val in ("enforced", "inherited"):
            bucket.iam_configuration.public_access_prevention = val
        else:
            logger.warning(f"Ignoring invalid public_access value: {val}")
            
    if "access_control" in filtered_updates:
        val = filtered_updates["access_control"].lower()
        if val in ("fine-grained", "uniform bucket-level access"):
            bucket.iam_configuration.uniform_bucket_level_access_enabled = (
                val == "uniform bucket-level access"
            )
        else:
            logger.warning(f"Ignoring invalid access_control value: {val}")
            
    if "protection" in filtered_updates:
        
        rules = list(bucket.lifecycle_rules or [])
        
        rules = [r for r in rules
                 if not (r.get("action",{}).get("type","").lower()=="delete")]
                 
        val = filtered_updates["protection"]
        if val == "Soft Delete":
            retention_days = filtered_updates.get("soft_delete_retention_days", 7)
            
            if not isinstance(retention_days, int) or retention_days <= 0:
                retention_days = 7
                
            rules.append({
                "action": {"type": "Delete"},
                "condition": {"age": retention_days}
            })
            bucket.lifecycle_rules = rules
        elif val not in (None, "None", ""):
            logger.warning(f"Ignoring invalid protection value: {val}")

    
    try:
        bucket.patch()
        logger.info(f"Successfully updated bucket {bucket_id} with {filtered_updates}")
    except GoogleAPIError as e:
        logger.error(f"GCS patch failed: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"GCS update failed: {e}")    

def get_bucket_id_from_uri(bucket_uri: str) -> str:
    """Extract bucket ID from bucket URI"""
    match = _GS_URI_RE.match(bucket_uri)
    if match:
        return match.group(1)
    else:
        raise HTTPException(status_code=500, detail="Invalid bucket URI format")

def upload_node_code_to_bucket(
    bucket_uri: str,
    file_name: str,
    data: bytes,
    content_type: str = "application/octet-stream"
) -> str:
    bucket = parse_bucket_uri(bucket_uri)
    blob = bucket.blob(file_name)
    try:
        blob.upload_from_string(data, content_type=content_type)
        logger.info(f"Uploaded file '{file_name}' to bucket '{bucket_uri}'.")
        return blob.public_url
    except GoogleAPIError:
        logger.exception("Failed to upload file to GCS.")
        raise

