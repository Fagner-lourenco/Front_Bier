"""
Rotas: Health Check
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime

from ..database import get_db

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """Health check simples"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "bierpass-saas"
    }


@router.get("/health/db")
async def health_check_db(db: Session = Depends(get_db)):
    """Health check com verificação do banco"""
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy" if db_status == "connected" else "unhealthy",
        "timestamp": datetime.utcnow().isoformat(),
        "database": db_status
    }
