from fastapi import APIRouter,Depends
from typing import List
from utils.bigquery_service import call_procedure
from schemas.billing import Plan
from models.tenant import Tenant
from dependencies import requires_tenant
from utils.ip_verifier import verify_ip
router = APIRouter()

@router.get("/", response_model=List[Plan])
async def get_plans(
    tenant: Tenant = Depends(requires_tenant),
    _: bool = Depends(verify_ip)
):
    return await call_procedure("get_plans")
