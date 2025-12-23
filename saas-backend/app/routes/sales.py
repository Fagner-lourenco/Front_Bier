"""
Rotas: Sales (Vendas)
- POST /sales - Registra venda (APP Kiosk via API Key)
- GET /sales - Lista vendas (admin)
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Sale, Machine, Beverage, User
from ..schemas import SaleCreate, SaleResponse, SaleDetailResponse
from ..utils.auth import get_machine_by_api_key, get_current_user, get_machine_optional

router = APIRouter(prefix="/sales", tags=["Sales"])


@router.post("", response_model=SaleResponse, status_code=status.HTTP_201_CREATED)
async def register_sale(
    sale_data: SaleCreate,
    db: Session = Depends(get_db),
    machine: Optional[Machine] = Depends(get_machine_optional)
):
    """
    Registra venda (APP Kiosk)
    
    Formato recebido do APP:
    {
      "machine_id": "M001",
      "beverage_id": "uuid-da-bebida",
      "volume_ml": 300,
      "total_value": 12.00,
      "payment_method": "PIX",
      "payment_transaction_id": "SDK_123456",
      "payment_nsu": "987654",
      "created_at": "2025-12-22T14:22:00Z"
    }
    
    Retorna: { "sale_id": "...", "status": "REGISTERED" }
    """
    # Determina organização
    if machine:
        org_id = machine.organization_id
        machine_db = machine
    else:
        # Desenvolvimento: busca máquina pelo código
        machine_db = db.query(Machine).filter(
            Machine.code == sale_data.machine_id
        ).first()
        
        if not machine_db:
            # Tenta buscar por ID
            machine_db = db.query(Machine).filter(
                Machine.id == sale_data.machine_id
            ).first()
        
        if not machine_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Machine {sale_data.machine_id} not found"
            )
        
        org_id = machine_db.organization_id
    
    # Busca bebida
    beverage = db.query(Beverage).filter(
        Beverage.id == sale_data.beverage_id
    ).first()
    
    if not beverage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Beverage {sale_data.beverage_id} not found"
        )
    
    # Cria venda
    sale = Sale(
        organization_id=org_id,
        machine_id=machine_db.id,
        beverage_id=beverage.id,
        volume_ml=sale_data.volume_ml,
        total_value=sale_data.total_value,
        payment_method=sale_data.payment_method,
        payment_transaction_id=sale_data.payment_transaction_id,
        payment_nsu=sale_data.payment_nsu,
        payment_auth_code=sale_data.payment_auth_code,
        payment_card_brand=sale_data.payment_card_brand,
        payment_card_last_digits=sale_data.payment_card_last_digits,
        status="pending",
        created_at=sale_data.created_at or datetime.utcnow(),
    )
    
    db.add(sale)
    db.commit()
    db.refresh(sale)
    
    return SaleResponse(sale_id=sale.id, status="REGISTERED")


@router.get("", response_model=List[SaleDetailResponse])
async def list_sales(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    machine_id: Optional[str] = Query(None),
    beverage_id: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0)
):
    """Lista vendas da organização (admin)"""
    query = db.query(Sale).filter(
        Sale.organization_id == current_user.organization_id
    )
    
    if machine_id:
        query = query.filter(Sale.machine_id == machine_id)
    if beverage_id:
        query = query.filter(Sale.beverage_id == beverage_id)
    if date_from:
        query = query.filter(Sale.created_at >= date_from)
    if date_to:
        query = query.filter(Sale.created_at <= date_to)
    
    sales = query.order_by(Sale.created_at.desc()).offset(offset).limit(limit).all()
    
    result = []
    for sale in sales:
        detail = SaleDetailResponse(
            id=sale.id,
            machine_id=sale.machine_id,
            beverage_id=sale.beverage_id,
            volume_ml=sale.volume_ml,
            total_value=sale.total_value,
            payment_method=sale.payment_method,
            payment_transaction_id=sale.payment_transaction_id,
            payment_nsu=sale.payment_nsu,
            status=sale.status,
            created_at=sale.created_at,
            machine_code=sale.machine.code if sale.machine else None,
            beverage_name=sale.beverage.name if sale.beverage else None,
        )
        result.append(detail)
    
    return result


@router.get("/{sale_id}", response_model=SaleDetailResponse)
async def get_sale(
    sale_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtém detalhes de uma venda (admin)"""
    sale = db.query(Sale).filter(
        Sale.id == sale_id,
        Sale.organization_id == current_user.organization_id
    ).first()
    
    if not sale:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sale not found"
        )
    
    return SaleDetailResponse(
        id=sale.id,
        machine_id=sale.machine_id,
        beverage_id=sale.beverage_id,
        volume_ml=sale.volume_ml,
        total_value=sale.total_value,
        payment_method=sale.payment_method,
        payment_transaction_id=sale.payment_transaction_id,
        payment_nsu=sale.payment_nsu,
        status=sale.status,
        created_at=sale.created_at,
        machine_code=sale.machine.code if sale.machine else None,
        beverage_name=sale.beverage.name if sale.beverage else None,
    )
