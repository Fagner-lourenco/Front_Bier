# Schemas
from .organization import OrganizationCreate, OrganizationUpdate, OrganizationResponse
from .user import UserCreate, UserUpdate, UserResponse, UserLogin, Token
from .machine import MachineCreate, MachineUpdate, MachineResponse
from .beverage import BeverageCreate, BeverageUpdate, BeverageResponse, BeverageListResponse
from .sale import SaleCreate, SaleResponse, SaleDetailResponse
from .consumption import ConsumptionCreate, ConsumptionResponse, ConsumptionDetailResponse
from .dashboard import DashboardMetrics, PeriodMetrics, BeverageMetrics, MachineMetrics

__all__ = [
    "OrganizationCreate", "OrganizationUpdate", "OrganizationResponse",
    "UserCreate", "UserUpdate", "UserResponse", "UserLogin", "Token",
    "MachineCreate", "MachineUpdate", "MachineResponse",
    "BeverageCreate", "BeverageUpdate", "BeverageResponse", "BeverageListResponse",
    "SaleCreate", "SaleResponse", "SaleDetailResponse",
    "ConsumptionCreate", "ConsumptionResponse", "ConsumptionDetailResponse",
    "DashboardMetrics", "PeriodMetrics", "BeverageMetrics", "MachineMetrics",
]
