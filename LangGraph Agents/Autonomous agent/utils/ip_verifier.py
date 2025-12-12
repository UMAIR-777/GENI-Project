from fastapi            import Request, HTTPException, status, Depends
from sqlalchemy.orm     import Session
from dependencies       import get_current_user_email
from database.session   import get_db
from models.ip_address  import IPAddress

async def verify_ip(
        
        request: Request,
        user_email: str = Depends(get_current_user_email),
        db: Session = Depends(get_db)
        
        ) -> bool:
    
    client_ip = request.headers.get("X-Forwarded-For", request.client.host)
    if isinstance(client_ip, str) and "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()

    latest_login = (db.query(IPAddress)
                      .filter(IPAddress.email == user_email)
                      .order_by(IPAddress.created_at.desc())
                      .first())

    if not latest_login:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="No login record found")

    if latest_login.ip_address != client_ip:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="IP mismatch detected")

    return True