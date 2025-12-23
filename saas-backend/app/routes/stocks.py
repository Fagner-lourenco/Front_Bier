"""
Rotas: Gestão de Estoque
- GET/POST /stocks - Listar/criar estoques
- POST /stocks/refill - Registrar abastecimento
- POST /stocks/adjust - Ajuste manual
- GET /stocks/alerts - Alertas ativos
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, Machine, Beverage
from ..models.stock import MachineStock, StockRefill, StockMovement, StockAlert
from ..schemas.stock import (
    MachineStockCreate, MachineStockUpdate, MachineStockResponse, MachineStockSummary,
    StockRefillCreate, StockRefillResponse,
    StockMovementResponse,
    StockAlertResponse,
    StockAdjustmentCreate,
)
from ..utils.auth import get_current_user, get_machine_optional

router = APIRouter(prefix="/stocks", tags=["Stock Management"])


def check_and_create_alert(db: Session, stock: MachineStock):
    """Verifica thresholds e cria alertas se necessário"""
    # Determina tipo de alerta baseado no nível
    alert_type = None
    severity = None
    
    if stock.current_stock_ml <= 0:
        alert_type = "empty"
        severity = "critical"
    elif stock.current_stock_ml <= stock.critical_stock_threshold_ml:
        alert_type = "critical_stock"
        severity = "critical"
    elif stock.current_stock_ml <= stock.low_stock_threshold_ml:
        alert_type = "low_stock"
        severity = "warning"
    
    if not alert_type:
        return
    
    # Verifica se já existe alerta ativo do mesmo tipo
    existing = db.query(StockAlert).filter(
        StockAlert.machine_stock_id == stock.id,
        StockAlert.alert_type == alert_type,
        StockAlert.status == "active"
    ).first()
    
    if existing:
        return  # Já tem alerta ativo
    
    # Busca dados para mensagem
    beverage = db.query(Beverage).filter(Beverage.id == stock.beverage_id).first()
    machine = db.query(Machine).filter(Machine.id == stock.machine_id).first()
    
    messages = {
        "empty": f"ESTOQUE ZERADO: {beverage.name if beverage else 'Bebida'} na máquina {machine.code if machine else 'N/A'}",
        "critical_stock": f"ESTOQUE CRÍTICO: {beverage.name if beverage else 'Bebida'} com apenas {stock.current_stock_ml}ml",
        "low_stock": f"ESTOQUE BAIXO: {beverage.name if beverage else 'Bebida'} com {stock.current_stock_ml}ml",
    }
    
    alert = StockAlert(
        organization_id=stock.organization_id,
        machine_stock_id=stock.id,
        alert_type=alert_type,
        severity=severity,
        message=messages.get(alert_type, "Alerta de estoque"),
        stock_level_ml=stock.current_stock_ml,
        threshold_ml=stock.low_stock_threshold_ml if alert_type == "low_stock" else stock.critical_stock_threshold_ml,
    )
    db.add(alert)


def resolve_alerts_if_ok(db: Session, stock: MachineStock):
    """Resolve alertas ativos se estoque estiver OK"""
    if stock.current_stock_ml > stock.low_stock_threshold_ml:
        db.query(StockAlert).filter(
            StockAlert.machine_stock_id == stock.id,
            StockAlert.status == "active"
        ).update({
            "status": "resolved",
            "resolved_at": datetime.utcnow()
        })


# ========== Estoques ==========

@router.get("", response_model=List[MachineStockResponse])
async def list_stocks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    machine_id: Optional[str] = Query(None),
    only_low: bool = Query(False, description="Apenas estoques baixos/críticos"),
):
    """Lista estoques da organização"""
    query = db.query(MachineStock).filter(
        MachineStock.organization_id == current_user.organization_id,
        MachineStock.active == True
    )
    
    if machine_id:
        query = query.filter(MachineStock.machine_id == machine_id)
    
    stocks = query.order_by(MachineStock.machine_id, MachineStock.tap_number).all()
    
    result = []
    for stock in stocks:
        # Calcula status
        if stock.current_stock_ml <= 0:
            stock_status = "empty"
        elif stock.current_stock_ml <= stock.critical_stock_threshold_ml:
            stock_status = "critical"
        elif stock.current_stock_ml <= stock.low_stock_threshold_ml:
            stock_status = "low"
        else:
            stock_status = "ok"
        
        if only_low and stock_status == "ok":
            continue
        
        beverage = db.query(Beverage).filter(Beverage.id == stock.beverage_id).first()
        
        result.append(MachineStockResponse(
            id=stock.id,
            machine_id=stock.machine_id,
            beverage_id=stock.beverage_id,
            beverage_name=beverage.name if beverage else None,
            tap_number=stock.tap_number,
            tap_label=stock.tap_label,
            capacity_ml=stock.capacity_ml,
            current_stock_ml=stock.current_stock_ml,
            stock_percentage=round((stock.current_stock_ml / stock.capacity_ml * 100) if stock.capacity_ml > 0 else 0, 1),
            low_stock_threshold_ml=stock.low_stock_threshold_ml,
            critical_stock_threshold_ml=stock.critical_stock_threshold_ml,
            stock_status=stock_status,
            active=stock.active,
            last_refill_at=stock.last_refill_at,
            last_consumption_at=stock.last_consumption_at,
        ))
    
    return result


@router.post("", response_model=MachineStockResponse, status_code=status.HTTP_201_CREATED)
async def create_stock(
    data: MachineStockCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Configura estoque para uma torneira"""
    # Verifica máquina
    machine = db.query(Machine).filter(
        Machine.id == data.machine_id,
        Machine.organization_id == current_user.organization_id
    ).first()
    
    if not machine:
        raise HTTPException(status_code=404, detail="Máquina não encontrada")
    
    # Verifica bebida
    beverage = db.query(Beverage).filter(Beverage.id == data.beverage_id).first()
    if not beverage:
        raise HTTPException(status_code=404, detail="Bebida não encontrada")
    
    # Verifica se já existe estoque para essa torneira
    existing = db.query(MachineStock).filter(
        MachineStock.machine_id == data.machine_id,
        MachineStock.tap_number == data.tap_number,
        MachineStock.active == True
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail=f"Torneira {data.tap_number} já configurada")
    
    stock = MachineStock(
        organization_id=current_user.organization_id,
        machine_id=data.machine_id,
        beverage_id=data.beverage_id,
        tap_number=data.tap_number,
        tap_label=data.tap_label,
        capacity_ml=data.capacity_ml,
        current_stock_ml=data.initial_stock_ml,
        low_stock_threshold_ml=data.low_stock_threshold_ml,
        critical_stock_threshold_ml=data.critical_stock_threshold_ml,
    )
    
    db.add(stock)
    db.commit()
    db.refresh(stock)
    
    return MachineStockResponse(
        id=stock.id,
        machine_id=stock.machine_id,
        beverage_id=stock.beverage_id,
        beverage_name=beverage.name,
        tap_number=stock.tap_number,
        tap_label=stock.tap_label,
        capacity_ml=stock.capacity_ml,
        current_stock_ml=stock.current_stock_ml,
        stock_percentage=round((stock.current_stock_ml / stock.capacity_ml * 100) if stock.capacity_ml > 0 else 0, 1),
        low_stock_threshold_ml=stock.low_stock_threshold_ml,
        critical_stock_threshold_ml=stock.critical_stock_threshold_ml,
        stock_status="ok" if stock.current_stock_ml > stock.low_stock_threshold_ml else "low",
        active=stock.active,
        last_refill_at=stock.last_refill_at,
        last_consumption_at=stock.last_consumption_at,
    )


# ========== Abastecimento ==========

@router.post("/refill", response_model=StockRefillResponse, status_code=status.HTTP_201_CREATED)
async def register_refill(
    data: StockRefillCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Registra abastecimento"""
    # Busca estoque
    stock = db.query(MachineStock).filter(
        MachineStock.id == data.machine_stock_id,
        MachineStock.organization_id == current_user.organization_id
    ).first()
    
    if not stock:
        raise HTTPException(status_code=404, detail="Estoque não encontrado")
    
    stock_before = stock.current_stock_ml
    
    # Atualiza estoque
    if data.refill_type == "full":
        # Barril novo: reseta para capacidade ou quantidade informada
        stock.current_stock_ml = min(data.quantity_ml, stock.capacity_ml)
    else:
        # Complemento: adiciona
        stock.current_stock_ml = min(stock.current_stock_ml + data.quantity_ml, stock.capacity_ml)
    
    stock.last_refill_at = datetime.utcnow()
    stock_after = stock.current_stock_ml
    
    # Cria registro de abastecimento
    refill = StockRefill(
        organization_id=current_user.organization_id,
        machine_stock_id=stock.id,
        refilled_by_user_id=current_user.id,
        operator_name=data.operator_name or current_user.name,
        quantity_ml=data.quantity_ml,
        stock_before_ml=stock_before,
        stock_after_ml=stock_after,
        refill_type=data.refill_type,
        batch_number=data.batch_number,
        supplier=data.supplier,
        cost_per_liter=data.cost_per_liter,
        notes=data.notes,
    )
    db.add(refill)
    
    # Registra movimento
    movement = StockMovement(
        organization_id=current_user.organization_id,
        machine_stock_id=stock.id,
        movement_type="refill",
        quantity_ml=stock_after - stock_before,
        stock_before_ml=stock_before,
        stock_after_ml=stock_after,
        refill_id=refill.id,
    )
    db.add(movement)
    
    # Resolve alertas se estoque OK
    resolve_alerts_if_ok(db, stock)
    
    db.commit()
    db.refresh(refill)
    
    return refill


# ========== Ajuste Manual ==========

@router.post("/adjust", response_model=StockMovementResponse, status_code=status.HTTP_201_CREATED)
async def adjust_stock(
    data: StockAdjustmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Ajuste manual de estoque (inventário, perda, etc)"""
    stock = db.query(MachineStock).filter(
        MachineStock.id == data.machine_stock_id,
        MachineStock.organization_id == current_user.organization_id
    ).first()
    
    if not stock:
        raise HTTPException(status_code=404, detail="Estoque não encontrado")
    
    stock_before = stock.current_stock_ml
    stock.current_stock_ml = min(data.new_stock_ml, stock.capacity_ml)
    stock_after = stock.current_stock_ml
    
    difference = stock_after - stock_before
    movement_type = "adjustment" if difference >= 0 else "waste"
    
    movement = StockMovement(
        organization_id=current_user.organization_id,
        machine_stock_id=stock.id,
        movement_type=movement_type,
        quantity_ml=abs(difference),
        stock_before_ml=stock_before,
        stock_after_ml=stock_after,
        notes=f"{data.reason}: {data.notes}" if data.notes else data.reason,
    )
    db.add(movement)
    
    # Verifica alertas
    if stock_after > stock.low_stock_threshold_ml:
        resolve_alerts_if_ok(db, stock)
    else:
        check_and_create_alert(db, stock)
    
    db.commit()
    db.refresh(movement)
    
    return movement


# ========== Alertas ==========

@router.get("/alerts", response_model=List[StockAlertResponse])
async def list_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    status_filter: Optional[str] = Query("active", description="active, acknowledged, resolved, all"),
    machine_id: Optional[str] = Query(None),
):
    """Lista alertas de estoque"""
    query = db.query(StockAlert).filter(
        StockAlert.organization_id == current_user.organization_id
    )
    
    if status_filter and status_filter != "all":
        query = query.filter(StockAlert.status == status_filter)
    
    if machine_id:
        stock_ids = db.query(MachineStock.id).filter(
            MachineStock.machine_id == machine_id
        ).subquery()
        query = query.filter(StockAlert.machine_stock_id.in_(stock_ids))
    
    alerts = query.order_by(StockAlert.created_at.desc()).limit(100).all()
    
    result = []
    for alert in alerts:
        stock = db.query(MachineStock).filter(MachineStock.id == alert.machine_stock_id).first()
        machine = db.query(Machine).filter(Machine.id == stock.machine_id).first() if stock else None
        beverage = db.query(Beverage).filter(Beverage.id == stock.beverage_id).first() if stock else None
        
        result.append(StockAlertResponse(
            id=alert.id,
            machine_stock_id=alert.machine_stock_id,
            alert_type=alert.alert_type,
            severity=alert.severity,
            message=alert.message,
            stock_level_ml=alert.stock_level_ml,
            threshold_ml=alert.threshold_ml,
            status=alert.status,
            created_at=alert.created_at,
            acknowledged_at=alert.acknowledged_at,
            resolved_at=alert.resolved_at,
            machine_code=machine.code if machine else None,
            beverage_name=beverage.name if beverage else None,
        ))
    
    return result


@router.put("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Marca alerta como visto"""
    alert = db.query(StockAlert).filter(
        StockAlert.id == alert_id,
        StockAlert.organization_id == current_user.organization_id
    ).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alerta não encontrado")
    
    alert.status = "acknowledged"
    alert.acknowledged_by = current_user.id
    alert.acknowledged_at = datetime.utcnow()
    
    db.commit()
    
    return {"status": "ok", "message": "Alerta confirmado"}


# ========== Histórico ==========

@router.get("/{stock_id}/movements", response_model=List[StockMovementResponse])
async def list_movements(
    stock_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(50, le=200),
):
    """Histórico de movimentações de um estoque"""
    stock = db.query(MachineStock).filter(
        MachineStock.id == stock_id,
        MachineStock.organization_id == current_user.organization_id
    ).first()
    
    if not stock:
        raise HTTPException(status_code=404, detail="Estoque não encontrado")
    
    movements = db.query(StockMovement).filter(
        StockMovement.machine_stock_id == stock_id
    ).order_by(StockMovement.created_at.desc()).limit(limit).all()
    
    return movements
