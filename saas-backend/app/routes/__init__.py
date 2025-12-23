# Routes
from .auth import router as auth_router
from .beverages import router as beverages_router
from .machines import router as machines_router
from .sales import router as sales_router
from .consumptions import router as consumptions_router
from .dashboard import router as dashboard_router
from .health import router as health_router
from .stocks import router as stocks_router

__all__ = [
    "auth_router",
    "beverages_router",
    "machines_router", 
    "sales_router",
    "consumptions_router",
    "dashboard_router",
    "health_router",
    "stocks_router",
]
