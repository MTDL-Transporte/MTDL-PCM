#!/usr/bin/env python3
"""
Semeia 5 equipamentos por categoria com os prefixos BRxx/A101..A105.
Atende às regras: status 'ativo', horímetro inicial 0, mobilização 2025-01-01.
"""
import os
import sys
from datetime import datetime
from random import choice, randint

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.equipment import Equipment

CATEGORIES_PREFIXES = {
    "Retroescavadeira": "BR30",
    "Pá Carregadeira": "BR31",
    "Rolo Compactador": "BR44",
    "Motoniveladora": "BR32",
    "Perfuratriz": "BR120",
    "Betoneira": "BR260",
    "Usina de Asfalto": "BR10",
    "Caminhões": "BR90",
    "Tratores": "BR33",
    "Guindastes": "BR370",
    "Geradores": "BR11",
    "Outros": "BR01",
}

MANUFACTURERS = ["Caterpillar", "Volvo", "John Deere", "Komatsu", "JCB", "Case", "Sany", "Scania"]
LOCATIONS = ["Obra A", "Obra B", "Pátio Central", "Mina 1", "Mina 2", "Planta"]


def seed_5_per_category():
    db = SessionLocal()
    created = 0
    try:
        for category, br in CATEGORIES_PREFIXES.items():
            for i in range(1, 6):  # A101..A105
                suffix = f"A10{i}"
                prefix = f"{br}/{suffix}"
                # Evitar duplicidade
                exists = db.query(Equipment).filter(Equipment.prefix == prefix).first()
                if exists:
                    continue
                eq = Equipment(
                    prefix=prefix,
                    name=f"{category} {prefix}",
                    model=f"Modelo {randint(100,999)}",
                    manufacturer=choice(MANUFACTURERS),
                    year=randint(2014, 2024),
                    serial_number=f"SN-{br}-{randint(10000,99999)}",
                    cost_center="CC-MNT",
                    company_name="BR",
                    status="ativo",  # necessário para módulo de abastecimento
                    mobilization_date=datetime(2025, 1, 1),
                    initial_horimeter=0.0,
                    current_horimeter=0.0,
                    equipment_class=("Linha Amarela" if category not in ["Caminhões", "Outros", "Geradores"] else "Linha Branca"),
                    category=category,
                    fleet="Propria",
                    monthly_quota=randint(160, 220),
                    location=choice(LOCATIONS),
                    description=f"Cadastro automático conforme regra de prefixos para {category}."
                )
                db.add(eq)
                created += 1
        db.commit()
        print(f"✅ Equipamentos criados: {created}")
        total = db.query(Equipment).count()
        print(f"📊 Total de equipamentos: {total}")
    except Exception as e:
        db.rollback()
        print(f"❌ Erro ao semear equipamentos: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_5_per_category()