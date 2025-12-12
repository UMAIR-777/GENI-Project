from fastapi import APIRouter, HTTPException,Depends,status
from typing import List
from google.cloud import bigquery
from utils.bigquery_service import call_procedure
from schemas.billing import TenantInfo, TenantInfoCreate, TenantInfoUpdate
from models.tenant import Tenant
from dependencies import requires_tenant
from utils.ip_verifier import verify_ip
router = APIRouter()

@router.get("/", response_model=TenantInfo)
async def get_tenant_info(
    tenant: Tenant = Depends(requires_tenant),
    _: bool = Depends(verify_ip)
    ):
    rows = await call_procedure(
        "get_tenant_info_by_id",
        [bigquery.ScalarQueryParameter("in_tenant_id", "STRING", tenant.id)]
    )
    if rows:
        return rows[0]
    raise HTTPException(status_code=404, detail="Tenant billing information doesnot exist")

@router.post("/", response_model=TenantInfo)
async def create_tenant(
    info: TenantInfoCreate,
    tenant: Tenant = Depends(requires_tenant),
    _: bool = Depends(verify_ip) 
    ):
    # 1) Check BigQuery if tenant_info already exists
    existing = await call_procedure(
        "get_tenant_info_by_id",
        [bigquery.ScalarQueryParameter("in_tenant_id", "STRING", tenant.id)]
    )
    if existing:
        # 2) If any row returned, refuse to create again
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant billing info already exists"
        )
    await call_procedure(
        "create_tenant_info",
        [
            bigquery.ScalarQueryParameter("in_tenant_id", "STRING", tenant.id),
            bigquery.ScalarQueryParameter("in_plan_id", "STRING", info.plan_id),
            bigquery.ScalarQueryParameter("in_credits_purchased", "FLOAT64", info.credits_purchased),
            bigquery.ScalarQueryParameter("in_spend_cap_enabled", "BOOL", info.spend_cap_enabled),
            bigquery.ScalarQueryParameter("in_billing_email", "STRING", tenant.email),
            bigquery.ScalarQueryParameter("in_billing_address", "STRING", info.billing_address),
            bigquery.ScalarQueryParameter("in_tax_id", "STRING", info.tax_id),
            bigquery.ScalarQueryParameter("in_payment_method", "STRING", info.payment_method),
        ]
    )
    return TenantInfo(
        tenant_id=tenant.id,
        plan_id=info.plan_id,
        credits_purchased=info.credits_purchased,
        spend_cap_enabled=info.spend_cap_enabled,
        billing_email=tenant.email,
        billing_address=info.billing_address,
        tax_id=info.tax_id,
        payment_method=info.payment_method,
    )

@router.put("/", response_model=TenantInfo)
async def update_tenant(
    info: TenantInfoUpdate,
    tenant: Tenant = Depends(requires_tenant),
    _: bool = Depends(verify_ip) 
    ):
    await call_procedure(
        "update_tenant_info",
        [
            bigquery.ScalarQueryParameter("in_tenant_id", "STRING", tenant.id),
            bigquery.ScalarQueryParameter("in_plan_id", "STRING", info.plan_id),
            bigquery.ScalarQueryParameter("in_credits_purchased", "FLOAT64", info.credits_purchased),
            bigquery.ScalarQueryParameter("in_spend_cap_enabled", "BOOL", info.spend_cap_enabled),
            bigquery.ScalarQueryParameter("in_billing_email", "STRING", tenant.email),
            bigquery.ScalarQueryParameter("in_billing_address", "STRING", info.billing_address),
            bigquery.ScalarQueryParameter("in_tax_id", "STRING", info.tax_id),
            bigquery.ScalarQueryParameter("in_payment_method", "STRING", info.payment_method),
        ]
    )
    return TenantInfo(
        tenant_id=tenant.id,
        plan_id=info.plan_id,
        credits_purchased=info.credits_purchased,
        spend_cap_enabled=info.spend_cap_enabled,
        billing_email=tenant.email,
        billing_address=info.billing_address,
        tax_id=info.tax_id,
        payment_method=info.payment_method,
    )

@router.delete("/", response_model=dict)
async def delete_tenant(
    tenant: Tenant = Depends(requires_tenant),
    _: bool = Depends(verify_ip)
):
    await call_procedure(
        "delete_tenant_info",
        [bigquery.ScalarQueryParameter("in_tenant_id", "STRING", tenant.id)]
    )
    return {"tenant info deleted": tenant.id}

