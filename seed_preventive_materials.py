#!/usr/bin/env python3
"""
Cria materiais típicos de manutenção preventiva (filtros, óleos, mangueiras, correias, graxa)
com estoque mínimo/máximo e preço unitário.
"""
import os
import sys
from random import uniform

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.warehouse import Material, StockMovement

MATERIALS = [
    {"name": "Filtro de Óleo", "category": "Peças", "unit": "UN", "unit_price": 48.90, "min": 80, "max": 400},
    {"name": "Filtro de Combustível", "category": "Peças", "unit": "UN", "unit_price": 65.50, "min": 80, "max": 400},
    {"name": "Filtro de Ar", "category": "Peças", "unit": "UN", "unit_price": 120.00, "min": 60, "max": 300},
    {"name": "Filtro Hidráulico", "category": "Peças", "unit": "UN", "unit_price": 180.00, "min": 50, "max": 300},
    {"name": "Óleo Motor 15W40", "category": "Lubrificantes", "unit": "L", "unit_price": 26.50, "min": 200, "max": 400},
    {"name": "Óleo Hidráulico ISO68", "category": "Lubrificantes", "unit": "L", "unit_price": 24.90, "min": 200, "max": 400},
    {"name": "Óleo Transmissão ATF", "category": "Lubrificantes", "unit": "L", "unit_price": 32.70, "min": 120, "max": 400},
    {"name": "Mangueira Hidráulica Alta", "category": "Peças", "unit": "M", "unit_price": 45.00, "min": 100, "max": 400},
    {"name": "Mangueira Hidráulica Baixa", "category": "Peças", "unit": "M", "unit_price": 32.00, "min": 120, "max": 400},
    {"name": "Correia Alternador", "category": "Peças", "unit": "UN", "unit_price": 75.00, "min": 60, "max": 300},
    {"name": "Correia Ventilador", "category": "Peças", "unit": "UN", "unit_price": 68.00, "min": 60, "max": 300},
    {"name": "Graxa Multiuso EP2", "category": "Lubrificantes", "unit": "KG", "unit_price": 18.00, "min": 150, "max": 400},
]


def ensure_materials():
    db = SessionLocal()
    created = 0
    try:
        for m in MATERIALS:
            exists = db.query(Material).filter(Material.name == m["name"]).first()
            if exists:
                continue
            # Gerar código numérico sequencial automaticamente através do endpoint interno
            # Aqui criamos manualmente seguindo o padrão já existente na API
            last = db.query(Material).order_by(Material.id.desc()).first()
            code = str(100000 + (last.id if last else 0) + 1)
            material = Material(
                code=code,
                name=m["name"],
                description=m["name"],
                category=m["category"],
                unit=m["unit"],
                current_stock=float(m["min"]),
                minimum_stock=float(m["min"]),
                maximum_stock=float(m["max"]),
                unit_price=float(m["unit_price"]),
                average_cost=float(m["unit_price"]),
                location="Almox. Central",
                is_active=True,
            )
            db.add(material)
            db.commit()
            db.refresh(material)
            # Uma entrada inicial para compor histórico
            db.add(StockMovement(
                material_id=material.id,
                type="Entrada",
                quantity=material.current_stock,
                unit_cost=material.unit_price,
                total_cost=material.unit_price * material.current_stock,
                previous_stock=0.0,
                new_stock=material.current_stock,
                reference_document="Cadastro Inicial",
                reason=f"Carga inicial de {material.name}",
                performed_by="Sistema",
            ))
            db.commit()
            created += 1
        print(f"✅ Materiais preventivos criados: {created}")
        total = db.query(Material).count()
        print(f"📊 Total de materiais: {total}")
    except Exception as e:
        db.rollback()
        print(f"❌ Erro ao criar materiais: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    ensure_materials()