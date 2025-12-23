"""
Rotas: Beverages (Bebidas)
- GET /beverages - Lista bebidas (APP Kiosk via API Key)
- CRUD completo para admin
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Beverage, Machine, User
from ..schemas import (
    BeverageCreate, 
    BeverageUpdate, 
    BeverageResponse,
    BeverageListResponse,
)
from ..utils.auth import get_current_user, get_machine_by_api_key, get_machine_optional

router = APIRouter(prefix="/beverages", tags=["Beverages"])


@router.get("")
async def list_beverages(
    db: Session = Depends(get_db),
    machine: Optional[Machine] = Depends(get_machine_optional),
    current_user: Optional[User] = Depends(lambda: None)  # Placeholder
):
    """
    Lista bebidas ativas
    
    Para APP Kiosk: usa X-API-Key header
    Para Admin: usa JWT Bearer token
    Sem auth: retorna todas as bebidas ativas (desenvolvimento)
    
    Retorna: { "beverages": [...] }
    """
    query = db.query(Beverage).filter(Beverage.active == True)
    
    # Se tem máquina autenticada, filtra por organização
    if machine:
        print(f"[API] Filtrando por machine org: {machine.organization_id}")
        query = query.filter(Beverage.organization_id == machine.organization_id)
    else:
        print("[API] Sem autenticação, retornando todas as bebidas")
    
    beverages = query.order_by(Beverage.display_order, Beverage.name).all()
    print(f"[API] Total bebidas encontradas: {len(beverages)}")
    for b in beverages:
        print(f"  - {b.name}")
    
    # Converte manualmente para evitar problemas de serialização
    beverage_list = []
    for b in beverages:
        beverage_list.append({
            "id": b.id,
            "name": b.name,
            "style": b.style,
            "abv": b.abv,
            "price_per_ml": b.price_per_ml,
            "image_url": b.image_url,
            "active": b.active
        })
    
    return {"beverages": beverage_list}


@router.get("/{beverage_id}", response_model=BeverageResponse)
async def get_beverage(
    beverage_id: str,
    db: Session = Depends(get_db)
):
    """Obtém bebida por ID"""
    beverage = db.query(Beverage).filter(Beverage.id == beverage_id).first()
    
    if not beverage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Beverage not found"
        )
    
    return beverage


@router.post("", response_model=BeverageResponse, status_code=status.HTTP_201_CREATED)
async def create_beverage(
    beverage_data: BeverageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cria nova bebida (admin)"""
    # Usa organização do usuário se não especificada
    org_id = beverage_data.organization_id or current_user.organization_id
    
    beverage = Beverage(
        organization_id=org_id,
        name=beverage_data.name,
        style=beverage_data.style,
        description=beverage_data.description,
        abv=beverage_data.abv,
        price_per_ml=beverage_data.price_per_ml,
        image_url=beverage_data.image_url,
        display_order=beverage_data.display_order,
    )
    
    db.add(beverage)
    db.commit()
    db.refresh(beverage)
    
    return beverage


@router.put("/{beverage_id}", response_model=BeverageResponse)
async def update_beverage(
    beverage_id: str,
    beverage_data: BeverageUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Atualiza bebida (admin)"""
    beverage = db.query(Beverage).filter(
        Beverage.id == beverage_id,
        Beverage.organization_id == current_user.organization_id
    ).first()
    
    if not beverage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Beverage not found"
        )
    
    # Atualiza campos fornecidos
    update_data = beverage_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(beverage, field, value)
    
    db.commit()
    db.refresh(beverage)
    
    return beverage


@router.delete("/{beverage_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_beverage(
    beverage_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove bebida (admin) - soft delete"""
    beverage = db.query(Beverage).filter(
        Beverage.id == beverage_id,
        Beverage.organization_id == current_user.organization_id
    ).first()
    
    if not beverage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Beverage not found"
        )
    
    # Soft delete
    beverage.active = False
    db.commit()
    
    return None
