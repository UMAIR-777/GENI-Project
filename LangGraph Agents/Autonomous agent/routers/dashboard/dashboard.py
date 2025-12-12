# dashboard.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi.responses import JSONResponse

from database.session import get_db
from dependencies.authorization import requires_tenant, requires_user
from models.group import Group
from models.tenant import Tenant
from models.user import User
from schemas.dashboard import AdminDashboardStats, DashboardUserStatus
from utils.ip_verifier import verify_ip

router = APIRouter()

@router.get("/user", response_model=DashboardUserStatus)
async def get_user_dashboard(
    user: User = Depends(requires_user),
    db: Session = Depends(get_db),
    _: bool = Depends(verify_ip)
):
    if user.role != "tenant":
        # collect the list of group IDs this user belongs to
        group_ids: List[str] = [g.id for g in user.groups]

        # call stored function to get workflow count
        result = db.execute(
            text("""
                SELECT get_user_workflow_count(:tenant_id, :group_ids) AS count
            """),
            {"tenant_id": user.tenant_id, "group_ids": group_ids}
        ).first()
        workflow_count = result.count if result else 0

        return {
            "email": user.email,
            "role": user.role,
            "groups": [g.name for g in user.groups],
            "workflow_count": workflow_count
        }

    # if somehow a tenant gets here, reject
    raise HTTPException(status_code=403, detail="Tenants cannot access the user dashboard")

@router.get("/tenant", response_model=AdminDashboardStats)
async def get_tenant_dashboard(
    tenant: Tenant = Depends(requires_tenant),
    db: Session = Depends(get_db),
    _: bool = Depends(verify_ip)
):
    # total users
    total_users = db.execute(
        text("SELECT get_total_users(:tenant_id)"),
        {"tenant_id": tenant.id}
    ).scalar()

    # total groups
    total_groups = db.execute(
        text("SELECT get_total_groups(:tenant_id)"),
        {"tenant_id": tenant.id}
    ).scalar()

    # total workflows
    total_workflows = db.execute(
        text("SELECT get_total_workflows(:tenant_id)"),
        {"tenant_id": tenant.id}
    ).scalar()

    # workflows by group
    rows = db.execute(
        text("SELECT * FROM get_workflows_by_group(:tenant_id)"),
        {"tenant_id": tenant.id}
    ).all()
    workflows_by_group = {row.group_name: row.workflow_count for row in rows}

    return {
        "tenant_id": tenant.id,
        "tenant_name": tenant.name,
        "tenant_email": tenant.email,
        "total_users": total_users,
        "total_groups": total_groups,
        "total_workflows": total_workflows,
        "workflows_by_group": workflows_by_group
    }
