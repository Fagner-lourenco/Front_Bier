"""
Schemas: Machine
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class MachineBase(BaseModel):
    code: str
    name: str
    location: Optional[str] = None
    address: Optional[str] = None


class MachineCreate(MachineBase):
    organization_id: Optional[str] = None  # Preenchido pelo contexto se não informado


class MachineUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    address: Optional[str] = None
    status: Optional[str] = None
    active: Optional[bool] = None


class MachineResponse(MachineBase):
    id: str
    organization_id: str
    api_key: str
    hmac_secret: str
    status: str
    active: bool
    last_heartbeat: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class MachinePublicResponse(MachineBase):
    """Resposta sem dados sensíveis (api_key, hmac_secret)"""
    id: str
    status: str
    active: bool
    
    class Config:
        from_attributes = True
