"""
Schemas: Gestão de Estoque
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ========== MachineStock ==========

class MachineStockCreate(BaseModel):
    """Criar estoque para torneira"""
    machine_id: str
    beverage_id: str
    tap_number: int = 1
    tap_label: Optional[str] = None
    capacity_ml: int = 30000  # 30L padrão
    initial_stock_ml: int = 0
    low_stock_threshold_ml: int = 5000
    critical_stock_threshold_ml: int = 2000


class MachineStockUpdate(BaseModel):
    """Atualizar configuração de estoque"""
    beverage_id: Optional[str] = None
    tap_label: Optional[str] = None
    capacity_ml: Optional[int] = None
    low_stock_threshold_ml: Optional[int] = None
    critical_stock_threshold_ml: Optional[int] = None
    active: Optional[bool] = None


class MachineStockResponse(BaseModel):
    """Resposta de estoque"""
    id: str
    machine_id: str
    beverage_id: str
    beverage_name: Optional[str] = None
    tap_number: int
    tap_label: Optional[str]
    capacity_ml: int
    current_stock_ml: int
    stock_percentage: float
    low_stock_threshold_ml: int
    critical_stock_threshold_ml: int
    stock_status: str  # ok, low, critical, empty
    active: bool
    last_refill_at: Optional[datetime]
    last_consumption_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class MachineStockSummary(BaseModel):
    """Resumo de estoque de uma máquina"""
    machine_id: str
    machine_code: str
    machine_name: str
    total_taps: int
    stocks: List[MachineStockResponse]
    alerts_count: int


# ========== StockRefill ==========

class StockRefillCreate(BaseModel):
    """Registrar abastecimento"""
    machine_stock_id: str
    quantity_ml: int = Field(..., gt=0)
    refill_type: str = "full"  # full, partial, adjustment
    operator_name: Optional[str] = None
    batch_number: Optional[str] = None
    supplier: Optional[str] = None
    cost_per_liter: Optional[float] = None
    notes: Optional[str] = None


class StockRefillResponse(BaseModel):
    """Resposta de abastecimento"""
    id: str
    machine_stock_id: str
    quantity_ml: int
    stock_before_ml: int
    stock_after_ml: int
    refill_type: str
    operator_name: Optional[str]
    batch_number: Optional[str]
    supplier: Optional[str]
    refilled_at: datetime
    
    class Config:
        from_attributes = True


# ========== StockMovement ==========

class StockMovementResponse(BaseModel):
    """Resposta de movimentação"""
    id: str
    movement_type: str
    quantity_ml: int
    stock_before_ml: int
    stock_after_ml: int
    notes: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


# ========== StockAlert ==========

class StockAlertResponse(BaseModel):
    """Resposta de alerta"""
    id: str
    machine_stock_id: str
    alert_type: str
    severity: str
    message: str
    stock_level_ml: int
    threshold_ml: Optional[int]
    status: str
    created_at: datetime
    acknowledged_at: Optional[datetime]
    resolved_at: Optional[datetime]
    
    # Dados da máquina/bebida
    machine_code: Optional[str] = None
    beverage_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class StockAlertAcknowledge(BaseModel):
    """Confirmar alerta como visto"""
    pass  # user_id vem do token


# ========== Adjustment ==========

class StockAdjustmentCreate(BaseModel):
    """Ajuste manual de estoque"""
    machine_stock_id: str
    new_stock_ml: int = Field(..., ge=0)
    reason: str  # inventory, waste, correction, other
    notes: Optional[str] = None
