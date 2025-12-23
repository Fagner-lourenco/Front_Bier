"""
Rotas: Consumptions (Consumos)
- POST /consumptions - Registra consumo (EDGE via API Key)
- GET /consumptions - Lista consumos (admin)
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Consumption, Sale, Machine, User
from ..models.stock import MachineStock, StockMovement, StockAlert
from ..schemas import ConsumptionCreate, ConsumptionResponse, ConsumptionDetailResponse
from ..utils.auth import get_machine_by_api_key, get_current_user, get_machine_optional

router = APIRouter(prefix="/consumptions", tags=["Consumptions"])


@router.post("", response_model=ConsumptionResponse, status_code=status.HTTP_201_CREATED)
async def register_consumption(
    consumption_data: ConsumptionCreate,
    db: Session = Depends(get_db),
    machine: Optional[Machine] = Depends(get_machine_optional)
):
    """
    Registra consumo realizado (EDGE)
    
    Formato recebido:
    {
      "token_id": "eyJhbGciOiJ...",
      "machine_id": "M001",
      "ml_served": 300,
      "status": "OK",
      "started_at": "2025-12-22T10:30:10.000Z",
      "finished_at": "2025-12-22T10:30:45.000Z"
    }
    
    Retorna: { "status": "OK", "message": "Consumption registered" }
    """
    # Determina organização e máquina
    if machine:
        org_id = machine.organization_id
        machine_db = machine
    else:
        # Desenvolvimento: busca máquina pelo código
        machine_db = db.query(Machine).filter(
            Machine.code == consumption_data.machine_id
        ).first()
        
        if not machine_db:
            machine_db = db.query(Machine).filter(
                Machine.id == consumption_data.machine_id
            ).first()
        
        if not machine_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Machine {consumption_data.machine_id} not found"
            )
        
        org_id = machine_db.organization_id
    
    # Busca venda relacionada (se fornecida)
    sale_id = consumption_data.sale_id
    if sale_id:
        sale = db.query(Sale).filter(Sale.id == sale_id).first()
        if sale:
            # Atualiza status da venda
            sale.status = "completed" if consumption_data.status == "OK" else "failed"
    
    # Cria consumo
    consumption = Consumption(
        organization_id=org_id,
        sale_id=sale_id,
        machine_id=machine_db.id,
        token_id=consumption_data.token_id,
        ml_served=consumption_data.ml_served,
        ml_authorized=consumption_data.ml_authorized,
        status=consumption_data.status,
        error_message=consumption_data.error_message,
        started_at=consumption_data.started_at,
        finished_at=consumption_data.finished_at,
        synced_at=datetime.utcnow(),
    )
    
    db.add(consumption)
    
    # === DEDUÇÃO AUTOMÁTICA DE ESTOQUE ===
    # Busca beverage_id da venda relacionada
    beverage_id = None
    if sale_id:
        sale_for_beverage = db.query(Sale).filter(Sale.id == sale_id).first()
        if sale_for_beverage:
            beverage_id = sale_for_beverage.beverage_id
    
    if beverage_id and consumption_data.status == "OK":
        # Busca estoque ativo desta bebida nesta máquina
        stock = db.query(MachineStock).filter(
            MachineStock.machine_id == machine_db.id,
            MachineStock.beverage_id == beverage_id,
            MachineStock.active == True
        ).first()
        
        if stock:
            stock_before = stock.current_stock_ml
            stock.current_stock_ml = max(0, stock.current_stock_ml - consumption_data.ml_served)
            stock.last_consumption_at = datetime.utcnow()
            
            # Registra movimentação
            movement = StockMovement(
                organization_id=org_id,
                machine_stock_id=stock.id,
                movement_type="consumption",
                quantity_ml=consumption_data.ml_served,
                stock_before_ml=stock_before,
                stock_after_ml=stock.current_stock_ml,
                consumption_id=consumption.id,
            )
            db.add(movement)
            
            # Verifica se precisa criar alerta
            if stock.current_stock_ml <= 0:
                alert_type, severity = "empty", "critical"
            elif stock.current_stock_ml <= stock.critical_stock_threshold_ml:
                alert_type, severity = "critical_stock", "critical"
            elif stock.current_stock_ml <= stock.low_stock_threshold_ml:
                alert_type, severity = "low_stock", "warning"
            else:
                alert_type = None
            
            if alert_type:
                # Verifica se já existe alerta ativo
                existing_alert = db.query(StockAlert).filter(
                    StockAlert.machine_stock_id == stock.id,
                    StockAlert.alert_type == alert_type,
                    StockAlert.status == "active"
                ).first()
                
                if not existing_alert:
                    alert = StockAlert(
                        organization_id=org_id,
                        machine_stock_id=stock.id,
                        alert_type=alert_type,
                        severity=severity,
                        message=f"Estoque {alert_type.replace('_', ' ')}: {stock.current_stock_ml}ml restantes",
                        stock_level_ml=stock.current_stock_ml,
                        threshold_ml=stock.low_stock_threshold_ml if alert_type == "low_stock" else stock.critical_stock_threshold_ml,
                    )
                    db.add(alert)
    
    db.commit()
    db.refresh(consumption)
    
    return ConsumptionResponse(
        status="OK",
        message="Consumption registered",
        consumption_id=consumption.id
    )


@router.get("", response_model=List[ConsumptionDetailResponse])
async def list_consumptions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    machine_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0)
):
    """Lista consumos da organização (admin)"""
    query = db.query(Consumption).filter(
        Consumption.organization_id == current_user.organization_id
    )
    
    if machine_id:
        query = query.filter(Consumption.machine_id == machine_id)
    if status_filter:
        query = query.filter(Consumption.status == status_filter)
    if date_from:
        query = query.filter(Consumption.synced_at >= date_from)
    if date_to:
        query = query.filter(Consumption.synced_at <= date_to)
    
    consumptions = query.order_by(Consumption.synced_at.desc()).offset(offset).limit(limit).all()
    
    return [ConsumptionDetailResponse.model_validate(c) for c in consumptions]


@router.get("/{consumption_id}", response_model=ConsumptionDetailResponse)
async def get_consumption(
    consumption_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtém detalhes de um consumo (admin)"""
    consumption = db.query(Consumption).filter(
        Consumption.id == consumption_id,
        Consumption.organization_id == current_user.organization_id
    ).first()
    
    if not consumption:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consumption not found"
        )
    
    return consumption
