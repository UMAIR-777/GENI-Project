from fastapi import Depends, HTTPException, status
from models.association      import user_group
from models.tenant           import Tenant
from models.user            import User
from models.group           import Group
from models.workflow         import Workflow
from models.ip_address       import IPAddress
from models.token_blacklist  import TokenBlacklist
from models.otp_verification import OTPVerification
from typing import Annotated, Union
from .dependency_injections import (
    get_current_tenant,
    get_account_details,
    get_current_user,
    get_tenant_or_team_member
)

def requires_tenant(tenant: Tenant = Depends(get_current_tenant)):
    if tenant.role != "tenant":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    return tenant

def requires_user(user: User = Depends(get_current_user)):
    if user.role not in ["client", "team_member"]:  # Fixed User.role -> user.role
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    return user

def requires_tenant_or_team_member(account: Union[Tenant, User] = Depends(get_tenant_or_team_member)):    
    valid_roles = ["tenant", "team_member"] 
    if account.role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient privileges for this operation"
        )
    return account

def requires_tenant_or_team_member_or_client(account: Union[Tenant, User] = Depends(get_account_details)):
    valid_roles = ["tenant", "team_member", "client"] 
    if account.role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient privileges for this operation"
        )
    return account