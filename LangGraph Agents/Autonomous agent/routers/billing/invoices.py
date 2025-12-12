from fastapi import APIRouter,HTTPException,Depends
from typing import List
from utils.bigquery_service import call_procedure
from schemas.billing import OverageInvoice,Invoice
from google.cloud import bigquery
from models.tenant import Tenant
from dependencies import requires_tenant
from utils.ip_verifier import verify_ip
router = APIRouter()

@router.get("/monthly", response_model=List[Invoice])
async def get_tenant_monthly_invoices(
    tenant: Tenant = Depends(requires_tenant),
    _: bool = Depends(verify_ip) 
):
    rows = await call_procedure(
        "get_monthly_invoices_by_tenant",
        [bigquery.ScalarQueryParameter("tenant_id_param", "STRING", tenant.id)]
    )
    if rows:
        return rows
    raise HTTPException(status_code=404, detail="No monthly invoices found for this tenant")



@router.get("/overage", response_model=List[OverageInvoice])
async def get_tenant_overage_invoices(
    tenant: Tenant = Depends(requires_tenant),
    _: bool = Depends(verify_ip)
):
    rows = await call_procedure(
        "get_overage_invoices_by_tenant",
        [bigquery.ScalarQueryParameter("tenant_id_param", "STRING", tenant.id)]
    )
    if rows:
        return rows
    raise HTTPException(status_code=404, detail="No overage invoices found for this tenant")
