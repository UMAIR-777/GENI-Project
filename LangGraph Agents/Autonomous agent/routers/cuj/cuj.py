from fastapi import APIRouter, Body, Depends, HTTPException, Query
from typing import Any, Optional, Dict
import os
import logging
import asyncio
from utils.ip_verifier import verify_ip
from database.session import get_db
# Import the schema models
from schemas.cuj import (
    AnalysisData, 
    CompetitorAnalysis, 
    SegmentationData, 
    MarketFitData, 
    CUJData, 
    FeatureFile,
    ProjectMetadata,
    JsonResponse,
    StrategyInput
)

from utils.cuj import *
from sqlalchemy.orm import Session
from models.tenant           import Tenant
from dependencies            import requires_tenant
# Configure logging
logger = logging.getLogger("cuj_router")

router = APIRouter()

os.makedirs(OUTPUT_DIR, exist_ok=True)
workflow_config = get_workflow_config()

# Endpoint to execute the full CUJ workflow
@router.post("/projects/execute")
def execute_full_workflow(
    strategy_input_data: StrategyInput,
    tenant     : Tenant  = Depends(requires_tenant),
    db: Session = Depends(get_db),
    _ip: bool = Depends(verify_ip)
    
):
    tenant_id = str(tenant.id)
    
    logger.info(f"Starting workflow execution for tenant: {tenant_id}")
    
    try:
        from cuj_workflow.core.cuj_executor import CUJWorkflowExecutor
        
        # Save the prompt to start the workflow
        strategy_input = {
            "Prompt": strategy_input_data.Prompt,
            "Founder_Goal": strategy_input_data.Founder_Goal, 
            "Client_Type": strategy_input_data.Client_Type,
            "Revenue Model(s)": strategy_input_data.Revenue_Model,
            "tenant_id": tenant_id
        }
        
        # Ensure tenant output directory exists
        tenant_output_dir = os.path.join(OUTPUT_DIR, tenant_id)
        os.makedirs(tenant_output_dir, exist_ok=True)
        logger.info(f"Created/verified tenant output directory: {tenant_output_dir}")
        
        # Save the strategy input ONLY to the tenant directory
        save_result = save_to_json(strategy_input, "strategy_input.json", directory=tenant_output_dir)
        logger.info(f"Saved strategy input to tenant directory: {save_result}")
        
        logger.info(f"Initializing CUJWorkflowExecutor with output_dir={tenant_output_dir}")
        executor = CUJWorkflowExecutor(
            config_path=WORKFLOW_CONFIG_PATH,
            output_dir=tenant_output_dir
        )
        
        # Create a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Execute entire workflow
        logger.info("Starting workflow execution")
        result = loop.run_until_complete(executor.execute_workflow())
        logger.info(f"Workflow execution completed with result: {result}")
        
        loop.close()
        
        return {"status": "success", "tenant_id": tenant_id, "result": result}
    except Exception as e:
        logger.error(f"Error executing workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Get project metadata
@router.get("/project_json", response_model=JsonResponse)
def get_project_metadata(
    tenant: Tenant = Depends(requires_tenant),
    db: Session = Depends(get_db),
    _ip: bool = Depends(verify_ip)
):
    # Require tenant_id
    tenant_id = str(tenant.id)
    tenant_output_dir = os.path.join(OUTPUT_DIR, tenant_id)
    data = load_from_json("1extractproblemstatement_output.json", directory=tenant_output_dir)
    if data:
        return JsonResponse(root=data)
    return JsonResponse(root={"error": f"Project metadata not found for tenant {tenant_id}"})

# Get problem & business analysis
@router.get("/analysis", response_model=JsonResponse)
def get_analysis(
    tenant: Tenant = Depends(requires_tenant),
    db: Session = Depends(get_db),
    _ip: bool = Depends(verify_ip)
):
    # Require tenant_id
    tenant_id = str(tenant.id)
    tenant_output_dir = os.path.join(OUTPUT_DIR, tenant_id)
    data = load_from_json("2analysis_output.json", directory=tenant_output_dir)
    if data:
        return JsonResponse(root=data)
    return JsonResponse(root={"error": f"Analysis data not found for tenant {tenant_id}"})

# Get competitor analysis
@router.get("/competitor-analysis", response_model=JsonResponse)
def get_competitor_analysis(
    tenant: Tenant = Depends(requires_tenant),
    db: Session = Depends(get_db),
    _ip: bool = Depends(verify_ip)
):
    # Require tenant_id
    tenant_id = str(tenant.id)
    
    tenant_output_dir = os.path.join(OUTPUT_DIR, tenant_id)
    data = load_from_json("3competitoranalysis_output.json", directory=tenant_output_dir)
    if data:
        return JsonResponse(root=data)
    return JsonResponse(root={"error": f"Competitor analysis data not found for tenant {tenant_id}"})

# Get user & market segmentation
@router.get("/segmentation", response_model=JsonResponse)
def get_segmentation(

    tenant: Tenant = Depends(requires_tenant),
    db: Session = Depends(get_db),
    _ip: bool = Depends(verify_ip)
):
    # Require tenant_id
    tenant_id = str(tenant.id)
   
    tenant_output_dir = os.path.join(OUTPUT_DIR, tenant_id)
    data = load_from_json("4segmentationanalysis_output.json", directory=tenant_output_dir)
    if data:
        return JsonResponse(root=data)
    return JsonResponse(root={"error": f"Segmentation data not found for tenant {tenant_id}"})

# Get MVP & product-market fit
@router.get("/market-fit", response_model=JsonResponse)
def get_market_fit(
    tenant: Tenant = Depends(requires_tenant),
    db: Session = Depends(get_db),
    _ip: bool = Depends(verify_ip)
    ):
    # Require tenant_id
    tenant_id = str(tenant.id)
   
    tenant_output_dir = os.path.join(OUTPUT_DIR, tenant_id)
    data = load_from_json("5mvpfit_output.json", directory=tenant_output_dir)
    if data:
        return JsonResponse(root=data)
    return JsonResponse(root={"error": f"Market fit data not found for tenant {tenant_id}"})

# Get Critical User Journeys
@router.get("/cuj", response_model=JsonResponse)
def get_cuj(
    tenant: Tenant = Depends(requires_tenant),
    db: Session = Depends(get_db),
    _ip: bool = Depends(verify_ip)
    ):
    # Require tenant_id
    tenant_id = str(tenant.id)
   
    tenant_output_dir = os.path.join(OUTPUT_DIR, tenant_id)
    data = load_from_json("6cujgeneration_output.json", directory=tenant_output_dir)
    if data:
        return JsonResponse(root=data)
    return JsonResponse(root={"error": f"CUJ data not found for tenant {tenant_id}"})

# Get Gherkin BDD files
@router.get("/bdd", response_model=FeatureFile)
def get_bdd(
    tenant: Tenant = Depends(requires_tenant),
    db: Session = Depends(get_db),
    _ip: bool = Depends(verify_ip)
    ):
    # Require tenant_id
    tenant_id = str(tenant.id)
   
    tenant_output_dir = os.path.join(OUTPUT_DIR, tenant_id)
    file_path = os.path.join(tenant_output_dir, "cuj_bdd.feature")
    content = "Feature: Sample BDD"
    try:
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                content = f.read()
        else:
            content = f"No BDD feature file found for tenant {tenant_id}"
    except Exception as e:
        logger.error(f"Error reading BDD feature file: {e}")
    return FeatureFile(content=content)

# Get Technical architecture spec & diagrams
@router.get("/architecture", response_model=FeatureFile)
def get_architecture(
    tenant: Tenant = Depends(requires_tenant),
    db: Session = Depends(get_db),
    _ip: bool = Depends(verify_ip)
    ):
    # Require tenant_id
    tenant_id = str(tenant.id)
    
    tenant_output_dir = os.path.join(OUTPUT_DIR, tenant_id)
    file_path = os.path.join(tenant_output_dir, "architecture_feature.feature")
    content = "Feature: Architecture template"
    try:
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                content = f.read()
        else:
            content = f"No architecture feature file found for tenant {tenant_id}"
    except Exception as e:
        logger.error(f"Error reading architecture feature file: {e}")
    return FeatureFile(content=content) 