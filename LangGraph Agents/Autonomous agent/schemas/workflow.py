from pydantic import BaseModel, field_validator, EmailStr, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


# ──────────────────────────────────────────────────────────────
# WORKFLOW SCHEMAS
# ──────────────────────────────────────────────────────────────

class WorkflowCreateResponse(BaseModel):
    workflow: dict  # Response after workflow creation


class WorkflowCreateRequest(BaseModel):
    task: str  # Task name for the workflow




class WorkflowResponse(BaseModel):
    id: str
    name: str
    data: dict
    tenant_id: str
    is_public: bool
    version: int
    group_id: Optional[str] = None  # optional if not returned by SP
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class WorkflowCreate(BaseModel):
    name: str = Field(..., description="Name of the workflow")
    data: dict = Field(..., description="Workflow data in JSON format")
    is_public: bool = Field(..., description="Whether the workflow is public")
    user_task: Optional[str] = Field(None, description="User task description for embedding")
    descriptions: Optional[List[str]] = Field(None, description="Descriptions for embedding")
    tags: Optional[List[str]] = Field(None, description="Tags for embedding")
    spo: Optional[dict] = Field(None, description="SPO data for embedding")

    @field_validator("data")
    @classmethod
    def data_must_be_object(cls, v: dict) -> dict:
        if not isinstance(v, dict):
            raise ValueError("Workflow data must be a JSON object")
        return v



class WorkflowUpdate(BaseModel):
    data      : dict   = Field(..., description="Updated workflow data")
    is_public : Optional[bool] = Field(None, description="Updated public status of the workflow")
    version: Optional[int] = None

    @field_validator("data")
    @classmethod
    def data_must_be_object(cls, v: dict) -> dict:
        if not isinstance(v, dict):
            raise ValueError("Updated workflow data must be a JSON object")
        return v


class WorkflowExecuteRequest(BaseModel):
    input_json: Dict[str, Any]  # Input JSON for workflow execution


class WorkflowExecuteResponse(BaseModel):
    message        : str              = Field(..., description="Execution message")
    result         : Dict[str, Any]   = Field(..., description="Execution result")
    execution_time : Optional[float] = Field(None, description="Execution time in seconds")
