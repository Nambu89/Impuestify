# Routers module __init__.py
from app.routers.auth import router as auth_router
from app.routers.payslips import router as payslips_router

__all__ = ["auth_router", "payslips_router"]