"""
BierPass SaaS Backend
API para gestão de máquinas dispensadoras de bebidas
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import engine, Base
from .routes import (
    health_router,
    auth_router,
    beverages_router,
    machines_router,
    sales_router,
    consumptions_router,
    dashboard_router,
    stocks_router,
)

# Cria tabelas no banco
Base.metadata.create_all(bind=engine)

# Cria app FastAPI
app = FastAPI(
    title="BierPass SaaS API",
    description="API para gestão de máquinas dispensadoras de bebidas",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins + ["*"],  # Permite tudo em dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rotas
app.include_router(health_router)  # /health (sem prefixo)
app.include_router(health_router, prefix=settings.api_v1_prefix)  # /api/v1/health
app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(beverages_router, prefix=settings.api_v1_prefix)
app.include_router(machines_router, prefix=settings.api_v1_prefix)
app.include_router(sales_router, prefix=settings.api_v1_prefix)
app.include_router(consumptions_router, prefix=f"{settings.api_v1_prefix}/consumptions")
app.include_router(dashboard_router, prefix=settings.api_v1_prefix)
app.include_router(stocks_router, prefix=settings.api_v1_prefix)


@app.get("/")
async def root():
    """Rota raiz"""
    return {
        "name": "BierPass SaaS API",
        "version": "1.0.0",
        "docs": "/docs" if settings.debug else "Disabled",
        "health": "/health"
    }


# Evento de startup
@app.on_event("startup")
async def startup_event():
    """Executado ao iniciar a aplicação"""
    print("=" * 50)
    print("🍺 BierPass SaaS API Starting...")
    print(f"📊 Debug Mode: {settings.debug}")
    print(f"🗄️  Database: {settings.database_url}")
    print(f"📚 Docs: http://localhost:3001/docs")
    print("=" * 50)
