from os import path
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Query,Body,Path, Depends
from database.session import get_db
from dependencies.authorization import requires_tenant
from utils.ip_verifier import verify_ip
from sqlalchemy              import text
from models.tenant import Tenant
from sqlalchemy.orm          import Session
from schemas.storage import FolderWithContentResponse, FolderCreate
from utils.bucket_operation import list_files_in_gcs, build_tree_from_blobs, create_folder_in_gcs, parse_bucket_uri,delete_folder_in_gcs,get_gcs_folder_path
from typing import Annotated
from google.api_core.exceptions import GoogleAPIError

router = APIRouter()


@router.get(
    "/structure",
    response_model=FolderWithContentResponse,
    summary="Get GCS-based folder structure for a given bucket URI and optional path"
)
def get_gcs_structure(
    path: Optional[str] = Query("", description="Folder path within bucket (e.g. 'docs/subfolder'); leave empty for full bucket"),
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
        blobs = list_files_in_gcs(bucket_uri, path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GCS list failed: {e}")

    
    tree: Dict[str, Any] = {}
    prefix = path.rstrip("/") + "/" if path else ""
    for blob_name in blobs:
        
        rel = blob_name[len(prefix):] if prefix and blob_name.startswith(prefix) else blob_name
        
        parts = [p for p in rel.split("/") if p]
        node = tree
        for idx, part in enumerate(parts):
            last = (idx == len(parts) - 1)
            if last:
                
                if blob_name.endswith("/"):
                    node.setdefault(part, {})  # ensure folder entry
                else:
                    node[part] = None          # file entry
            else:
                
                node = node.setdefault(part, {})

    
    return build_tree_from_blobs(tree, prefix)

@router.post("/", response_model=dict)
def create_folder(
    folder: FolderCreate = Body(..., description="Folder details"),
    bucket_name: str = Query(..., description="Bucket Name"),
    tenant     : Tenant  = Depends(requires_tenant),
    db         : Session = Depends(get_db),
    _          : bool    = Depends(verify_ip)
):
    full_folder_path = (
        f"{folder.path.rstrip('/')}/{folder.name}"
        if folder.path
        else folder.name
    )
    
    try:
        result = db.execute(
            text("SELECT get_bucket_uri(:name, :tenant)"),
            {"name": bucket_name, "tenant": tenant.id}
        )
        bucket_uri = result.scalar_one()
        
        # Check if folder already exists
        bucket = parse_bucket_uri(bucket_uri)
        normalized_folder = get_gcs_folder_path(full_folder_path)
        folder_blob_name = normalized_folder.rstrip("/") + "/" if normalized_folder else "root/"
        
        # Check if folder or any objects with this prefix already exist
        existing_blobs = list(bucket.list_blobs(prefix=folder_blob_name, max_results=1))
        folder_blob = bucket.blob(folder_blob_name)
        
        if existing_blobs or folder_blob.exists():
            raise HTTPException(status_code=409, detail=f"Folder '{folder.name}' already exists in this path")
        
        create_folder_in_gcs(bucket_uri, full_folder_path)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, detail=str(e))
        
    return {
        "message": "Folder created successfully",
        "name": folder.name,
        "path": full_folder_path
    }
    
@router.get("/{folder_path:path}/files", response_model=List[Dict[str, str]])
def get_files_of_specific_folder(
    folder_path: str,
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
        
        # Normalize the folder path
        if folder_path in ["", "/", "root"]:
            prefix = ""
        else:
            # Remove 'root/' prefix if present
            if folder_path.startswith("root/"):
                folder_path = folder_path[5:]
            prefix = folder_path.rstrip("/") + "/"
        
        # First check if the folder exists by looking for at least one blob with this prefix
        folder_exists = False
        test_blobs = list(bucket.list_blobs(prefix=prefix, max_results=1))
        folder_exists = len(test_blobs) > 0
        
        # Also check for folder placeholder if no blobs were found
        if not folder_exists:
            folder_placeholder = bucket.blob(prefix)
            folder_exists = folder_placeholder.exists()
        
        if not folder_exists:
            raise HTTPException(status_code=404, detail=f"Folder '{folder_path}' not found")
        
        # Use delimiter to get only direct children
        iterator = bucket.client.list_blobs(
            bucket.name, prefix=prefix, delimiter="/"
        )
        
        result = []
        # Process direct file blobs
        for blob in iterator:
            # Skip folder placeholder objects (ending with /)
            if not blob.name.endswith('/') and blob.name != prefix:
                # Only include files directly in this folder (no additional '/' in relative path)
                relative_name = blob.name[len(prefix):]
                if '/' not in relative_name:
                    result.append({
                        "name": relative_name, 
                        "path": blob.name,
                        "uri": f"{bucket_uri}/{blob.name}"
                    })
        return result
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))    


@router.delete("/{folder_path:path}", response_model=dict)
def delete_folder(
    folder_path: str = Path(..., description="Folder path inside the bucket, e.g. 'zain/zain2'"),
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
        delete_folder_in_gcs(bucket_uri, folder_path)
    except GoogleAPIError as e:
        
        raise HTTPException(status_code=500, detail=f"GCS folder deletion failed: {str(e)}")
    return {"message": "Folder and its contents deleted successfully"}


@router.get("/list_all_folders", response_model=List[Dict[str, str]])
def get_all_folders(
    bucket_name: str = Query(..., description="Bucket Name"),
    tenant     : Tenant  = Depends(requires_tenant),
    db         : Session = Depends(get_db),
    _          : bool    = Depends(verify_ip)
):
    """
    Get all folders in the bucket, including subfolders.
    """
    try:
        result = db.execute(
            text("SELECT get_bucket_uri(:name, :tenant)"),
            {"name": bucket_name, "tenant": tenant.id}
        )
        bucket_uri = result.scalar_one()
        bucket = parse_bucket_uri(bucket_uri)
        blobs = bucket.list_blobs()  # flat listing of all objects
        
        # Track all unique folder paths
        all_folders = set()
        
        for blob in blobs:
            # Extract all folder segments from each blob path
            parts = blob.name.split('/')
            
            # Build folder paths progressively
            current_path = ""
            for i in range(len(parts) - 1):  # Exclude the file name (last part)
                if parts[i]:  # Skip empty segments
                    if current_path:
                        current_path += f"/{parts[i]}"
                    else:
                        current_path = parts[i]
                    all_folders.add(current_path)
        
        # Convert to response format
        result = []
        for folder_path in sorted(all_folders):
            result.append({
                "name": folder_path.split('/')[-1],  # Just the folder name
                "path": folder_path,  # Full path without trailing slash
                "uri": f"{bucket_uri}/{folder_path}/"  # Full URI with trailing slash
            })
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
        
            
@router.get("/{folder_path}/folders", response_model=List[Dict[str, str]])
def get_folders_of_specific_folder(
    folder_path: str,
    bucket_name: str = Query(..., description="Bucket Name"),
    tenant     : Tenant  = Depends(requires_tenant),
    db         : Session = Depends(get_db),
    _          : bool    = Depends(verify_ip)
):
    """
    Get all subfolders (immediate and nested) of the specified folder path.
    The folder_path can be a nested path like 'doc/code'.
    """
    try:
        result = db.execute(
            text("SELECT get_bucket_uri(:name, :tenant)"),
            {"name": bucket_name, "tenant": tenant.id}
        )
        bucket_uri = result.scalar_one()
        # Parse bucket URI to get bucket name
        bucket = parse_bucket_uri(bucket_uri)
        
        # Normalize the folder path
        if folder_path in ["", "/", "root"]:
            prefix = ""
        else:
            # Remove 'root/' prefix if present
            if folder_path.startswith("root/"):
                folder_path = folder_path[5:]
            prefix = folder_path.rstrip("/") + "/"
        
        # Check if folder exists (except for root)
        if prefix:
            # First try to see if any blobs exist with this prefix
            blobs = list(bucket.list_blobs(prefix=prefix, max_results=1))
            folder_exists = len(blobs) > 0
            
            # If no blobs found, check if the folder placeholder exists
            if not folder_exists:
                folder_placeholder = bucket.blob(prefix)
                folder_exists = folder_placeholder.exists()
                
            if not folder_exists:
                raise HTTPException(status_code=404, detail=f"Folder '{folder_path}' not found")
        
        # Get all blobs under this prefix
        all_blobs = list(bucket.list_blobs(prefix=prefix))
        
        # Find all subfolder paths at any nesting level
        subfolder_dict = {}
        for blob in all_blobs:
            # Skip the folder placeholder itself
            if blob.name == prefix:
                continue
                
            # Get the relative path from the prefix
            rel_path = blob.name[len(prefix):]
            if not rel_path:
                continue
                
            # Extract all subfolder paths from this blob's path
            path_parts = rel_path.split('/')
            current_path = prefix
            
            # Build each subfolder path and add to results
            for i, part in enumerate(path_parts[:-1]):  # Skip the last part if it's a file
                if not part:  # Skip empty parts
                    continue
                    
                # Build the current subfolder path
                current_path += part + "/"
                subfolder = part
                subfolder_full_path = current_path.rstrip("/")
                
                # Add to results if not already there
                if subfolder_full_path not in subfolder_dict:
                    subfolder_dict[subfolder_full_path] = {
                        "name": subfolder,
                        "path": subfolder_full_path,
                        "uri": f"{bucket_uri}/{subfolder_full_path}"
                    }
        
        # Convert dictionary to list for response
        result = list(subfolder_dict.values())
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))