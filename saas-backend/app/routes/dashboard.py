"""
Rotas: Dashboard
Métricas e relatórios para administradores
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db
from ..models import Sale, Consumption, Beverage, Machine, User
from ..schemas import DashboardMetrics, PeriodMetrics, BeverageMetrics, MachineMetrics
from ..utils.auth import get_current_user

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def get_period_metrics(db: Session, org_id: str, start_date: datetime, end_date: datetime) -> PeriodMetrics:
    """Calcula métricas para um período"""
    sales = db.query(Sale).filter(
        Sale.organization_id == org_id,
        Sale.created_at >= start_date,
        Sale.created_at <= end_date
    ).all()
    
    total_sales = len(sales)
    total_revenue = sum(s.total_value for s in sales)
    total_ml = sum(s.volume_ml for s in sales)
    
    # Taxa de sucesso baseada em consumos
    consumptions = db.query(Consumption).filter(
        Consumption.organization_id == org_id,
        Consumption.synced_at >= start_date,
        Consumption.synced_at <= end_date
    ).all()
    
    ok_count = sum(1 for c in consumptions if c.status == "OK")
    success_rate = (ok_count / len(consumptions) * 100) if consumptions else 100.0
    
    return PeriodMetrics(
        total_sales=total_sales,
        total_revenue=round(total_revenue, 2),
        total_ml=total_ml,
        average_ticket=round(total_revenue / total_sales, 2) if total_sales > 0 else 0,
        success_rate=round(success_rate, 1)
    )


@router.get("", response_model=DashboardMetrics)
async def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retorna métricas do dashboard
    
    Formato:
    {
      "today": { total_sales, total_revenue, total_ml, ... },
      "week": { ... },
      "month": { ... },
      "by_beverage": [...],
      "by_machine": [...]
    }
    """
    org_id = current_user.organization_id
    now = datetime.utcnow()
    
    # Períodos
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=now.weekday())
    month_start = today_start.replace(day=1)
    
    # Métricas por período
    today_metrics = get_period_metrics(db, org_id, today_start, now)
    week_metrics = get_period_metrics(db, org_id, week_start, now)
    month_metrics = get_period_metrics(db, org_id, month_start, now)
    
    # Métricas por bebida (mês)
    beverage_stats = db.query(
        Sale.beverage_id,
        func.count(Sale.id).label('count'),
        func.sum(Sale.total_value).label('revenue'),
        func.sum(Sale.volume_ml).label('ml')
    ).filter(
        Sale.organization_id == org_id,
        Sale.created_at >= month_start
    ).group_by(Sale.beverage_id).all()
    
    by_beverage = []
    for stat in beverage_stats:
        beverage = db.query(Beverage).filter(Beverage.id == stat.beverage_id).first()
        if beverage:
            by_beverage.append(BeverageMetrics(
                beverage_id=stat.beverage_id,
                beverage_name=beverage.name,
                total_sales=stat.count,
                total_revenue=round(float(stat.revenue or 0), 2),
                total_ml=int(stat.ml or 0)
            ))
    
    # Métricas por máquina (mês)
    machine_stats = db.query(
        Sale.machine_id,
        func.count(Sale.id).label('count'),
        func.sum(Sale.total_value).label('revenue'),
        func.sum(Sale.volume_ml).label('ml')
    ).filter(
        Sale.organization_id == org_id,
        Sale.created_at >= month_start
    ).group_by(Sale.machine_id).all()
    
    by_machine = []
    for stat in machine_stats:
        machine = db.query(Machine).filter(Machine.id == stat.machine_id).first()
        if machine:
            by_machine.append(MachineMetrics(
                machine_id=stat.machine_id,
                machine_code=machine.code,
                machine_name=machine.name,
                total_sales=stat.count,
                total_revenue=round(float(stat.revenue or 0), 2),
                total_ml=int(stat.ml or 0),
                status=machine.status
            ))
    
    return DashboardMetrics(
        today=today_metrics,
        week=week_metrics,
        month=month_metrics,
        by_beverage=by_beverage,
        by_machine=by_machine,
        generated_at=now
    )
