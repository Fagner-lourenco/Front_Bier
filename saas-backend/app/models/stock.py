"""
Modelos: Gestão de Estoque
- MachineStock: Estoque por torneira/máquina
- StockRefill: Registro de abastecimentos
- StockMovement: Log de movimentações
- StockAlert: Alertas de estoque baixo
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Float, Integer, Text, Boolean
from sqlalchemy.orm import relationship
from ..database import Base


class MachineStock(Base):
    """Estoque de uma bebida em uma torneira específica da máquina"""
    __tablename__ = "machine_stocks"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    machine_id = Column(String(36), ForeignKey("machines.id"), nullable=False, index=True)
    beverage_id = Column(String(36), ForeignKey("beverages.id"), nullable=False, index=True)
    
    # Identificação da torneira
    tap_number = Column(Integer, nullable=False, default=1)  # 1, 2, 3...
    tap_label = Column(String(50))  # "Torneira 1", "Esquerda", etc.
    
    # Capacidade e estoque (em ML)
    capacity_ml = Column(Integer, nullable=False, default=30000)  # 30L padrão
    current_stock_ml = Column(Integer, nullable=False, default=0)
    
    # Thresholds de alerta
    low_stock_threshold_ml = Column(Integer, default=5000)  # 5L
    critical_stock_threshold_ml = Column(Integer, default=2000)  # 2L
    
    # Status
    active = Column(Boolean, default=True)
    
    # Controle
    last_refill_at = Column(DateTime)
    last_consumption_at = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    organization = relationship("Organization")
    machine = relationship("Machine", back_populates="stocks")
    beverage = relationship("Beverage")
    refills = relationship("StockRefill", back_populates="stock", cascade="all, delete-orphan")
    movements = relationship("StockMovement", back_populates="stock", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<MachineStock {self.machine_id[:8]} tap{self.tap_number} - {self.current_stock_ml}ml>"


class StockRefill(Base):
    """Registro de abastecimento"""
    __tablename__ = "stock_refills"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    machine_stock_id = Column(String(36), ForeignKey("machine_stocks.id"), nullable=False, index=True)
    
    # Quem fez
    refilled_by_user_id = Column(String(36), ForeignKey("users.id"))
    operator_name = Column(String(100))  # Se não for usuário do sistema
    
    # Quantidades
    quantity_ml = Column(Integer, nullable=False)
    stock_before_ml = Column(Integer)
    stock_after_ml = Column(Integer)
    
    # Tipo: full (barril novo), partial (complemento), adjustment (ajuste)
    refill_type = Column(String(20), default="full")
    
    # Dados do lote (opcional)
    batch_number = Column(String(50))
    supplier = Column(String(100))
    cost_per_liter = Column(Float)
    
    notes = Column(Text)
    
    # Timestamps
    refilled_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    organization = relationship("Organization")
    stock = relationship("MachineStock", back_populates="refills")
    user = relationship("User")
    
    def __repr__(self):
        return f"<StockRefill {self.id[:8]} +{self.quantity_ml}ml>"


class StockMovement(Base):
    """Log de movimentações de estoque"""
    __tablename__ = "stock_movements"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    machine_stock_id = Column(String(36), ForeignKey("machine_stocks.id"), nullable=False, index=True)
    
    # Tipo: consumption, refill, adjustment, waste
    movement_type = Column(String(20), nullable=False)
    
    # Quantidades (sempre positivo, tipo indica direção)
    quantity_ml = Column(Integer, nullable=False)
    stock_before_ml = Column(Integer)
    stock_after_ml = Column(Integer)
    
    # Referências opcionais
    consumption_id = Column(String(36), ForeignKey("consumptions.id"))
    refill_id = Column(String(36), ForeignKey("stock_refills.id"))
    
    notes = Column(String(500))
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relacionamentos
    organization = relationship("Organization")
    stock = relationship("MachineStock", back_populates="movements")
    
    def __repr__(self):
        return f"<StockMovement {self.movement_type} {self.quantity_ml}ml>"


class StockAlert(Base):
    """Alertas de estoque"""
    __tablename__ = "stock_alerts"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    machine_stock_id = Column(String(36), ForeignKey("machine_stocks.id"), nullable=False, index=True)
    
    # Tipo: low_stock, critical_stock, empty
    alert_type = Column(String(30), nullable=False)
    
    # Severidade: info, warning, critical
    severity = Column(String(10), default="warning")
    
    message = Column(String(500))
    
    # Dados do momento
    stock_level_ml = Column(Integer)
    threshold_ml = Column(Integer)
    
    # Status: active, acknowledged, resolved
    status = Column(String(20), default="active")
    acknowledged_by = Column(String(36), ForeignKey("users.id"))
    acknowledged_at = Column(DateTime)
    resolved_at = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relacionamentos
    organization = relationship("Organization")
    stock = relationship("MachineStock")
    
    def __repr__(self):
        return f"<StockAlert {self.alert_type} - {self.status}>"
