# router/buckets.py
from fastapi import APIRouter, HTTPException, Query, Response, Depends, status, Body
from typing import Dict, List, Tuple, Optional
from google.cloud import storage
from google.api_core.exceptions import GoogleAPIError, Conflict
import re
import logging
import io
import zipfile
from fastapi.responses import StreamingResponse
import uuid
from dependencies import requires_tenant
from models.tenant import Tenant
from models.bucket import Bucket
from utils.bucket_operation import create_zip_from_bucket, fetch_bucket_metadata, generate_bucket_id, sanitize_bucket_name, transfer_bucket_contents, update_bucket_settings,get_bucket_id_from_uri,parse_bucket_uri
from utils.ip_verifier import verify_ip
from database.session import get_db   
from sqlalchemy.orm import Session
from sqlalchemy import text
from schemas.bucket import BucketMetadataResponse, BucketMetadataUpdateRequest,BucketAllDataResponse,FolderMetadata
from schemas.storage import FileResponse
logger = logging.getLogger(__name__)

router = APIRouter()

_GS_URI_RE = re.compile(r"^gs://([^/]+)/?$")




@router.post("/rename", response_model=Dict[str, str])
def rename_bucket(
    current_name: str = Query(..., description="Current bucket name"),
    new_name: str = Query(..., description="New desired bucket name (any case/spaces)"),
    tenant: Tenant = Depends(requires_tenant),
    db: Session = Depends(get_db),
    _: bool = Depends(verify_ip)
):
    # Verify the current bucket exists by getting its URI
    try:
        result = db.execute(
            text("SELECT get_bucket_uri(:name, :tenant_id)"),
            {"name": current_name, "tenant_id": tenant.id}
        )
        current_bucket_uri = result.scalar_one()
    except Exception:
        raise HTTPException(status_code=404, detail=f"Bucket '{current_name}' not found")

    # Check if the new name already exists
    exists = db.execute(
        text("SELECT bucket_exists(:name, :tenant_id)"),
        {"name": new_name, "tenant_id": tenant.id}
    ).scalar()
    if exists:
        raise HTTPException(status_code=409, detail=f"Bucket with name '{new_name}' already exists")

    # Perform the rename via the stored function
    result = db.execute(
        text("SELECT update_bucket_name(:name, :new_name, :tenant_id)"),
        {"name": current_name, "new_name": new_name, "tenant_id": tenant.id}
    )
    success = result.scalar()
    if not success:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to rename bucket '{current_name}' to '{new_name}'")

    db.commit()
    return {"bucket_name": new_name, "message": "Bucket renamed successfully"}


@router.post("/transfer", response_model=Dict[str, object])
def transfer_bucket(
    source_bucket_name: str = Query(..., description="Source bucket name"),
    dest_bucket_name: str = Query(..., description="Destination bucket name"),
    tenant: Tenant = Depends(requires_tenant),
    db: Session = Depends(get_db),
    _: bool = Depends(verify_ip)
):
    try:
        # Get source bucket URI using stored procedure with proper error handling
        try:
            source_result = db.execute(
                text("SELECT get_bucket_uri(:name, :tenant_id)"),
                {"name": source_bucket_name, "tenant_id": tenant.id}
            )
            source_bucket_uri = source_result.scalar_one()
            source_bucket_id = get_bucket_id_from_uri(source_bucket_uri)
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"Source bucket '{source_bucket_name}' not found")
        
        # Get destination bucket URI using stored procedure with proper error handling
        try:
            dest_result = db.execute(
                text("SELECT get_bucket_uri(:name, :tenant_id)"),
                {"name": dest_bucket_name, "tenant_id": tenant.id}
            )
            dest_bucket_uri = dest_result.scalar_one()
            dest_bucket_id = get_bucket_id_from_uri(dest_bucket_uri)
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"Destination bucket '{dest_bucket_name}' not found")
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Handle any other errors
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    # Don't allow transferring to the same bucket
    if source_bucket_id == dest_bucket_id:
        raise HTTPException(status_code=400, detail="Source and destination buckets cannot be the same")
    
    try:
        transferred_blobs = transfer_bucket_contents(source_bucket_id, dest_bucket_id)
        
        # Determine if destination was created as part of this operation
        bucket_creation_msg = ""
        
        return {
            "source_bucket": source_bucket_name,
            "destination_bucket": dest_bucket_name,
            "files_transferred": len(transferred_blobs),
            "message": f"Bucket contents transferred successfully{bucket_creation_msg}"
        }
    except ValueError as e:
        # Handle missing source bucket
        raise HTTPException(status_code=404, detail=str(e))
    except GoogleAPIError as e:
        # Handle GCS API errors
        raise HTTPException(status_code=500, detail=f"Transfer failed: {str(e)}")    
    
@router.get("/download", response_class=Response)
async def download_bucket_as_zip(
    bucket_name: str = Query(..., description="Bucket name"),
    tenant: Tenant = Depends(requires_tenant),
    db: Session = Depends(get_db),
    _: bool = Depends(verify_ip)
):
    try:
        # Get bucket URI using stored procedure
        result = db.execute(
            text("SELECT get_bucket_uri(:name, :tenant_id)"),
            {"name": bucket_name, "tenant_id": tenant.id}
        )
        bucket_uri = result.scalar_one()
        bucket_id = get_bucket_id_from_uri(bucket_uri)
        
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Bucket '{bucket_name}' not found")
        else:
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    try:
        # Create ZIP archive from bucket contents
        zip_buffer = create_zip_from_bucket(bucket_id, bucket_name)
        
        # Return as a streaming response
        return StreamingResponse(
            zip_buffer, 
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={bucket_name}.zip"
            }
        )
    except ValueError as e:
        # Handle missing bucket
        raise HTTPException(status_code=404, detail=str(e))
    except GoogleAPIError as e:
        # Handle GCS API errors
        raise HTTPException(status_code=500, detail=f"ZIP creation failed: {str(e)}")


@router.get("/all")
def list_buckets(db: Session = Depends(get_db), tenant=Depends(requires_tenant)):
    try:
        # Execute the SQL function to get all buckets for the tenant
        records = db.execute(
            text("SELECT * FROM list_tenant_buckets(:tenant_id)"),
            {"tenant_id": str(tenant.id)}
        ).fetchall()
        
        # Process the results - only extract bucket_id and name
        result = []
        for record in records:
            # Handle both named tuple and dictionary access methods
            try:
                # Try accessing as named tuple
                result.append({
                    "bucket_id": record.bucket_id,
                    "name": record.name
                })
            except AttributeError:
                # If it fails, try accessing as dictionary or by index
                # bucket_id is at index 0, name is at index 1
                result.append({
                    "bucket_id": record[0],
                    "name": record[1]
                })
            
        return result
        
    except Exception as e:
        # Proper error handling
        logger.error(f"Error listing buckets: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_bucket(
    bucket_name: str = Query(...),
    db: Session = Depends(get_db),
    tenant=Depends(requires_tenant),
    _: bool = Depends(verify_ip),
):
    # Check if bucket exists using stored procedure
    exists = db.execute(text(
        "SELECT bucket_exists(:name, :tenant_id)"),
        {"name": bucket_name, "tenant_id": tenant.id}
    ).scalar()
    
    if exists:
        raise HTTPException(400, f"Bucket with name '{bucket_name}' already exists")
    
    bucket_id = generate_bucket_id()
    sanitized_bucket_id = sanitize_bucket_name(bucket_id)
    
    client = storage.Client()
    
    try:
        client.create_bucket(sanitized_bucket_id)
    except Conflict:
        # In the unlikely event of a UUID collision, try again
        sanitized_bucket_id = sanitize_bucket_name(generate_bucket_id())
        client.create_bucket(sanitized_bucket_id)
    except GoogleAPIError as e:
        raise HTTPException(500, f"GCS error: {e}")
    
    # Record in database using stored procedure
    bucket_uri = f"gs://{sanitized_bucket_id}"
    db.execute(text(
        "SELECT insert_bucket(:bucket_id, :name, :bucket_uri, :tenant_id)"),
        {
            "bucket_id": sanitized_bucket_id,
            "name": bucket_name,
            "bucket_uri": bucket_uri,
            "tenant_id": tenant.id
        }
    )
    db.commit()
    
    return {"name": bucket_name, "message": "Bucket created"}


@router.get("/{name}")
def get_bucket(name: str, db: Session = Depends(get_db), tenant=Depends(requires_tenant)):
    try:
        # Get bucket URI using stored procedure
        result = db.execute(
            text("SELECT get_bucket_uri(:name, :tenant_id)"),
            {"name": name, "tenant_id": tenant.id}
        )
        bucket_uri = result.scalar_one()
        bucket_id = get_bucket_id_from_uri(bucket_uri)
        
        # Fetch metadata using the bucket ID
        metadata = fetch_bucket_metadata(bucket_id)
        
        # Build response
        result = metadata.dict()
        result["name"] = name
        
        return result
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(404, "Bucket not found")
        else:
            raise HTTPException(500, f"Error fetching bucket metadata: {str(e)}")


@router.put(
    "/metadata/{name}",
    status_code=status.HTTP_200_OK,
    summary="update bucket settings"
)
def update_bucket_by_id(
    name: str,
    update_request: BucketMetadataUpdateRequest = Body(...),
    db: Session = Depends(get_db),
    tenant = Depends(requires_tenant),
):
    
    
    try:
        # 1. Get bucket URI using stored procedure
        try:
            result = db.execute(
                text("SELECT get_bucket_uri(:name, :tenant_id)"),
                {"name": name, "tenant_id": str(tenant.id)}
            )
            bucket_uri = result.scalar_one()
            
            # Extract bucket_id from URI
            bucket_id = get_bucket_id_from_uri(bucket_uri)
            
            if not bucket_id:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to extract bucket ID from URI"
                )
                
        except Exception as e:
            if "not found" in str(e).lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Bucket '{name}' not found for this tenant"
                )
            else:
                logger.error(f"Error accessing bucket URI: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error accessing bucket: {str(e)}"
                )
        
        # 2. Extract only client-sent fields
        update_data = update_request.dict(exclude_unset=True)
        
        updated_fields = []
        ignored_fields = []
        response = {"name": name}
        
        # 3. Rename in DB if requested
        if "name" in update_data:
            new_name = update_data.pop("name")
            # Only update the name if it's not a placeholder value
            if new_name != "string" and new_name and new_name.strip():
                # Check if the new name is already taken
                try:
                    exists = db.execute(text(
                        "SELECT bucket_exists(:name, :tenant_id)"),
                        {"name": new_name, "tenant_id": str(tenant.id)}
                    ).scalar()
                    
                    if exists:
                        # Need to check if it's the same bucket or a different one
                        try:
                            existing_uri = db.execute(
                                text("SELECT get_bucket_uri(:name, :tenant_id)"),
                                {"name": new_name, "tenant_id": str(tenant.id)}
                            ).scalar_one()
                            
                            existing_id = get_bucket_id_from_uri(existing_uri)
                            
                            if existing_id and existing_id != bucket_id:
                                raise HTTPException(
                                    status_code=status.HTTP_409_CONFLICT,
                                    detail=f"Bucket name '{new_name}' is already in use"
                                )
                        except Exception as e:
                            if "not found" not in str(e).lower():
                                logger.error(f"Error checking existing bucket: {str(e)}")
                                raise HTTPException(
                                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                    detail=f"Error checking existing bucket: {str(e)}"
                                )
                    
                    success = db.execute(text(
                        "SELECT update_bucket_name(:name, :new_name, :tenant_id)"),
                        {"name": name, "new_name": new_name, "tenant_id": str(tenant.id)}
                    ).scalar()
                    
                    if not success:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Failed to update bucket name from '{name}' to '{new_name}'"
                        )
                    
                    db.commit()
                    updated_fields.append("name")
                    response["name"] = new_name
                    response["previous_name"] = name
                except HTTPException:
                    raise
                except Exception as e:
                    db.rollback()
                    logger.error(f"Database error during name update: {str(e)}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Database error during name update: {str(e)}"
                    )
            else:
                ignored_fields.append("name")
                logger.warning(f"Ignoring invalid name update value: '{new_name}'")
        
        # 4. Update GCS bucket settings if any updates remain
        if update_data:
            try:
                update_bucket_settings(bucket_id, update_data)
                
                # Identify which fields were actually updated vs ignored
                for key in update_data:
                    if update_data[key] == "string" or (isinstance(update_data[key], str) and not update_data[key].strip()):
                        ignored_fields.append(key)
                    else:
                        updated_fields.append(key)
                    
            except HTTPException as e:
                # Don't rollback the name change if it occurred
                if "name" in updated_fields:
                    response["message"] = f"Bucket name updated but other settings failed: {e.detail}"
                    response["updated_fields"] = ["name"]
                    return response
                else:
                    raise e
            except Exception as e:
                logger.error(f"Unexpected error updating bucket settings: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Unexpected error updating bucket settings: {str(e)}"
                )
        
        # 5. Build response message
        response["updated_fields"] = updated_fields
        if ignored_fields:
            response["ignored_fields"] = ignored_fields
            
        if updated_fields:
            response["message"] = f"Bucket updated successfully. Fields updated: {', '.join(updated_fields)}"
            if ignored_fields:
                response["message"] += f". Fields ignored (had placeholder values): {', '.join(ignored_fields)}"
        elif ignored_fields:
            response["message"] = f"No changes were made. All fields had placeholder values: {', '.join(ignored_fields)}"
        else:
            response["message"] = "No changes were made to the bucket"
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error in update_bucket_by_id: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )
    

@router.delete("/{name}", status_code=status.HTTP_200_OK)
def delete_bucket(
    name: str,
    db: Session = Depends(get_db),
    tenant=Depends(requires_tenant),
    _: bool = Depends(verify_ip),
):
    try:
        # Get bucket URI using stored procedure
        result = db.execute(
            text("SELECT get_bucket_uri(:name, :tenant_id)"),
            {"name": name, "tenant_id": tenant.id}
        )
        bucket_uri = result.scalar_one()
        bucket_id = get_bucket_id_from_uri(bucket_uri)
        
        # Now delete the bucket from GCS
        client = storage.Client()
        bucket = client.bucket(bucket_id)
        try:
            bucket.delete(force=True)
        except GoogleAPIError as e:
            raise HTTPException(500, f"GCS delete error: {e}")
        
        # Use the stored procedure to delete the DB record
        db.execute(
            text("CALL delete_bucket_record(:name, :tenant_id)"),
            {"name": str(name), "tenant_id": str(tenant.id)}
        )
        db.commit()
        
        return {"message": f"Bucket '{name}' deleted"}
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(404, "Bucket not found")
        else:
            raise HTTPException(500, f"Error deleting bucket: {str(e)}")
        

@router.get(
    "/{name}/all-data",
    response_model=None,  
    summary="Get all bucket data including metadata, files list, and folders list"
)
def get_bucket_all_data(
    name: str, 
    db: Session = Depends(get_db), 
    tenant: Tenant = Depends(requires_tenant),
    _: bool = Depends(verify_ip)
):
    try:
        # 1. Get bucket URI using stored procedure
        result = db.execute(
            text("SELECT get_bucket_uri(:name, :tenant_id)"),
            {"name": name, "tenant_id": tenant.id}
        )
        bucket_uri = result.scalar_one()
        bucket_id = get_bucket_id_from_uri(bucket_uri)
        
        # 2. Fetch bucket metadata
        metadata = fetch_bucket_metadata(bucket_id)
        
        # 3. Get all files and folders in the bucket
        client = storage.Client()
        bucket = client.get_bucket(bucket_id)
        blobs = list(bucket.list_blobs())
        
        # Process files
        files = []
        total_size = 0
        
        for blob in blobs:
            # Skip folder placeholders
            if blob.name.endswith('/'):
                continue
                
            # Get file metadata
            blob.reload()  # Ensure we have latest metadata
            filename = blob.name.split('/')[-1]
            file_size = blob.size
            total_size += file_size
            
            # Get detailed metadata for the file
            file_metadata = {
                "name": filename,
                # "path": blob.name,  # Restored this field
                # "uri": f"{bucket_uri}/{blob.name}",  # Restored this field
                "size": file_size,
                # "type": filename.split('.')[-1] if '.' in filename else "",
                
                "type": blob.content_type,
                "created": blob.time_created.isoformat() if blob.time_created else None,
                "last_modified": blob.updated.isoformat() if blob.updated else None,
                "storage_class": blob.storage_class,
                "public_access": "Not public",
                "version_history": "—",
                "encryption": "Google-managed",
                "object_retention retain until time": "—",
                # "retain_until_time": "—",
                "retention_expiration_time": blob.retention_expiration_time.isoformat() if blob.retention_expiration_time else "—",
                "holds": "None"
            }
            
            # Simplified public access check to avoid potential errors
            try:
                acl = blob.acl
                if 'allUsers' in [entry.entity for entry in acl.get_entities()]:
                    file_metadata["public_access"] = "Public"
            except Exception as e:
                logger.warning(f"Could not check ACL for blob {blob.name}: {str(e)}")
            
            files.append(file_metadata)
        
        # 4. Extract all folders from blob paths and compute folder metadata
        folders_set = set()
        folder_contents = {}  # To track files and size per folder
        
        # Add root folder
        folders_set.add("")
        folder_contents[""] = {"files": 0, "size": 0, "last_modified": None, "created": None}
        
        # Process all blobs to extract folder paths
        for blob in blobs:
            path_parts = blob.name.split('/')
            current_path = ""
            
            # Build each folder path
            for i in range(len(path_parts) - 1):  # Skip the file name part
                if path_parts[i]:  # Skip empty segments
                    if current_path:
                        current_path += f"/{path_parts[i]}"
                    else:
                        current_path = path_parts[i]
                    folders_set.add(current_path)
                    
                    # Initialize folder content tracking if needed
                    if current_path not in folder_contents:
                        folder_contents[current_path] = {
                            "files": 0, 
                            "size": 0, 
                            "last_modified": None,
                            "created": None
                        }
                    
                    # Update folder created time if this is the first file or older
                    if (blob.time_created and 
                        (not folder_contents[current_path]["created"] or 
                         blob.time_created < folder_contents[current_path]["created"])):
                        folder_contents[current_path]["created"] = blob.time_created
            
            # Count this file for its parent folder
            parent_folder = "/".join(path_parts[:-1]) if len(path_parts) > 1 else ""
            if not blob.name.endswith('/'):  # Only count actual files
                folder_contents[parent_folder]["files"] += 1
                folder_contents[parent_folder]["size"] += blob.size
                
                # Update last modified time if this file is newer
                if (blob.updated and 
                    (not folder_contents[parent_folder]["last_modified"] or 
                     blob.updated > folder_contents[parent_folder]["last_modified"])):
                    folder_contents[parent_folder]["last_modified"] = blob.updated
                
                # Update created time if this file is older
                if (blob.time_created and 
                    (not folder_contents[parent_folder]["created"] or 
                     blob.time_created < folder_contents[parent_folder]["created"])):
                    folder_contents[parent_folder]["created"] = blob.time_created
                    
                # Also update all parent folders
                parts = parent_folder.split('/')
                for i in range(len(parts)):
                    parent = "/".join(parts[:i])
                    if parent in folder_contents:
                        folder_contents[parent]["files"] += 1
                        folder_contents[parent]["size"] += blob.size
                        if (blob.updated and 
                            (not folder_contents[parent]["last_modified"] or 
                             blob.updated > folder_contents[parent]["last_modified"])):
                            folder_contents[parent]["last_modified"] = blob.updated
                        if (blob.time_created and 
                            (not folder_contents[parent]["created"] or 
                             blob.time_created < folder_contents[parent]["created"])):
                            folder_contents[parent]["created"] = blob.time_created
        
        # Convert to folder metadata objects
        folders = []
        for folder_path in sorted(folders_set):
            folder_name = folder_path.split('/')[-1] if folder_path else "root"
            folder_info = folder_contents.get(folder_path, {
                "files": 0, 
                "size": 0, 
                "last_modified": None,
                "created": None
            })
            
            folder_metadata = {
                "name": folder_name,
                # "path": folder_path,  # Restored this field
                # "uri": f"{bucket_uri}/{folder_path}{'/' if folder_path else ''}",  # Restored this field
                # "file_count": folder_info["files"],  # Restored this field
                "size": folder_info["size"],  # Changed to integer value only
                "type": "Folder",
                "created": folder_info["created"].isoformat() if folder_info["created"] else "—",
                "storage_class": bucket.storage_class,
                "last_modified": folder_info["last_modified"].isoformat() if folder_info["last_modified"] else "—",
                "public_access": metadata.public_access,
                "version_history": "—",
                "encryption": "Google-managed",
                "object_retention retain until time": "—",
                # "retain_until_time": "—",
                "retention_expiration_time": "—",
                "holds": "None"
            }
            
            folders.append(folder_metadata)
        
        # 5. Assemble the response
        response = {
            "bucket_id": bucket_id,
            "name": name,
            "bucket_uri": bucket_uri,
            "created": metadata.created,
            "location_type": metadata.location_type,
            "location": metadata.location,
            "default_storage_class": metadata.default_storage_class,
            "last_modified": metadata.last_modified,
            "public_access": metadata.public_access,
            "access_control": metadata.access_control,
            "protection": metadata.protection,
            "file_count": len(files),
            "folder_count": len(folders),
            "total_size_bytes": total_size,
            "files": files,
            "folders": folders
        }
        
        return response
        
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Bucket '{name}' not found")
        else:
            logger.error(f"Error fetching bucket all data: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error fetching bucket all data: {str(e)}")