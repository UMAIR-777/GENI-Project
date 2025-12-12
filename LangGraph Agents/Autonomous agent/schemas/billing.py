from datetime import date
from pydantic import BaseModel, EmailStr,Field
from typing import Optional

from enum import Enum

class AddonCatalogItem(BaseModel):
    CostDimension: str
    Type: str
    Unit: str
    PerCount: float
    BaseCost: float
    
class TenantAddons(BaseModel):
    tenant_id: str
    CostDimension: str
    Type: str
    Unit: str
    PerCount: float
    BaseCost: float
    IncludedUsage: float
    ActualUsage: float
    OverageUnits: float
    OverageCost: float
    
class InvoiceStatus(str, Enum):
    PAID = "PAID"
    PENDING = "PENDING"
    FAILED = "FAILED"

class Invoice(BaseModel):
    invoice_id: str
    tenant_id: str
    billing_period: date
    credits_used: float
    total_due: float
    invoice_status: InvoiceStatus
    pdf_link: Optional[str]

class OverageInvoice(BaseModel):
    invoice_id: str
    tenant_id: str
    billing_period: date
    total_cost_overages: float
    invoice_status: InvoiceStatus
    pdf_link: Optional[str]

class Plan(BaseModel):
    plan_id: str
    monthly_cost: float
    included_token_in: float
    overage_token_in: float
    included_token_out: float
    overage_token_out: float
    included_db_disk: float
    overage_db_disk: float
    included_storage_disk: float
    overage_storage_disk: float
    included_db_cpu_hours: float
    overage_db_cpu_hours: float
    included_workflow_cpu_hours: float
    overage_workflow_cpu_hours: float
    included_gpu_hours: float
    overage_gpu_hours: float
    included_ingress: float
    overage_ingress: float
    included_egress: float
    overage_egress: float

class TenantInfo(BaseModel):
    tenant_id: str
    plan_id: str
    credits_purchased: float
    spend_cap_enabled: bool
    billing_email: EmailStr | None
    billing_address: str | None
    tax_id: str | None
    payment_method: str | None

class TenantInfoCreate(BaseModel):
    plan_id: str
    credits_purchased: float = 0
    spend_cap_enabled: bool = True
    billing_email: EmailStr | None = None
    billing_address: str | None = None
    tax_id: str | None = None
    payment_method: str | None

class TenantInfoUpdate(BaseModel):
    plan_id: str
    credits_purchased: float
    spend_cap_enabled: bool
    billing_email: EmailStr | None
    billing_address: str | None
    tax_id: str | None
    payment_method: str | None

class Usage(BaseModel):
    tenant_id: str
    usage_month: date
    cost_dimension: str
    base_cost: float
    plan_limits: Optional[float]
    actual_usage: float
    pro_rate_expected: float
    budget_remain: float
    daily_rate: float
    projected_usage: float
    projected_overage: float
    projected_over_date: float
    total_projected_overage_cost: float


