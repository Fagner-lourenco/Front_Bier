"""
Modelo: Consumption
Registro do consumo real (enviado pelo EDGE após dispensar)
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship
from ..database import Base


class Consumption(Base):
    __tablename__ = "consumptions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    sale_id = Column(String(36), ForeignKey("sales.id"), index=True)
    machine_id = Column(String(36), ForeignKey("machines.id"), nullable=False, index=True)
    
    # Token usado
    token_id = Column(String(500))  # Token JWT/base64 usado para autorizar
    
    # Consumo real
    ml_served = Column(Integer, nullable=False)  # ml efetivamente servido
    ml_authorized = Column(Integer)  # ml que foi autorizado
    
    # Status
    status = Column(String(20), nullable=False)  # OK, PARTIAL, FAILED, ERROR
    error_message = Column(String(500))  # Mensagem de erro se houver
    
    # Tempos
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    
    # Sync
    synced_at = Column(DateTime, default=datetime.utcnow)  # Quando foi recebido pelo SaaS
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    organization = relationship("Organization", back_populates="consumptions")
    sale = relationship("Sale", back_populates="consumption")
    machine = relationship("Machine", back_populates="consumptions")
    
    def __repr__(self):
        return f"<Consumption {self.id[:8]} - {self.ml_served}ml>"
