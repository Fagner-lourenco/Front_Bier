"""
Schemas: Dashboard Metrics
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class PeriodMetrics(BaseModel):
    """Métricas de um período"""
    total_sales: int = 0
    total_revenue: float = 0.0
    total_ml: int = 0
    average_ticket: float = 0.0
    success_rate: float = 100.0


class BeverageMetrics(BaseModel):
    """Métricas por bebida"""
    beverage_id: str
    beverage_name: str
    total_sales: int
    total_revenue: float
    total_ml: int


class MachineMetrics(BaseModel):
    """Métricas por máquina"""
    machine_id: str
    machine_code: str
    machine_name: str
    total_sales: int
    total_revenue: float
    total_ml: int
    status: str


class DashboardMetrics(BaseModel):
    """
    Métricas do dashboard
    Formato:
    {
      "today": { total_sales, total_revenue, total_ml, ... },
      "week": { ... },
      "month": { ... },
      "by_beverage": [...],
      "by_machine": [...]
    }
    """
    today: PeriodMetrics
    week: PeriodMetrics
    month: PeriodMetrics
    by_beverage: list[BeverageMetrics] = []
    by_machine: list[MachineMetrics] = []
    generated_at: datetime
