import random
from datetime import datetime

from app.database import SessionLocal
from app.models.equipment import Equipment

BR_PREFIXES = {
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

MANUFACTURERS = ["Caterpillar", "Volvo", "Komatsu", "JCB", "Scania", "John Deere", "Wirtgen"]

COUNT_PER_CATEGORY = 10  # A101..A110


def seed_br_prefixes():
    s = SessionLocal()
    created = 0
    try:
        for category, base in BR_PREFIXES.items():
            for idx in range(101, 101 + COUNT_PER_CATEGORY):
                prefix = f"{base}/A{idx:03d}"
                exists = s.query(Equipment).filter(Equipment.prefix == prefix).first()
                if exists:
                    continue
                eq = Equipment(
                    prefix=prefix,
                    name=f"{category} {base} A{idx:03d}",
                    model=f"Modelo-{random.randint(100, 999)}",
                    manufacturer=random.choice(MANUFACTURERS),
                    year=random.randint(2015, 2024),
                    serial_number=f"SN-{random.randint(100000, 999999)}",
                    status="Ativo",
                    location="Obra Principal",
                    cost_center="CC-001",
                    description=f"Equipamento semeado com prefixo {base}/A{idx:03d}",
                    mobilization_date=datetime(2025, 1, 5),
                    initial_horimeter=0,
                    current_horimeter=0,
                    equipment_class=category,
                    monthly_quota=160.0,
                )
                s.add(eq)
                created += 1
        s.commit()
        print({"created": created})
    finally:
        s.close()


if __name__ == "__main__":
    seed_br_prefixes()