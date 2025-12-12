from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

# Node Agent Request
class WorkflowNodeAgentRequest(BaseModel):
    task: str = Field(..., description="Task description for the node agent")
    function_inputs: List[str] = Field(..., description="List of input parameters")
    function_output: str = Field(..., description="Output parameter")
    node_name: str = Field(..., description="Name for the new node")
    workflow_id: Optional[str] = Field(None, description="Associated workflow ID")



# Node Creation
class WorkflowNodeCreateRequest(BaseModel):
    name: str = Field(..., example="word-count")
    code: str = Field(..., example="def count_words(text):\n    return len(text.split())")
    input: list[str] = Field(..., example=["Hello world", "FastAPI is awesome"])
    output: list[str] = Field(..., example=["2", "3"])
    tags: list[str] = Field(..., example=["utility", "text-processing"])
    description: str = Field(..., example="Counts words in a given string.")

    spo: dict = Field(
        ...,
        example={"subject": "text", "predicate": "count", "object": "words"},
        description="Simple SPO metadata"
    )
    uri: str = Field(..., example="uri of node")







class WorkflowNodeCreateResponse(BaseModel):
    id: str
    name: str


# Node Responses
class WorkflowNodeResponse(BaseModel):
    id: str
    name: str
    uri: str
    node_metadata: Dict[str, Any]
    updated_at: datetime

class WorkflowNodeReadResponse(BaseModel):
    id: str
    name: str
    code_uri: str
    metadata: Dict[str, Any]

class WorkflowNodeListItem(BaseModel):
    id: str
    name: str
    code_uri: str
    metadata: Dict[str, Any]

class WorkflowNodeListResponse(BaseModel):
    nodes: List[WorkflowNodeListItem]

# Node Update
class WorkflowNodeUpdate(BaseModel):
    code: str
    input: List[str]
    output: List[str]
    tags: List[str]
    description: str
    spo: Dict[str, Any]
    uri: str  # mapped to node_metadata.code_uri

# Node Deletion
class WorkflowNodeDeleteResponse(BaseModel):
    message: str