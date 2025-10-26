#!/usr/bin/env python3
"""
Cria planos de manutenção preventiva por equipamento nos intervalos:
250h, 500h, 750h, 1000h, 2000h e 4000h.
Vincula ações e materiais cadastrados previamente (seed_preventive_materials.py).
Idempotente: não duplica planos já existentes.
"""
import os
import sys
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.equipment import Equipment
from app.models.maintenance import MaintenancePlan, MaintenancePlanAction, MaintenancePlanMaterial
from app.models.warehouse import Material

INTERVALS = [250, 500, 750, 1000, 2000, 4000]

ACTIONS_TEMPLATE = [
    {"description": "Inspecionar níveis e vazamentos", "action_type": "Inspeção", "estimated_time_minutes": 30},
    {"description": "Trocar óleo do motor", "action_type": "Troca", "estimated_time_minutes": 60},
    {"description": "Inspecionar e limpar filtros", "action_type": "Inspeção", "estimated_time_minutes": 40},
    {"description": "Lubrificar pontos críticos", "action_type": "Lubrificação", "estimated_time_minutes": 20},
    {"description": "Verificar correias e mangueiras", "action_type": "Inspeção", "estimated_time_minutes": 30},
]

# Mapeamento básico de materiais por intervalo
MATERIALS_BY_INTERVAL = {
    250: [
        ("Filtro de Óleo", 1, "UN", True),
        ("Filtro de Combustível", 1, "UN", True),
        ("Óleo Motor 15W40", 8, "L", True),
        ("Graxa Multiuso EP2", 1, "KG", False),
    ],
    500: [
        ("Filtro de Ar", 1, "UN", True),
        ("Filtro Hidráulico", 1, "UN", True),
        ("Óleo Hidráulico ISO68", 20, "L", True),
        ("Óleo Motor 15W40", 8, "L", False),
    ],
    750: [
        ("Mangueira Hidráulica Alta", 3, "M", False),
        ("Correia Alternador", 1, "UN", False),
        ("Óleo Motor 15W40", 8, "L", False),
        ("Graxa Multiuso EP2", 1, "KG", False),
    ],
    1000: [
        ("Óleo Transmissão ATF", 10, "L", True),
        ("Mangueira Hidráulica Baixa", 3, "M", False),
        ("Correia Ventilador", 1, "UN", False),
        ("Filtro de Ar", 1, "UN", True),
    ],
    2000: [
        ("Filtro Hidráulico", 1, "UN", True),
        ("Óleo Hidráulico ISO68", 30, "L", True),
        ("Filtro de Combustível", 1, "UN", True),
        ("Graxa Multiuso EP2", 2, "KG", False),
    ],
    4000: [
        ("Filtro de Óleo", 1, "UN", True),
        ("Filtro de Ar", 1, "UN", True),
        ("Óleo Motor 15W40", 10, "L", True),
        ("Óleo Transmissão ATF", 10, "L", True),
        ("Correia Alternador", 1, "UN", False),
        ("Correia Ventilador", 1, "UN", False),
    ],
}


def find_material_by_name(db, name: str) -> Material:
    return db.query(Material).filter(Material.name == name).first()


def ensure_plan_for_equipment(db, equipment: Equipment, interval_value: int) -> MaintenancePlan:
    existing = db.query(MaintenancePlan).filter(
        MaintenancePlan.equipment_id == equipment.id,
        MaintenancePlan.type == "Preventiva",
        MaintenancePlan.interval_type == "Horímetro",
        MaintenancePlan.interval_value == interval_value,
    ).first()
    if existing:
        return existing

    plan = MaintenancePlan(
        name=f"Plano {interval_value}h - {equipment.prefix}",
        equipment_id=equipment.id,
        type="Preventiva",
        interval_type="Horímetro",
        interval_value=interval_value,
        description=f"Plano de manutenção a cada {interval_value} horas",
        checklist_template={"items": ["Checar níveis", "Inspecionar vazamentos", "Limpeza geral"]},
        is_active=True,
        estimated_hours=4.0 if interval_value <= 500 else 6.0,
        priority="Normal",
        created_at=datetime.now(),
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def attach_actions(db, plan: MaintenancePlan):
    # Se já houver ações, não duplicar
    existing_actions = db.query(MaintenancePlanAction).filter(MaintenancePlanAction.plan_id == plan.id).count()
    if existing_actions:
        return
    for idx, action in enumerate(ACTIONS_TEMPLATE, start=1):
        db.add(MaintenancePlanAction(
            plan_id=plan.id,
            description=action["description"],
            action_type=action["action_type"],
            sequence_order=idx,
            estimated_time_minutes=action["estimated_time_minutes"],
            requires_specialist=False,
            safety_notes="",
        ))
    db.commit()


def attach_materials(db, plan: MaintenancePlan, interval_value: int):
    # Se já houver materiais, não duplicar
    existing_mats = db.query(MaintenancePlanMaterial).filter(MaintenancePlanMaterial.plan_id == plan.id).count()
    if existing_mats:
        return
    items = MATERIALS_BY_INTERVAL.get(interval_value, [])
    for name, qty, unit, is_critical in items:
        m = find_material_by_name(db, name)
        if not m:
            print(f"⚠️ Material '{name}' não encontrado para {plan.name}; pulando vínculo.")
            continue
        db.add(MaintenancePlanMaterial(
            plan_id=plan.id,
            material_id=m.id,
            quantity=float(qty),
            unit=unit,
            is_critical=is_critical,
        ))
    db.commit()


def main():
    db = SessionLocal()
    try:
        equipments = db.query(Equipment).all()
        if not equipments:
            print("❌ Nenhum equipamento encontrado. Execute primeiro seed_equipments_5_br.py.")
            return
        total_created = 0
        for eq in equipments:
            for iv in INTERVALS:
                plan = ensure_plan_for_equipment(db, eq, iv)
                attach_actions(db, plan)
                attach_materials(db, plan, iv)
                # Contabilizar somente criação de novos planos
                if plan.created_at and (datetime.now() - plan.created_at).seconds < 5:
                    total_created += 1
        count_plans = db.query(MaintenancePlan).count()
        print(f"✅ Planos processados. Novos criados: {total_created}")
        print(f"📊 Total de planos: {count_plans}")
    except Exception as e:
        db.rollback()
        print(f"❌ Erro ao criar planos: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    main()