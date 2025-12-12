# routers/user.py
import json
from fastapi            import APIRouter, Depends, HTTPException, status
from fastapi.responses  import Response
from sqlalchemy         import text
from sqlalchemy.orm     import Session

from database.session   import get_db
from models.tenant      import Tenant
from schemas.user       import (
                            UserCreate,
                            UserResponse,
                            UserDetailResponse,
                            AssignWorkflowAccessRequest,
                            UserUpdate,
                        )
from dependencies       import requires_tenant
from utils              import ip_verifier, email_sender, security, generate_uuid

router = APIRouter()
def parse_json_column(val):
    if val is None:
        return []
    if isinstance(val, str):
        return json.loads(val)
    return val

@router.post(
          "", 
          response_model =  UserResponse, 
          status_code    =  status.HTTP_201_CREATED)
async def create_user(
    user_data   : UserCreate,
    tenant      : Tenant    = Depends(requires_tenant),
    db          : Session   = Depends(get_db),
    _           : bool      = Depends(ip_verifier.verify_ip),
):
    
    
    exists_email = db.execute(
        text(
             "SELECT * FROM fn_check_user_email_exists(:email, :tenant_id)"),
            {
                "email"     : user_data.email, 
                "tenant_id" : tenant.id
            },
    ).scalar()
    
    if exists_email:
        raise HTTPException(
            status_code =   status.HTTP_400_BAD_REQUEST,
            detail      =   "Email already exists",
        )

    
    user_id = generate_uuid.generate_uuid()
    
    db.execute(
            text("CALL sp_create_user(:id, :name, :email, :password_hash, :tenant_id, :role)"),
            {
                "id"            : user_id,
                "name"          : user_data.name,
                "email"         : user_data.email,
                "password_hash" : security.get_password_hash(user_data.password),
                "tenant_id"     : tenant.id,
                "role"          : user_data.role,
            },
        )
        
    
    
    for group_id in user_data.group_ids:
        
            db.execute(
                text("CALL sp_assign_user_to_group(:user_id, :group_id, :tenant_id)"),
                {   
                    "user_id"   : user_id, 
                    "group_id"  : group_id, 
                    "tenant_id" : tenant.id
                },
            )
        
    db.commit()

    tenant_name = db.execute(
            text("SELECT name FROM tenants WHERE id = :tid"), 
            {
                "tid"   : tenant.id
            }
        ).scalar()
        
    if tenant_name:
            
            email_sender.send_creds_to_users(
                user_data.email, 
                user_data.password, 
                tenant_name
            )
    else:
            print(f"Warning: Tenant name not found for ID: {tenant.id}")
    
    
    
    return UserResponse(
        id          =   user_id, 
        email       =   user_data.email, 
        role        =   user_data.role, 
        is_active   =   True
    )
    
    

@router.get(
          "", 
          response_model=list[UserResponse]
          )
async def get_all_users(
    tenant  : Tenant    = Depends(requires_tenant),
    db      : Session   = Depends(get_db),
    _       : bool      = Depends(ip_verifier.verify_ip),
):
    rows = db.execute(
        text("SELECT * FROM fn_get_all_users(:tenant_id)"),
        {
            "tenant_id" : tenant.id
        },
    ).fetchall()
    
    return  [
                UserResponse
                (
                    id          =   row.id, 
                    email       =   row.email, 
                    role        =   row.role, 
                    is_active   =   row.is_active
                ) 
                for row in rows
            ]


@router.get(
    "/{user_id}",
    response_model  =   UserDetailResponse
)
async def get_user_details(
    user_id : str,
    tenant  : Tenant    = Depends(requires_tenant),
    db      : Session   = Depends(get_db),
    _       : bool      = Depends(ip_verifier.verify_ip),
):
    
    row = db.execute(
        text("SELECT * FROM fn_get_user_details(:user_id, :tenant_id)"),
        {
            "user_id"   : user_id, 
            "tenant_id" : tenant.id
        },
    ).first()

    if not row:
        raise HTTPException(
            status_code =   status.HTTP_404_NOT_FOUND,
            detail      =   "User not found"
        )

    
    data = row._asdict()

    
    data["groups"]    = parse_json_column(data.get("groups"))
    data["workflows"] = parse_json_column(data.get("workflows"))

    
    return data


@router.patch(
          "/{user_id}", 
          response_model=UserResponse)
async def update_user(
    user_id : str,
    update  : UserUpdate,
    tenant  : Tenant    = Depends(requires_tenant),
    db      : Session   = Depends(get_db),
    _       : bool      = Depends(ip_verifier.verify_ip),
):
    db.execute(
        text("CALL sp_update_user(:user_id, :email, :role, :is_active, :tenant_id)"),
        {
            "user_id"   : user_id,
            "email"     : update.email,
            "role"      : update.role,
            "is_active" : update.is_active,
            "tenant_id" : tenant.id,
        },
    )
    
    db.commit()
    
    row = db.execute(
        text("SELECT * FROM fn_get_user_details(:user_id, :tenant_id)"),
        {
            "user_id"   : user_id, 
            "tenant_id" : tenant.id
        },
    ).first()
    
    if not row:
        raise HTTPException(
            status_code     =   status.HTTP_404_NOT_FOUND, 
            detail          =   "User not found"
        )
    
    return UserResponse(
         id         =   row.id, 
         email      =   row.email, 
         role       =   row.role, 
         is_active  =   row.is_active)


@router.post(
          "/{user_id}/assign-workflow-access", 
          status_code=status.HTTP_204_NO_CONTENT
          )
async def assign_workflow_access(
    user_id         : str,
    workflow_data   : AssignWorkflowAccessRequest,
    tenant          : Tenant    = Depends(requires_tenant),
    db              : Session   = Depends(get_db),
    _               : bool      = Depends(ip_verifier.verify_ip),
):
    valid = db.execute(
        text("SELECT * FROM fn_validate_workflow_access(:user_id, :tenant_id, :wf_ids)"),
        {
            "user_id"   : user_id,
            "tenant_id" : tenant.id,
            "wf_ids"    : workflow_data.workflow_ids,
        },
    ).scalar()
    
    if not valid:
        raise HTTPException(
            status_code =   status.HTTP_400_BAD_REQUEST,
            detail      =   "Invalid workflow access assignment",
        )

    for workflow_id in workflow_data.workflow_ids:
        db.execute(
            text("CALL sp_assign_workflow_access(:user_id, :wf_id, :tenant_id)"),
            {
                "user_id"   : user_id, 
                "wf_id"     : workflow_id, 
                "tenant_id" : tenant.id
            },
        )
    
    db.commit()
    return Response(
         status_code    =   status.HTTP_204_NO_CONTENT
        )


@router.delete(
          "/{user_id}", 
          status_code=status.HTTP_204_NO_CONTENT
          )
async def delete_user(
    user_id : str,
    tenant  : Tenant    = Depends(requires_tenant),
    db      : Session   = Depends(get_db),
    _       : bool      = Depends(ip_verifier.verify_ip),
):
    db.execute(
        text("CALL sp_delete_user(:user_id, :tenant_id)"),
        {
            "user_id"   : user_id, 
            "tenant_id" : tenant.id
        },
    )
    
    db.commit()
    return Response(
         status_code    =   status.HTTP_204_NO_CONTENT
        )