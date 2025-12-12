from fastapi import APIRouter,HTTPException,Depends
from typing import List
from utils.bigquery_service import call_procedure
from schemas.billing import Usage
from google.cloud import bigquery
from typing import Optional
from datetime import date
from models.tenant import Tenant
from dependencies import requires_tenant
from utils.ip_verifier import verify_ip

router = APIRouter()

@router.get("/{tenant_id}", response_model=List[Usage])
async def get_usage_tenant(
    
    month: Optional[date] = None, 
    tenant: Tenant = Depends(requires_tenant),
    _: bool = Depends(verify_ip)          
):
    rows = await call_procedure(
        "get_tenant_total_cost_dynamic_by_tenant",
        [bigquery.ScalarQueryParameter("in_tenant_id", "STRING", tenant.id)]
    )
    if not rows:
        raise HTTPException(404, "No usage found for this tenant")

    if month:
        
        rows = [r for r in rows if r["usage_month"] == month]

    return rows