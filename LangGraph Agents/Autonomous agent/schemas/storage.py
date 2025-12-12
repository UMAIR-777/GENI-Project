from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class FileCreate(BaseModel):
    name: str = Field(description="File name without extension")
    file_type: str = Field(description="File extension or type")
    folder_path: str = Field(description="Path where the file will be stored")
    data: bytes = Field(description="Binary content of the file")


class FileResponse(BaseModel):
    
    name: str = Field(description="File name")
    path: str = Field(description="Full path to the file")
    
    file_type: Optional[str] = Field(None, description="File extension or type")
    
    data: Optional[bytes] = Field(None, description="Binary content of the file")

    size:Optional[int] = Field(None,description="file size in bytes")


class FolderCreate(BaseModel):
    name: str = Field(..., description="Folder name")  
    path: str = Field(description="Folder path including the folder name")
    
    
    


class FolderWithContentResponse(BaseModel):
    
    name: str = Field(description="Folder name")
    path: str = Field(description="Full path to the folder")
    children: List["FolderWithContentResponse"] = Field(default_factory=list, description="Subfolders")
    files: List[FileResponse] = Field(default_factory=list, description="Files in this folder")


# This is necessary for the recursive model to work properly
FolderWithContentResponse.model_rebuild()