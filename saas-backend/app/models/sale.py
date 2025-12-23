"""
Modelo: Sale
Registro de vendas realizadas (enviado pelo APP após pagamento)
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Float, Integer
from sqlalchemy.orm import relationship
from ..database import Base


class Sale(Base):
    __tablename__ = "sales"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    machine_id = Column(String(36), ForeignKey("machines.id"), nullable=False, index=True)
    beverage_id = Column(String(36), ForeignKey("beverages.id"), nullable=False, index=True)
    
    # Venda
    volume_ml = Column(Integer, nullable=False)  # 200, 300, 400, 500
    total_value = Column(Float, nullable=False)  # Valor total em R$
    
    # Pagamento (da maquininha)
    payment_method = Column(String(20), nullable=False)  # PIX, CREDIT, DEBIT
    payment_transaction_id = Column(String(100), index=True)  # ID da transação SDK
    payment_nsu = Column(String(50))  # NSU da operadora
    payment_auth_code = Column(String(20))  # Código de autorização
    payment_card_brand = Column(String(20))  # VISA, MASTER, etc
    payment_card_last_digits = Column(String(4))  # Últimos 4 dígitos
    
    # Status
    status = Column(String(20), default="pending")  # pending, completed, failed
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    organization = relationship("Organization", back_populates="sales")
    machine = relationship("Machine", back_populates="sales")
    beverage = relationship("Beverage", back_populates="sales")
    consumption = relationship("Consumption", back_populates="sale", uselist=False)
    
    def __repr__(self):
        return f"<Sale {self.id[:8]} - {self.volume_ml}ml>"
