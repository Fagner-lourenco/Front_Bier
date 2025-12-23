"""
Schemas: Consumption
Compatível com o formato enviado pelo EDGE
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ConsumptionCreate(BaseModel):
    """
    Formato recebido do EDGE:
    {
      "token_id": "eyJhbGciOiJ...",
      "machine_id": "M001",
      "ml_served": 300,
      "status": "OK",
      "started_at": "2025-12-22T10:30:10.000Z",
      "finished_at": "2025-12-22T10:30:45.000Z"
    }
    
    Ou com sale_id (se conhecido):
    {
      "sale_id": "SALE_789",
      "machine_id": "M001",
      "ml_served": 300,
      "status": "OK",
      ...
    }
    """
    token_id: Optional[str] = None
    sale_id: Optional[str] = None
    machine_id: str
    ml_served: int
    ml_authorized: Optional[int] = None
    status: str  # OK, PARTIAL, FAILED, ERROR
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class ConsumptionResponse(BaseModel):
    """
    Resposta para o EDGE:
    {
      "status": "OK",
      "message": "Consumption registered"
    }
    """
    status: str = "OK"
    message: str = "Consumption registered"
    consumption_id: Optional[str] = None


class ConsumptionDetailResponse(BaseModel):
    """Resposta detalhada para dashboard"""
    id: str
    sale_id: Optional[str]
    machine_id: str
    ml_served: int
    ml_authorized: Optional[int]
    status: str
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    synced_at: datetime
    
    class Config:
        from_attributes = True
