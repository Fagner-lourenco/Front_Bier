"""
Schemas: Beverage
Compatível com o formato esperado pelo APP Kiosk
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class BeverageBase(BaseModel):
    name: str
    style: Optional[str] = None
    description: Optional[str] = None
    abv: float = 0.0
    price_per_ml: float = Field(..., gt=0)
    image_url: Optional[str] = None
    display_order: int = 0


class BeverageCreate(BeverageBase):
    organization_id: Optional[str] = None  # Preenchido pelo contexto se não informado


class BeverageUpdate(BaseModel):
    name: Optional[str] = None
    style: Optional[str] = None
    description: Optional[str] = None
    abv: Optional[float] = None
    price_per_ml: Optional[float] = None
    image_url: Optional[str] = None
    display_order: Optional[int] = None
    active: Optional[bool] = None


class BeverageResponse(BaseModel):
    """
    Resposta compatível com APP Kiosk
    Formato: { id, name, style, abv, price_per_ml, image_url }
    """
    id: str
    name: str
    style: Optional[str] = None
    abv: float
    price_per_ml: float
    image_url: Optional[str] = None
    active: bool = True
    
    class Config:
        from_attributes = True


class BeverageListResponse(BaseModel):
    """
    Wrapper para lista de bebidas
    Formato: { beverages: [...] }
    """
    beverages: list[BeverageResponse]
