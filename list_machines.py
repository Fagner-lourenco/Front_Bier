"""
Lista todas as máquinas cadastradas no SaaS
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saas-backend'))

from app.database import SessionLocal
from app.models import Machine

def list_machines():
    db = SessionLocal()
    try:
        machines = db.query(Machine).all()
        
        if not machines:
            print("❌ Nenhuma máquina cadastrada!")
            return
        
        print(f"📋 Máquinas cadastradas no SaaS:\n")
        for m in machines:
            print(f"✅ {m.code} - {m.name}")
            print(f"   ID: {m.id}")
            print(f"   API Key: {m.api_key}")
            print(f"   HMAC Secret: {m.hmac_secret}")
            print(f"   Organization: {m.organization_id}")
            print(f"   Active: {m.active}")
            print()
            
    finally:
        db.close()

if __name__ == "__main__":
    list_machines()
