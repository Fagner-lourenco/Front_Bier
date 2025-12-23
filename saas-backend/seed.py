"""
Seed: Dados iniciais para desenvolvimento
Cria organização, usuário, máquina e bebidas de teste
"""
import sys
import os

# Adiciona o diretório pai ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine, Base
from app.models import Organization, User, Machine, Beverage
from app.utils.auth import get_password_hash


def seed_database():
    """Popula banco com dados de desenvolvimento"""
    
    # Cria tabelas
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        # Verifica se já existe dados
        existing_org = db.query(Organization).first()
        if existing_org:
            print("⚠️  Banco já possui dados. Seed ignorado.")
            print(f"   Organização: {existing_org.name}")
            
            # Mostra API Key da máquina para facilitar testes
            machine = db.query(Machine).filter(Machine.organization_id == existing_org.id).first()
            if machine:
                print(f"   Máquina: {machine.code}")
                print(f"   API Key: {machine.api_key}")
            return
        
        print("🌱 Criando dados de seed...")
        
        # 1. Organização
        org = Organization(
            name="BierPass Demo",
            slug="bierpass-demo",
            email="demo@bierpass.com.br",
            phone="(11) 99999-9999",
            city="São Paulo",
            state="SP",
            plan="pro"
        )
        db.add(org)
        db.flush()
        print(f"✅ Organização criada: {org.name}")
        
        # 2. Usuário Admin
        admin = User(
            organization_id=org.id,
            email="admin@bierpass.com.br",
            password_hash=get_password_hash("admin123"),
            name="Administrador",
            role="admin"
        )
        db.add(admin)
        print(f"✅ Usuário criado: {admin.email} (senha: admin123)")
        
        # 3. Máquina
        machine = Machine(
            organization_id=org.id,
            code="M001",
            name="Kiosk Principal",
            location="Loja Centro",
            address="Av. Paulista, 1000 - São Paulo/SP"
        )
        db.add(machine)
        db.flush()
        print(f"✅ Máquina criada: {machine.code}")
        print(f"   API Key: {machine.api_key}")
        print(f"   HMAC Secret: {machine.hmac_secret}")
        
        # 4. Bebidas
        beverages = [
            {
                "name": "Chopp Pilsen",
                "style": "Pilsen",
                "description": "Chopp claro e refrescante",
                "abv": 4.5,
                "price_per_ml": 0.04,
                "image_url": "assets/images/beverages/chopp.png",
                "display_order": 1
            },
            {
                "name": "Chopp IPA",
                "style": "IPA",
                "description": "India Pale Ale com notas cítricas",
                "abv": 6.5,
                "price_per_ml": 0.06,
                "image_url": "assets/images/beverages/ipa.png",
                "display_order": 2
            },
            {
                "name": "Água de Coco",
                "style": "Natural",
                "description": "Água de coco natural gelada",
                "abv": 0.0,
                "price_per_ml": 0.03,
                "image_url": "assets/images/beverages/agua-coco.png",
                "display_order": 3
            },
            {
                "name": "Suco de Laranja",
                "style": "Natural",
                "description": "Suco de laranja 100% natural",
                "abv": 0.0,
                "price_per_ml": 0.035,
                "image_url": "assets/images/beverages/suco-laranja.png",
                "display_order": 4
            }
        ]
        
        beverage_ids = []
        for bev_data in beverages:
            bev = Beverage(organization_id=org.id, **bev_data)
            db.add(bev)
            db.flush()
            beverage_ids.append({"id": bev.id, "name": bev.name})
            print(f"✅ Bebida criada: {bev.name} (ID: {bev.id})")
        
        db.commit()
        
        print("\n" + "=" * 50)
        print("🎉 SEED CONCLUÍDO COM SUCESSO!")
        print("=" * 50)
        print("\n📋 DADOS PARA CONFIGURAR O APP:")
        print(f"\n   saas_url: http://localhost:3001")
        print(f"   machine_id: M001")
        print(f"   api_key: {machine.api_key}")
        print(f"\n🔐 LOGIN ADMIN:")
        print(f"   Email: admin@bierpass.com.br")
        print(f"   Senha: admin123")
        print(f"\n🍺 BEBIDAS:")
        for bev in beverage_ids:
            print(f"   - {bev['name']}: {bev['id']}")
        print()
        
    except Exception as e:
        print(f"❌ Erro no seed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
