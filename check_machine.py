"""
Verifica se a máquina está cadastrada no SaaS
"""
import sys
import os

# Adiciona path correto
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saas-backend'))

from app.database import SessionLocal
from app.models import Machine

MACHINE_ID = "40792dfc-828d-4f17-a3f2-3302396658e8"

def check_machine():
    db = SessionLocal()
    try:
        machine = db.query(Machine).filter(Machine.id == MACHINE_ID).first()
        
        if machine:
            print(f"✅ Máquina encontrada!")
            print(f"   ID: {machine.id}")
            print(f"   Code: {machine.code}")
            print(f"   Name: {machine.name}")
            print(f"   API Key: {machine.api_key}")
            print(f"   HMAC Secret: {machine.hmac_secret}")
            print(f"   Organization ID: {machine.organization_id}")
            print(f"   Active: {machine.active}")
            return True
        else:
            print(f"❌ Máquina {MACHINE_ID} NÃO encontrada no banco!")
            print(f"\n💡 Solução: Execute o seed para criar a máquina:")
            print(f"   cd saas-backend")
            print(f"   python seed.py")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao consultar banco: {e}")
        print(f"\n💡 Certifique-se de que o SaaS está configurado:")
        print(f"   cd saas-backend")
        print(f"   python -m uvicorn app.main:app --reload")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    check_machine()
