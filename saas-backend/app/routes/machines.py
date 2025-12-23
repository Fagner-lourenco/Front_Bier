"""
Rotas: Machines (Máquinas)
CRUD para administradores
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import Machine, User
from ..schemas import MachineCreate, MachineUpdate, MachineResponse
from ..utils.auth import get_current_user

router = APIRouter(prefix="/machines", tags=["Machines"])


@router.get("", response_model=List[MachineResponse])
async def list_machines(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lista máquinas da organização (admin)"""
    machines = db.query(Machine).filter(
        Machine.organization_id == current_user.organization_id
    ).order_by(Machine.code).all()
    
    return machines


@router.get("/{machine_id}", response_model=MachineResponse)
async def get_machine(
    machine_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtém máquina por ID (admin)"""
    machine = db.query(Machine).filter(
        Machine.id == machine_id,
        Machine.organization_id == current_user.organization_id
    ).first()
    
    if not machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Machine not found"
        )
    
    return machine


@router.post("", response_model=MachineResponse, status_code=status.HTTP_201_CREATED)
async def create_machine(
    machine_data: MachineCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cria nova máquina (admin)"""
    # Verifica se código já existe na organização
    existing = db.query(Machine).filter(
        Machine.organization_id == current_user.organization_id,
        Machine.code == machine_data.code
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Machine with code {machine_data.code} already exists"
        )
    
    machine = Machine(
        organization_id=current_user.organization_id,
        code=machine_data.code,
        name=machine_data.name,
        location=machine_data.location,
        address=machine_data.address,
    )
    
    db.add(machine)
    db.commit()
    db.refresh(machine)
    
    return machine


@router.put("/{machine_id}", response_model=MachineResponse)
async def update_machine(
    machine_id: str,
    machine_data: MachineUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Atualiza máquina (admin)"""
    machine = db.query(Machine).filter(
        Machine.id == machine_id,
        Machine.organization_id == current_user.organization_id
    ).first()
    
    if not machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Machine not found"
        )
    
    update_data = machine_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(machine, field, value)
    
    db.commit()
    db.refresh(machine)
    
    return machine


@router.delete("/{machine_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_machine(
    machine_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove máquina (admin) - soft delete"""
    machine = db.query(Machine).filter(
        Machine.id == machine_id,
        Machine.organization_id == current_user.organization_id
    ).first()
    
    if not machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Machine not found"
        )
    
    machine.active = False
    db.commit()
    
    return None


@router.post("/{machine_id}/regenerate-key", response_model=MachineResponse)
async def regenerate_api_key(
    machine_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Regenera API Key da máquina (admin)"""
    from ..models.machine import generate_api_key
    
    machine = db.query(Machine).filter(
        Machine.id == machine_id,
        Machine.organization_id == current_user.organization_id
    ).first()
    
    if not machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Machine not found"
        )
    
    machine.api_key = generate_api_key()
    db.commit()
    db.refresh(machine)
    
    return machine
