"""
Modelo: Organization (Multi-tenant)
Representa uma empresa/franquia que possui máquinas BierPass
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from ..database import Base


class Organization(Base):
    __tablename__ = "organizations"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    slug = Column(String(50), unique=True, nullable=False, index=True)
    
    # Contato
    email = Column(String(100))
    phone = Column(String(20))
    
    # Endereço
    address = Column(Text)
    city = Column(String(50))
    state = Column(String(2))
    
    # Plano/Status
    plan = Column(String(20), default="basic")  # basic, pro, enterprise
    active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    machines = relationship("Machine", back_populates="organization", cascade="all, delete-orphan")
    beverages = relationship("Beverage", back_populates="organization", cascade="all, delete-orphan")
    sales = relationship("Sale", back_populates="organization", cascade="all, delete-orphan")
    consumptions = relationship("Consumption", back_populates="organization", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Organization {self.name}>"
