# ============================ Imports ============================

from fastapi                 import APIRouter, Depends, HTTPException, status
from fastapi.responses       import JSONResponse
from sqlalchemy              import text
from sqlalchemy.orm          import Session
from sqlalchemy.exc          import SQLAlchemyError

from database.session        import get_db
from models.tenant           import Tenant
from schemas.group           import GroupCreate, GroupResponse, GroupSpecificWorkflow
from dependencies            import requires_tenant
from utils.ip_verifier       import verify_ip
from utils.generate_uuid     import generate_uuid

import logging


# =========================== Logger & Router ===========================

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================ Endpoints ============================

@router.post("/", response_model=GroupResponse)
async def create_group(
    group_data : GroupCreate,
    tenant     : Tenant  = Depends(requires_tenant),
    db         : Session = Depends(get_db),
    _          : bool    = Depends(verify_ip)
) -> GroupResponse:
    try:
        exists = db.execute(
            text("SELECT fn_check_group_exists(:name, :tenant_id)"),
            {
                "name"     : group_data.name,
                "tenant_id": tenant.id
            }
        ).scalar()

        if exists:
            raise HTTPException(
                status_code = status.HTTP_400_BAD_REQUEST,
                detail      = "Group name already exists"
            )

        group_id = generate_uuid()

        db.execute(
            text("CALL sp_create_group(:id, :name, :tenant_id)"),
            {
                "id"       : group_id,
                "name"     : group_data.name,
                "tenant_id": tenant.id
            }
        )
        db.commit()

        return GroupResponse(id=group_id, name=group_data.name)

    except SQLAlchemyError as db_err:
        logger.error(f"[create_group] database error: {db_err}")
        db.rollback()
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail      = "Internal error while creating group"
        )

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception(f"[create_group] unexpected error: {exc}")
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail      = "Unexpected error occurred"
        )


@router.get("/allgroups", response_model=list[GroupResponse])
async def get_all_groups(
    tenant: Tenant = Depends(requires_tenant),
    db    : Session = Depends(get_db),
    _     : bool    = Depends(verify_ip)
):
    
    
    rows = db.execute(
            text("SELECT * FROM fn_get_all_groups(:tenant_id)"),
            {"tenant_id": tenant.id}
        ).fetchall()
        
    return [GroupResponse(**r._asdict()) for r in rows]
    

@router.get("/{group_id}/get-group-workflow", response_model=list[GroupSpecificWorkflow])
async def get_group_workflows(
    group_id: str,
    tenant  : Tenant = Depends(requires_tenant),
    db      : Session = Depends(get_db),
    _       : bool    = Depends(verify_ip)
):
    exists = db.execute(
        text("SELECT fn_check_group_by_id(:id, :tenant_id)"),
        {
            "id"       : group_id,
            "tenant_id": tenant.id
        }
    ).scalar()

    if not exists:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail      = "Group not found"
        )

    rows = db.execute(
        text("SELECT * FROM fn_get_group_workflows(:group_id, :tenant_id)"),
        {
            "group_id" : group_id,
            "tenant_id": tenant.id
        }
    ).fetchall()

    return [GroupSpecificWorkflow(**r._asdict()) for r in rows]
        
@router.post("/{group_id}/add-user/{user_id}", status_code=status.HTTP_200_OK)
async def assign_user_to_group(
    group_id: str,
    user_id : str,
    tenant  : Tenant = Depends(requires_tenant),
    db      : Session = Depends(get_db),
    _       : bool    = Depends(verify_ip)
):
    db.execute(
        text("CALL sp_assign_user_to_group(:user_id, :group_id, :tenant_id)"),
        {
            "user_id"  : user_id,
            "group_id" : group_id,
            "tenant_id": tenant.id
        }
    )
    db.commit()

    return JSONResponse(
        status_code = status.HTTP_200_OK,
        content     = {"message": f"User {user_id} added to group {group_id}"}
    )


@router.post("/{group_id}/add-workflow/{workflow_id}", status_code=status.HTTP_200_OK)
async def assign_workflow_to_group(
    group_id   : str,
    workflow_id: str,
    tenant     : Tenant = Depends(requires_tenant),
    db         : Session = Depends(get_db),
    _          : bool    = Depends(verify_ip)
):
    db.execute(
        text("CALL sp_assign_workflow_to_group(:workflow_id, :group_id, :tenant_id)"),
        {
            "workflow_id": workflow_id,
            "group_id"   : group_id,
            "tenant_id"  : tenant.id
        }
    )
    db.commit()

    return JSONResponse(
        status_code = status.HTTP_200_OK,
        content     = {"message": f"Workflow {workflow_id} added to group {group_id}"}
    )


@router.delete("/{group_id}/remove-workflow/{workflow_id}", status_code=status.HTTP_200_OK)
async def remove_workflow_from_group(
    group_id   : str,
    workflow_id: str,
    tenant     : Tenant = Depends(requires_tenant),
    db         : Session = Depends(get_db),
    _          : bool    = Depends(verify_ip)
):
    db.execute(
        text("CALL sp_remove_workflow_from_group(:workflow_id, :group_id, :tenant_id)"),
        {
            "workflow_id": workflow_id,
            "group_id"   : group_id,
            "tenant_id"  : tenant.id
        }
    )
    db.commit()

    return JSONResponse(
        status_code = status.HTTP_200_OK,
        content     = {"message": f"Workflow {workflow_id} removed from group {group_id}"}
    )


@router.delete("/{group_id}", status_code=status.HTTP_200_OK)
async def delete_group(
    group_id: str,
    tenant  : Tenant  = Depends(requires_tenant),
    db      : Session = Depends(get_db),
    _       : bool    = Depends(verify_ip)
):
    db.execute(
        text("CALL sp_delete_group(:group_id, :tenant_id)"),
        {
            "group_id" : group_id,
            "tenant_id": tenant.id
        }
    )
    db.commit()

    return JSONResponse(
        status_code = status.HTTP_200_OK,
        content     = {"message": f"Group {group_id} deleted"}
    )
