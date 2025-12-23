"""
🎯 Configuração Centralizada - BierPass
Define caminhos absolutos e configurações globais
"""

from pathlib import Path
import os

# Base path - sempre absoluto
PROJECT_ROOT = Path(__file__).parent.absolute()

# Banco de dados - sempre no root
DATABASE_PATH = PROJECT_ROOT / "bierpass.db"
EDGE_DATABASE_PATH = PROJECT_ROOT / "edge-server" / "edge_data.db"

# Diretórios
EDGE_DIR = PROJECT_ROOT / "edge-server"
SAAS_DIR = PROJECT_ROOT / "saas-backend"
FRONTEND_DIR = PROJECT_ROOT / "app-kiosk"

# URLs
EDGE_URL = "http://localhost:5000"
SAAS_URL = "http://localhost:3001"
FRONTEND_URL = "http://localhost:8080/app-kiosk"

# Portas
EDGE_PORT = 5000
SAAS_PORT = 3001
FRONTEND_PORT = 8080

# Modo debug
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Variáveis de ambiente para subprocessos
ENV_VARS = {
    "DATABASE_PATH": str(DATABASE_PATH),
    "EDGE_DATABASE_PATH": str(EDGE_DATABASE_PATH),
    "PROJECT_ROOT": str(PROJECT_ROOT),
    "PYTHONUNBUFFERED": "1",
}

print(f"🔧 BierPass Configuration")
print(f"   PROJECT_ROOT: {PROJECT_ROOT}")
print(f"   DATABASE: {DATABASE_PATH}")
print(f"   EDGE DB: {EDGE_DATABASE_PATH}")
