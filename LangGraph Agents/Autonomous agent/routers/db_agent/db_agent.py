import json
import os
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.params import Body
from fastapi.responses import JSONResponse
from pydantic import create_model
from sqlalchemy.orm import Session
from database.session import get_db
from database_agent.sql_writter.generation import run_generation_workflow
from database_agent.sql_writter.planning import run_planning_workflow
from dependencies.authorization import requires_tenant
from typing import List, Optional

from models.tenant import Tenant
from schemas.db_agent import *
from utils.db_agent import dynamic_handler, read_json_file
from utils.ip_verifier import verify_ip

from utils.config import DG_AGENT_JSON_PATH

router = APIRouter()

@router.get("/", summary="Return JSON group data")
async def create_group(
    tenant: Tenant = Depends(requires_tenant),
    db: Session = Depends(get_db),
    _: bool = Depends(verify_ip)
):
    file_path = DG_AGENT_JSON_PATH
    
    try:
        content = read_json_file(file_path)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "tenant": tenant.id,
                "data": content,
                "message": "Group data loaded successfully"
            }
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requested group data file not found"
        )
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to parse JSON data"
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {str(err)}"
        )

@router.post("/planning", response_model=PlanningResponse, summary="Run BDD planning workflow")
async def plan_bdd(
    payload: InputBDD = Body(..., description="Planning input payload"),
    tenant=Depends(requires_tenant),
    db: Session = Depends(get_db),
    _: bool = Depends(verify_ip)
) -> PlanningResponse:
    
    # invoke planning workflow
    planning_data = run_planning_workflow(
        payload.bdd, workflow_id="pass by myself", tenant_id=tenant.id
    )
    result = PlanningResult(
        logical_design=planning_data["logical_design"],
        bdd_scenario=planning_data["bdd_scenario"]
    )
    message = (
        "Planning completed. To generate BDD outputs, POST to `/bdd/generation` with the planning result."
    )
    return PlanningResponse(planning_result=result, message=message)

@router.post("/generation", response_model=GenerationResponse, summary="Run BDD generation workflow")
async def generate_bdd(
    payload: GenerationRequest = Body(..., description="Generation input payload"),
    tenant=Depends(requires_tenant),
    db: Session = Depends(get_db),
    _: bool = Depends(verify_ip)
) -> GenerationResponse:

    gen_data = run_generation_workflow(
        logical_design=payload.logical_design,
        bdd_scenario=payload.bdd_scenario,
        workflow_id="workflow_id_db_agent",
        tenant_id=tenant.id
    )
    gen_result = GenerationResult(generated_output=gen_data["generated_output"])
    return GenerationResponse(generation_result=gen_result)

@router.post("/procedures/execute", response_model=BatchProcedureResponse)
async def execute_procedures(
    tenant: Tenant = Depends(requires_tenant),
    db: Session = Depends(get_db),
    _: bool = Depends(verify_ip),
    call: List[ProcedureCall] = Body(..., description="List of procedure definitions and inputs")
) -> BatchProcedureResponse:
    
    results: List[ProcedureExecutionResult] = []
    try:
        # hilal will provide the multi-procedure
        return BatchProcedureResponse
    except Exception as e:
        raise HTTPException(500, detail={"procedure": call.procedure, "error": str(e)})

@router.post(f"/procedure/execute", response_model=ProcedureExecutionResult)
async def execute_procedure(
    tenant: Tenant = Depends(requires_tenant),
    db: Session = Depends(get_db),
    _: bool = Depends(verify_ip),
    call: ProcedureCall = Body(..., description="Procedure definition and inputs")
) -> ProcedureExecutionResult:
    
    try:
        SQL_TO_PYTHON = {
            "TEXT": str,
            "VARCHAR": str,
            "UUID": str,
            "INTEGER": int,
            "INT": int,
            "FLOAT": float,
            "BOOLEAN": bool,
            "TIMESTAMP": str,
            "JSONB": dict
        }

        for proc in call:
            proc_name = proc["procedure"]
            description = proc["description"]
            inputs = proc["inputs"]


            fields = {
                param["name"]: (SQL_TO_PYTHON[param["type"].upper()], ...)
                for param in inputs
            }
            InputModel = create_model(f"{proc_name}_Input", **fields)
            exec_res = dynamic_handler(InputModel, proc)
        return ProcedureExecutionResult(procedure=call.procedure, description=description,result=exec_res)
    except Exception as e:
        raise HTTPException(500, detail={"procedure": call.procedure, "error": str(e)})
    