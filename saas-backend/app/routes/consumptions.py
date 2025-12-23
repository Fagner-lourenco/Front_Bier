"""
Endpoints para consumptions (registros de dispensa)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Consumption, Sale, Machine
from ..schemas import ConsumptionCreate, ConsumptionResponse

router = APIRouter()


@router.post("/api/v1/consumptions", response_model=ConsumptionResponse)
async def create_consumption(
    consumption_data: ConsumptionCreate,
    db: Session = Depends(get_db)
):
    """
    Registra uma dispensa de bebida
    """
    try:
        # Validações
        if not consumption_data.sale_id:
            raise HTTPException(status_code=400, detail="sale_id é obrigatório")
        
        if not consumption_data.machine_id:
            raise HTTPException(status_code=400, detail="machine_id é obrigatório")
        
        # Verifica se sale existe
        sale = db.query(Sale).filter(Sale.id == consumption_data.sale_id).first()
        if not sale:
            raise HTTPException(status_code=404, detail="Sale não encontrada")
        
        # Verifica se machine existe
        machine = db.query(Machine).filter(Machine.id == consumption_data.machine_id).first()
        if not machine:
            raise HTTPException(status_code=404, detail="Machine não encontrada")
        
        # Cria consumption
        consumption = Consumption(
            sale_id=consumption_data.sale_id,
            machine_id=consumption_data.machine_id,
            dispensed_at=consumption_data.dispensed_at,
            status=consumption_data.status or "completed"
        )
        
        db.add(consumption)
        db.commit()
        db.refresh(consumption)
        
        return consumption
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao criar consumption: {str(e)}")


@router.get("/api/v1/consumptions/{consumption_id}", response_model=ConsumptionResponse)
async def get_consumption(
    consumption_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtém detalhes de um consumption específico
    """
    consumption = db.query(Consumption).filter(
        Consumption.id == consumption_id
    ).first()
    
    if not consumption:
        raise HTTPException(status_code=404, detail="Consumption não encontrada")
    
    return consumption


@router.get("/api/v1/consumptions")
async def list_consumptions(
    sale_id: int = None,
    machine_id: int = None,
    db: Session = Depends(get_db)
):
    """
    Lista consumptions com filtros opcionais
    """
    query = db.query(Consumption)
    
    if sale_id:
        query = query.filter(Consumption.sale_id == sale_id)
    
    if machine_id:
        query = query.filter(Consumption.machine_id == machine_id)
    
    consumptions = query.all()
    return consumptions
