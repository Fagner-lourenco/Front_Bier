"""
Schemas: Organization
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class OrganizationBase(BaseModel):
    name: str
    slug: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    plan: str = "basic"


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    plan: Optional[str] = None
    active: Optional[bool] = None


class OrganizationResponse(OrganizationBase):
    id: str
    active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
