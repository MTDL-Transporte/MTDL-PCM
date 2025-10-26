import random
from datetime import datetime

from app.database import SessionLocal
from app.models.equipment import Equipment

CATEGORIES = [
    "Escavadeira Hidraulica",
    "Retroescavadeira",
    "Pá carregadeira",
    "Rolo compactador",
    "Motoniveladora",
    "Perfuratriz",
    "Betoneira",
    "Usina de asfalto",
    "Caminhões",
    "Tratores",
    "Outros",
]

PREFIX_MAP = {
    "Escavadeira Hidraulica": "ESC",
    "Retroescavadeira": "RET",
    "Pá carregadeira": "PAC",
    "Rolo compactador": "ROL",
    "Motoniveladora": "MOT",
    "Perfuratriz": "PER",
    "Betoneira": "BET",
    "Usina de asfalto": "USA",
    "Caminhões": "CAM",
    "Tratores": "TRA",
    "Outros": "OUT",
}

MANUFACTURERS = ["Caterpillar", "Volvo", "Komatsu", "JCB", "Scania", "John Deere", "Wirtgen"]


def seed_5_per_category():
    s = SessionLocal()
    created = 0
    try:
        for cat in CATEGORIES:
            prefix_seed = PREFIX_MAP[cat]
            for i in range(1, 6):
                prefix = f"{prefix_seed}-{i:03d}"
                exists = s.query(Equipment).filter(Equipment.prefix == prefix).first()
                if exists:
                    continue
                eq = Equipment(
                    prefix=prefix,
                    name=f"{cat} {i:03d}",
                    model=f"Modelo-{random.randint(100, 999)}",
                    manufacturer=random.choice(MANUFACTURERS),
                    year=random.randint(2018, 2024),
                    serial_number=f"SN-{random.randint(100000, 999999)}",
                    status="Ativo",
                    location="Obra Principal",
                    cost_center="CC-001",
                    description=f"Equipamento semeado para testes - {cat}",
                    mobilization_date=datetime(2025, 1, 5),
                    initial_horimeter=0,
                    current_horimeter=0,
                    equipment_class=cat,
                    monthly_quota=160.0,
                )
                s.add(eq)
                created += 1
        s.commit()
        print({"created": created})
    finally:
        s.close()


if __name__ == "__main__":
    seed_5_per_category()