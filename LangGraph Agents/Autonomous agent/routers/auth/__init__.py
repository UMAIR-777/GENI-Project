from .login import router as login_router
from .logout import router as logout_router
from .otp_verification import router as otp_router

routers = [login_router, logout_router, otp_router]
