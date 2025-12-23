"""
Modelo: Beverage
Bebidas disponíveis para venda
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Float, Integer
from sqlalchemy.orm import relationship
from ..database import Base


class Beverage(Base):
    __tablename__ = "beverages"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    
    # Informações básicas
    name = Column(String(100), nullable=False)
    style = Column(String(50))  # Pilsen, IPA, Lager, etc
    description = Column(String(500))
    
    # Características
    abv = Column(Float, default=0.0)  # Teor alcoólico (0.0 para não-alcoólicos)
    
    # Preço
    price_per_ml = Column(Float, nullable=False)  # Ex: 0.04 = R$0,04 por ml
    
    # Imagem
    image_url = Column(String(500))
    
    # Ordenação no cardápio
    display_order = Column(Integer, default=0)
    
    active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    organization = relationship("Organization", back_populates="beverages")
    sales = relationship("Sale", back_populates="beverage")
    
    def __repr__(self):
        return f"<Beverage {self.name}>"
