"""
Modelo: Machine
Máquinas dispensadoras de bebidas
"""
import uuid
import secrets
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from ..database import Base


def generate_api_key():
    """Gera uma API Key única para a máquina"""
    return f"sk_{secrets.token_urlsafe(32)}"


def generate_hmac_secret():
    """Gera um HMAC secret para validação de tokens"""
    return secrets.token_urlsafe(32)


class Machine(Base):
    __tablename__ = "machines"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    
    # Identificação
    code = Column(String(20), nullable=False, index=True)  # Ex: M001
    name = Column(String(100), nullable=False)
    
    # Localização
    location = Column(String(200))
    address = Column(Text)
    
    # Autenticação
    api_key = Column(String(100), unique=True, nullable=False, default=generate_api_key, index=True)
    hmac_secret = Column(String(100), nullable=False, default=generate_hmac_secret)
    
    # Status
    status = Column(String(20), default="offline")  # online, offline, maintenance
    last_heartbeat = Column(DateTime)
    
    active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    organization = relationship("Organization", back_populates="machines")
    sales = relationship("Sale", back_populates="machine", cascade="all, delete-orphan")
    consumptions = relationship("Consumption", back_populates="machine", cascade="all, delete-orphan")
    stocks = relationship("MachineStock", back_populates="machine", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Machine {self.code}>"
