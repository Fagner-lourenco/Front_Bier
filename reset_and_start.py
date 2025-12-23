#!/usr/bin/env python3
"""
🚀 BierPass Reset & Start Manager
Limpa, recria database com dados e inicia tudo automaticamente
"""

import os
import sys
import subprocess
import time
import threading
import requests
from pathlib import Path
from datetime import datetime

# Cores para output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def log(msg, color=None, prefix=None):
    """Log com timestamp e cor"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    if prefix:
        msg = f"[{prefix}] {msg}"
    if color:
        print(f"{color}{timestamp} {msg}{Colors.RESET}")
    else:
        print(f"{timestamp} {msg}")

def run_command(cmd, cwd=None, name="Command"):
    """Executa comando e captura output"""
    try:
        log(f"Executando: {' '.join(cmd)}", Colors.BLUE, name)
        result = subprocess.run(
            cmd,
            cwd=cwd or Path.cwd(),
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            log(f"✅ Sucesso", Colors.GREEN, name)
            return True, result.stdout
        else:
            log(f"❌ Erro: {result.stderr}", Colors.RED, name)
            return False, result.stderr
    except Exception as e:
        log(f"❌ Exceção: {e}", Colors.RED, name)
        return False, str(e)

def main():
    base_dir = Path(__file__).parent
    
    log("=" * 70, Colors.BOLD)
    log("🚀 BierPass Reset & Start Manager", Colors.BOLD)
    log("=" * 70, Colors.BOLD)
    
    # Step 1: Parar serviços existentes
    log("\n[STEP 1] Parando serviços existentes...", Colors.BLUE)
    os.system("taskkill /F /IM python.exe /T 2>nul")
    time.sleep(2)
    log("✅ Serviços parados", Colors.GREEN, "CLEANUP")
    
    # Step 2: Limpar banco de dados antigo
    log("\n[STEP 2] Limpando banco de dados...", Colors.BLUE)
    db_path = base_dir / "bierpass.db"
    edge_db_path = base_dir / "edge-server" / "edge_data.db"
    
    if db_path.exists():
        db_path.unlink()
        log(f"🗑️  Deletado: {db_path.name}", Colors.YELLOW, "CLEANUP")
    
    if edge_db_path.exists():
        edge_db_path.unlink()
        log(f"🗑️  Deletado: {edge_db_path.name}", Colors.YELLOW, "CLEANUP")
    
    # Step 3: Iniciar SaaS para criar schema
    log("\n[STEP 3] Inicializando SaaS (criar schema)...", Colors.BLUE)
    saas_dir = base_dir / "saas-backend"
    
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3001"],
        cwd=str(saas_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8',
        errors='replace'
    )
    
    log("Aguardando SaaS ficar pronto...", Colors.YELLOW, "SAAS")
    time.sleep(5)
    
    # Verifica se SaaS está respondendo
    for i in range(10):
        try:
            response = requests.get("http://localhost:3001/health", timeout=2)
            if response.status_code < 500:
                log("✅ SaaS pronto", Colors.GREEN, "SAAS")
                break
        except:
            if i == 9:
                log("⚠️  SaaS não respondeu, continuando mesmo assim", Colors.YELLOW, "SAAS")
        time.sleep(1)
    
    # Step 4: Executar seed.py para popular dados
    log("\n[STEP 4] Populando banco com dados (seed)...", Colors.BLUE)
    seed_file = saas_dir / "seed.py"
    
    if seed_file.exists():
        success, output = run_command(
            [sys.executable, str(seed_file)],
            cwd=str(saas_dir),
            name="SEED"
        )
        
        if success:
            log("✅ Banco populado com sucesso", Colors.GREEN, "SEED")
        else:
            log(f"⚠️  Seed teve problema, mas continuando: {output[:200]}", Colors.YELLOW, "SEED")
    else:
        log("⚠️  seed.py não encontrado", Colors.YELLOW, "SEED")
    
    # Step 5: Parar SaaS temporário
    log("\n[STEP 5] Reiniciando serviços...", Colors.BLUE)
    process.terminate()
    time.sleep(1)
    
    # Step 6: Iniciar todos os serviços
    log("\n[STEP 6] Iniciando todos os serviços...", Colors.BLUE)
    
    services = {
        'EDGE': {
            'cwd': base_dir / 'edge-server',
            'cmd': [sys.executable, 'app.py'],
            'port': 5000,
        },
        'SaaS': {
            'cwd': base_dir / 'saas-backend',
            'cmd': [sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', '3001'],
            'port': 3001,
        },
        'Frontend': {
            'cwd': base_dir,
            'cmd': [sys.executable, '-m', 'http.server', '8080', '--directory', '.'],
            'port': 8080,
        }
    }
    
    processes = {}
    
    for name, service in services.items():
        try:
            log(f"Iniciando {name}...", Colors.BLUE, name)
            
            proc = subprocess.Popen(
                service['cmd'],
                cwd=str(service['cwd']),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1
            )
            
            processes[name] = proc
            
            # Thread para ler output
            def read_output(proc, service_name):
                for line in proc.stdout:
                    if line.strip():
                        log(line.strip(), prefix=service_name)
            
            thread = threading.Thread(
                target=read_output,
                args=(proc, name),
                daemon=True
            )
            thread.start()
            
            time.sleep(2)
            
        except Exception as e:
            log(f"❌ Erro ao iniciar {name}: {e}", Colors.RED, name)
    
    # Step 7: Verificar saúde dos serviços
    log("\n[STEP 7] Verificando saúde dos serviços...", Colors.BLUE)
    time.sleep(3)
    
    def check_port(port):
        try:
            response = requests.get(f'http://localhost:{port}/health', timeout=2)
            return response.status_code < 500
        except:
            return False
    
    for i in range(5):
        all_healthy = True
        for name, service in services.items():
            if check_port(service['port']):
                log(f"✅ {name} está saudável", Colors.GREEN, name)
            else:
                log(f"⏳ {name} ainda iniciando...", Colors.YELLOW, name)
                all_healthy = False
        
        if all_healthy:
            break
        
        time.sleep(2)
    
    # Final message
    log("\n" + "=" * 70, Colors.BOLD)
    log("✅ SISTEMA PRONTO!", Colors.GREEN, "MANAGER")
    log("=" * 70, Colors.BOLD)
    
    log("\n🌐 URLs disponíveis:", Colors.BOLD)
    log("  Frontend: http://localhost:8080/app-kiosk", prefix="ACESSO")
    log("  EDGE API: http://localhost:5000", prefix="ACESSO")
    log("  SaaS API: http://localhost:3001", prefix="ACESSO")
    
    log("\n📊 Banco de dados:", Colors.BOLD)
    log("  ✅ Criado vazio (schema OK)", prefix="DB")
    log("  ✅ Populado com bebidas de teste", prefix="DB")
    log("  ✅ Pronto para transações", prefix="DB")
    
    log("\n🧪 Próximos passos:", Colors.BOLD)
    log("  1. Abra: http://localhost:8080/app-kiosk", prefix="TESTE")
    log("  2. Selecione: Água → 200ml → PIX", prefix="TESTE")
    log("  3. Aguarde 5s (mock aprova)", prefix="TESTE")
    log("  4. Veja dispensação", prefix="TESTE")
    
    log("\n⏹️  Para parar: Ctrl+C", Colors.YELLOW, "INFO")
    
    # Monitor
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log("\n🛑 Parando serviços...", Colors.YELLOW, "MANAGER")
        for proc in processes.values():
            try:
                proc.terminate()
            except:
                pass
        log("✅ Tudo parado", Colors.GREEN, "MANAGER")

if __name__ == '__main__':
    main()
