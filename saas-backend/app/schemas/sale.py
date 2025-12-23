"""
Schemas: Sale
Compatível com o formato enviado pelo APP Kiosk
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class SaleCreate(BaseModel):
    """
    Formato recebido do APP Kiosk:
    {
      "machine_id": "M001",
      "beverage_id": 1,
      "volume_ml": 300,
      "total_value": 12.00,
      "payment_method": "PIX",
      "payment_transaction_id": "SDK_123456",
      "payment_nsu": "987654",
      "created_at": "2025-12-22T14:22:00Z"
    }
    """
    machine_id: str  # Código da máquina (ex: M001) ou UUID
    beverage_id: str  # UUID da bebida
    volume_ml: int = Field(..., gt=0, le=1000)
    total_value: float = Field(..., gt=0)
    payment_method: str  # PIX, CREDIT, DEBIT
    payment_transaction_id: str
    payment_nsu: Optional[str] = None
    payment_auth_code: Optional[str] = None
    payment_card_brand: Optional[str] = None
    payment_card_last_digits: Optional[str] = None
    created_at: Optional[datetime] = None


class SaleResponse(BaseModel):
    """
    Resposta para o APP Kiosk:
    {
      "sale_id": "SALE_789",
      "status": "REGISTERED"
    }
    """
    sale_id: str
    status: str = "REGISTERED"


class SaleDetailResponse(BaseModel):
    """Resposta detalhada para dashboard"""
    id: str
    machine_id: str
    beverage_id: str
    volume_ml: int
    total_value: float
    payment_method: str
    payment_transaction_id: Optional[str]
    payment_nsu: Optional[str]
    status: str
    created_at: datetime
    
    # Dados relacionados
    machine_code: Optional[str] = None
    beverage_name: Optional[str] = None
    
    class Config:
        from_attributes = True
