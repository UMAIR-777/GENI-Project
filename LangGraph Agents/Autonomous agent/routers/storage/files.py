from fastapi import APIRouter, HTTPException, Query, Body,Path, Depends,UploadFile,File,Form
from typing import Dict, List,Union
from sqlalchemy              import text
from sqlalchemy.orm          import Session
from database.session import get_db
from dependencies.authorization import requires_tenant
from utils.ip_verifier import verify_ip
from models.tenant import Tenant
from schemas.storage import FileCreate, FileResponse
from utils.bucket_operation import parse_bucket_uri,upload_file_to_gcs
import os
router = APIRouter()

@router.post("/", response_model=dict)
def create_file(
    file_data: FileCreate,
    bucket_name: str = Query(..., description="Bucket Name"),
    tenant     : Tenant  = Depends(requires_tenant),
    db         : Session = Depends(get_db),
    _          : bool    = Depends(verify_ip)
):
    result = db.execute(
        text("SELECT get_bucket_uri(:name, :tenant)"),
        {"name": bucket_name, "tenant": tenant.id}
    )
    bucket_uri = result.scalar_one() 
    
    # 1. Check if folder exists
    prefix = file_data.folder_path.rstrip("/") + "/" if file_data.folder_path else ""
    bucket = parse_bucket_uri(bucket_uri)
    exists_blob = list(bucket.list_blobs(prefix=prefix, max_results=1))
    placeholder = bucket.blob(prefix)
    if not exists_blob and not placeholder.exists():
        raise HTTPException(status_code=404, detail=f"Folder '{file_data.folder_path}' not found")
    
    # 2. Check if file already exists
    full_name = f"{file_data.name}.{file_data.file_type}"
    file_path = f"{prefix}{full_name}"
    file_blob = bucket.blob(file_path)
    
    if file_blob.exists():
        raise HTTPException(status_code=409, detail=f"File '{full_name}' already exists in this folder")
    
    # 3. Then upload
    try:
        upload_file_to_gcs(bucket_uri, file_data.folder_path, full_name, file_data.data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GCS storage failed: {e}")
    
    return {"message": "File created successfully"}

@router.get("/GetAllFiles", response_model=List[Dict[str, Union[str, int]]])
def get_all_files(
    bucket_name: str = Query(..., description="Bucket Name"),
    tenant     : Tenant  = Depends(requires_tenant),
    db         : Session = Depends(get_db),
    _          : bool    = Depends(verify_ip)
):
    try:
        result = db.execute(
            text("SELECT get_bucket_uri(:name, :tenant)"),
            {"name": bucket_name, "tenant": tenant.id}
        )
        bucket_uri = result.scalar_one() 
        bucket = parse_bucket_uri(bucket_uri)
        
        # Simply list all blobs in the bucket
        blobs = list(bucket.list_blobs())
        
        # If no blobs found, return empty list instead of error
        if not blobs:
            return []
        
        result = []
        for blob in blobs:
            # Skip folder placeholder objects
            if not blob.name.endswith('/'):
                # Extract filename from the full path
                filename = blob.name.split('/')[-1]
                folder_path = blob.name[:-(len(filename)+1)] if '/' in blob.name else ""
                
                # Get file size in bytes
                blob.reload()  # Ensure we have the latest metadata
                file_size = blob.size
                
                result.append({
                    "name": filename,
                    "path": blob.name,
                    "uri": f"{bucket_uri}/{blob.name}",
                    "file_type": filename.split('.')[-1] if '.' in filename else "",
                    "size": file_size  # Add file size in bytes
                })
        return result
    except Exception as e:
        # Log the error for debugging
        print(f"Error listing files: {str(e)}")
        # Return more descriptive error
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")
    

@router.get(
    "/{file_path:path}",
    response_model=FileResponse,
    summary="GET a file from GCS"
)
def get_file(
    file_path: str = Path(..., description="Full file path, e.g. 'subdir/report.pdf'"),
    bucket_name: str = Query(..., description="Bucket Name"),
    tenant     : Tenant  = Depends(requires_tenant),
    db         : Session = Depends(get_db),
    _          : bool    = Depends(verify_ip)
):
    result = db.execute(
        text("SELECT get_bucket_uri(:name, :tenant)"),
        {"name": bucket_name, "tenant": tenant.id}
    )
    bucket_uri = result.scalar_one() 
    bucket = parse_bucket_uri(bucket_uri)
    blob = bucket.blob(file_path)

    # Check existence
    if not blob.exists():
        raise HTTPException(status_code=404, detail=f"File '{file_path}' not found")

    # Get metadata including size
    blob.reload()
    file_size = blob.size

    # Download
    data = blob.download_as_bytes()
    filename = file_path.split("/")[-1]
    file_type = filename.split(".")[-1] if "." in filename else ""

    return {
        "name": filename,
        "path": file_path,
        "uri": f"{bucket_uri}/{file_path}",
        "file_type": file_type,
        "data": data,
        "size": file_size  # Add file size in bytes
    }
    
@router.delete(
    "/{file_path:path}",
    response_model=dict,
    summary="Delete a file from GCS"
)
def delete_file(
    file_path: str = Path(
        ..., description="Full file path including subdirectories, e.g. 'doc/work1.txt'"
    ),
    bucket_name: str = Query(..., description="Bucket Name"),
    tenant     : Tenant  = Depends(requires_tenant),
    db         : Session = Depends(get_db),
    _          : bool    = Depends(verify_ip)
):
    result = db.execute(
        text("SELECT get_bucket_uri(:name, :tenant)"),
        {"name": bucket_name, "tenant": tenant.id}
    )
    bucket_uri = result.scalar_one() 
    bucket = parse_bucket_uri(bucket_uri)
    blob = bucket.blob(file_path)
    if not blob.exists():
        raise HTTPException(status_code=404, detail=f"File '{file_path}' not found")
    blob.delete()
    return {"message": "File deleted successfully"}


@router.post("/upload", response_model=dict)
async def upload_file(
    file: UploadFile = File(..., description="File to upload"),
    folder_path: str = Form(None, description="Optional folder path"),
    bucket_name: str = Query(..., description="Bucket Name"),
    tenant: Tenant = Depends(requires_tenant),
    db: Session = Depends(get_db),
    _: bool = Depends(verify_ip)
):
    try:
        # Get bucket URI using the same DB function as other endpoints
        result = db.execute(
            text("SELECT get_bucket_uri(:name, :tenant)"),
            {"name": bucket_name, "tenant": tenant.id}
        )
        bucket_uri = result.scalar_one()
        
        # Get file content
        file_content = await file.read()
        file_name = file.filename
        
        # Prepare the file path
        prefix = folder_path.rstrip("/") + "/" if folder_path else ""
        file_path = f"{prefix}{file_name}"
        
        # Parse bucket from URI
        bucket = parse_bucket_uri(bucket_uri)
        
        # Check if file already exists
        file_blob = bucket.blob(file_path)
        if file_blob.exists():
            raise HTTPException(status_code=409, detail=f"File '{file_name}' already exists in this path")
        
        # Determine content type from the file
        content_type = file.content_type or "application/octet-stream"
        
        # Upload the file
        try:
            file_blob.upload_from_string(file_content, content_type=content_type)
            
            # Get file size
            file_blob.reload()
            file_size = file_blob.size
            
            # Get file extension
            file_type = os.path.splitext(file_name)[1][1:] if '.' in file_name else ""
            
            return {
                "message": "File uploaded successfully", 
                "path": file_path,
                "name": file_name,
                "size": file_size,
                "file_type": file_type,
                "uri": f"{bucket_uri}/{file_path}"
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"GCS storage failed: {e}")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")