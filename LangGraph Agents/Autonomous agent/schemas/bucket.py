from pydantic import BaseModel,Field
from typing import Optional,List,Dict,Any
from .storage import FileResponse



class BucketMetadataResponse(BaseModel):
    name: str                                
    created: str
    location_type: Optional[str] = None
    location: Optional[str] = None
    default_storage_class: Optional[str] = None
    last_modified: Optional[str] = None
    public_access: Optional[str] = None
    access_control: Optional[str] = None
    protection: Optional[str] = None
    bucket_uri: Optional[str] = None        

    class Config:
        populate_by_name = True
        

class BucketMetadataUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, description="User-displayed name for the bucket (updates DB record)")
    default_storage_class: Optional[str] = Field(None, description="STANDARD, NEARLINE, COLDLINE, ARCHIVE, etc.")
    public_access: Optional[str] = Field(None, description="'Subject to object ACLs' or 'Enforced'")
    access_control: Optional[str] = Field( None, description="'Fine‑grained' or 'Uniform bucket‑level access'")
    protection: Optional[str] = Field(None, description="'Soft Delete' or None")
    soft_delete_retention_days: Optional[int] = Field(None, description="Days to retain deleted objects")

    class Config:
        populate_by_name = True    


class FolderMetadata(BaseModel):
    name: str
    path: str
    uri: str

class BucketAllDataResponse(BaseModel):
    # Bucket metadata
    bucket_id: str
    name: str
    bucket_uri: str
    created: str
    location_type: Optional[str] = None
    location: Optional[str] = None
    default_storage_class: Optional[str] = None
    last_modified: Optional[str] = None
    public_access: Optional[str] = None
    access_control: Optional[str] = None
    protection: Optional[str] = None
    
    # Statistics
    file_count: int
    folder_count: int
    total_size_bytes: int = 0
    
    # Separate lists for files and folders
    files: List[FileResponse] = Field(default_factory=list)
    folders: List[FolderMetadata] = Field(default_factory=list)
    
    class Config:
        populate_by_name = True