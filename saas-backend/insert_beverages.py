"""
Script para inserir bebidas no banco
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models import Organization, Beverage

db = SessionLocal()
org = db.query(Organization).first()
print(f'Org: {org.name} (ID: {org.id})')

# Verifica bebidas existentes
existing = db.query(Beverage).filter(Beverage.organization_id == org.id).all()
print(f'Bebidas existentes: {len(existing)}')

if len(existing) == 0:
    beverages = [
        {'name': 'Chopp Pilsen', 'style': 'Pilsen', 'description': 'Chopp claro e refrescante', 'abv': 4.5, 'price_per_ml': 0.04, 'image_url': 'assets/images/beverages/chopp.png', 'display_order': 1},
        {'name': 'Chopp IPA', 'style': 'IPA', 'description': 'India Pale Ale com notas citricas', 'abv': 6.5, 'price_per_ml': 0.06, 'image_url': 'assets/images/beverages/ipa.png', 'display_order': 2},
        {'name': 'Agua de Coco', 'style': 'Natural', 'description': 'Agua de coco natural gelada', 'abv': 0.0, 'price_per_ml': 0.03, 'image_url': 'assets/images/beverages/agua-coco.png', 'display_order': 3},
        {'name': 'Suco de Laranja', 'style': 'Natural', 'description': 'Suco de laranja 100% natural', 'abv': 0.0, 'price_per_ml': 0.035, 'image_url': 'assets/images/beverages/suco-laranja.png', 'display_order': 4}
    ]
    for b in beverages:
        bev = Beverage(organization_id=org.id, **b)
        db.add(bev)
        print(f'Adicionado: {b["name"]}')
    db.commit()
    print('Bebidas inseridas com sucesso!')
else:
    for b in existing:
        print(f'  - {b.name} (ID: {b.id}, active: {b.active})')

db.close()
