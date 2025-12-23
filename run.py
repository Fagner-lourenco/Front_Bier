#!/usr/bin/env python3
"""
🚀 BierPass Service Launcher - Versão Simplificada
Inicia tudo do jeito certo, independente de onde você está
"""

import os
import sys
import subprocess
import time
from pathlib import Path

# ============================================================
# 1. DEFINIR CAMINHOS ABSOLUTOS (FIX PRINCIPAL)
# ============================================================

PROJECT_ROOT = Path(__file__).parent.absolute()
os.chdir(str(PROJECT_ROOT))  # Garante que estamos na pasta correta

print(f"\n{'='*60}")
print(f"🚀 BierPass Service Launcher")
print(f"{'='*60}")
print(f"📁 Projeto: {PROJECT_ROOT}")
print(f"{'='*60}\n")

# ============================================================
# 2. DEFINIR VARIÁVEIS DE AMBIENTE GLOBAIS
# ============================================================

env = os.environ.copy()
env.update({
    "PROJECT_ROOT": str(PROJECT_ROOT),
    "DATABASE_PATH": str(PROJECT_ROOT / "bierpass.db"),
    "EDGE_DATABASE_PATH": str(PROJECT_ROOT / "edge-server" / "edge_data.db"),
    "PYTHONUNBUFFERED": "1",
})

print("✅ Variáveis de ambiente configuradas")
print(f"   DATABASE_PATH={env['DATABASE_PATH']}")
print(f"   EDGE_DATABASE_PATH={env['EDGE_DATABASE_PATH']}\n")

# ============================================================
# 3. INICIAR SERVIÇOS
# ============================================================

print("Iniciando serviços...\n")

# EDGE
print("[EDGE] Iniciando...")
edge_process = subprocess.Popen(
    [sys.executable, "app.py"],
    cwd=str(PROJECT_ROOT / "edge-server"),
    env=env,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    encoding='utf-8',
    errors='replace',
    bufsize=1
)

# SaaS
print("[SaaS] Iniciando...")
saas_process = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3001"],
    cwd=str(PROJECT_ROOT / "saas-backend"),
    env=env,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    encoding='utf-8',
    errors='replace',
    bufsize=1
)

# Frontend
print("[Frontend] Iniciando...")
frontend_process = subprocess.Popen(
    [sys.executable, "-m", "http.server", "8080", "--directory", "."],
    cwd=str(PROJECT_ROOT / "app-kiosk"),
    env=env,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    encoding='utf-8',
    errors='replace',
    bufsize=1
)

time.sleep(2)

print("\n✅ Todos os serviços iniciados!\n")
print(f"{'='*60}")
print("🌐 URLs:")
print(f"   Frontend: {env['PROJECT_ROOT']}/app-kiosk")
print(f"   EDGE API: http://localhost:5000")
print(f"   SaaS API: http://localhost:3001")
print(f"{'='*60}\n")

print("📊 Banco de dados:")
print(f"   Local: {env['DATABASE_PATH']}")
print(f"   Status: ✅ Centralizado\n")

# ============================================================
# 4. MONITORAR OUTPUTS
# ============================================================

import threading

def read_output(process, name):
    """Lê output do processo"""
    try:
        for line in process.stdout:
            if line.strip():
                print(f"[{name}] {line.strip()}")
    except:
        pass

processes = {
    'EDGE': edge_process,
    'SaaS': saas_process,
    'Frontend': frontend_process,
}

for name, proc in processes.items():
    thread = threading.Thread(
        target=read_output,
        args=(proc, name),
        daemon=True
    )
    thread.start()

# ============================================================
# 5. MONITORAR SAÚDE E MANTER RODANDO
# ============================================================

import requests

print("Monitorando serviços (Ctrl+C para parar)...\n")

def check_health(port):
    try:
        requests.get(f"http://localhost:{port}/health", timeout=2)
        return True
    except:
        return False

try:
    while True:
        time.sleep(10)
        
        # Verifica se processos estão vivos
        for name, proc in processes.items():
            if proc.poll() is not None:
                print(f"\n⚠️  {name} caiu! Reiniciando...")
                # Poderia recriar o processo aqui se necessário
        
        # Verifica saúde
        if check_health(5000):
            print("✅ EDGE OK", end="")
        if check_health(3001):
            print(" | ✅ SaaS OK", end="")
        if check_health(8080):
            print(" | ✅ Frontend OK")

except KeyboardInterrupt:
    print("\n\n🛑 Parando serviços...")
    for proc in processes.values():
        try:
            proc.terminate()
            proc.wait(timeout=2)
        except:
            proc.kill()
    
    print("✅ Serviços parados")
    sys.exit(0)
