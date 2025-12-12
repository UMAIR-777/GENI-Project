from fastapi import APIRouter,HTTPException,Depends
from typing import List
from utils.bigquery_service import call_procedure
from schemas.billing import TenantAddons,AddonCatalogItem
from google.cloud import bigquery
from models.tenant import Tenant
from dependencies import requires_tenant
from utils.ip_verifier import verify_ip
router = APIRouter()

@router.get("/", response_model=List[AddonCatalogItem])
async def get_addons_catalog(
    tenant: Tenant = Depends(requires_tenant),
    _: bool = Depends(verify_ip)
):
    return await call_procedure("get_addon_catalog")



@router.get("/{tenant_id}", response_model=List[TenantAddons])
async def get_tenant(
    tenant: Tenant = Depends(requires_tenant),
    _: bool = Depends(verify_ip)
):
    rows = await call_procedure(
        "get_tenant_addons_cost_by_tenant",
        [bigquery.ScalarQueryParameter("in_tenant_id", "STRING", tenant.id)]
    )
    if rows:
        return rows
    raise HTTPException(status_code=404, detail="No Addons found for this tenant")
