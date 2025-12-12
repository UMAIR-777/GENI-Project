# ============================ Imports ============================
from datetime            import datetime
from typing              import Any, Dict, List, Optional
from pydantic            import BaseModel, Field


# ============================ Schemas =============================
feature: str
scenario_details: Dict[str, Any]

class PlanningResult(BaseModel):
    logical_design: str
    bdd_scenario: str

class GenerationResult(BaseModel):
    generated_output: str

class BDDResponse(BaseModel):
    planning_result: Optional[PlanningResult] = None
    generation_result: Optional[GenerationResult] = None
    message: Optional[str] = None

class ProcedureInput(BaseModel):
    name: str
    type: str
    description: str
    value: Any

class ProcedureCall(BaseModel):
    procedure: str
    description: str
    inputs: List[ProcedureInput]
    returns: Optional[Any] = None
    side_effects: Optional[str] = None

class ProcedureExecutionResult(BaseModel):
    procedure: str
    description: str
    result: Any

class BatchProcedureResponse(BaseModel):
    tenant_id: str
    results: List[ProcedureExecutionResult]

class InputBDD(BaseModel):
    # Define the fields of your BDD input
    feature: str
    scenario_details: Dict[str, Any]

class PlanningResult(BaseModel):
    logical_design: str
    bdd_scenario: str

class GenerationResult(BaseModel):
    generated_output: str

class BDDResponse(BaseModel):
    planning_result: Optional[PlanningResult] = None
    generation_result: Optional[GenerationResult] = None
    message: Optional[str] = None

class InputBDD(BaseModel):
    bdd: str = Field(..., description="Name of the feature")

class PlanningRequest(BaseModel):
    input: InputBDD

class PlanningResult(BaseModel):
    logical_design: str = Field(..., description="Logical design generated during planning")
    bdd_scenario: str = Field(..., description="BDD scenario outlining Given/When/Then steps")

class PlanningResponse(BaseModel):
    planning_result: PlanningResult
    message: Optional[str] = Field(
        None,
        description="Message for next steps, e.g., to invoke generation endpoint"
    )

class GenerationRequest(BaseModel):
    logical_design: str = Field(..., description="Logical design from planning phase")
    bdd_scenario: str = Field(..., description="BDD scenario from planning phase")

class GenerationResult(BaseModel):
    generated_output: str = Field(..., description="Final generated output based on the design and scenario")

class GenerationResponse(BaseModel):
    generation_result: GenerationResult
