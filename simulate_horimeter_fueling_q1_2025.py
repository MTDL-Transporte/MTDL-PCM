#!/usr/bin/env python3
"""
Simula horímetro em dias úteis (Jan–Mar/2025), abastecimentos semanais
(DIESEL S10) e cria algumas paradas corretivas aleatórias.
Aciona preventivas via check_and_create_preventive_maintenance.
"""
import os
import sys
import random
import asyncio
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.equipment import Equipment, HorimeterLog
from app.models.warehouse import Material, Fueling, StockMovement
from app.models.maintenance import WorkOrder, TimeLog
from sqlalchemy import and_

WORKDAY_HOURS_RANGE = (6.0, 9.5)
FUELING_QTY_RANGE = (120.0, 300.0)
Q1_START = datetime(2025, 1, 1)
Q1_END = datetime(2025, 3, 31)

async def trigger_preventives(equipment: Equipment, db):
    from app.routers.maintenance import check_and_create_preventive_maintenance
    try:
        created = await check_and_create_preventive_maintenance(equipment, db)
        return created or []
    except Exception:
        return []


def find_fuel_material(db) -> Material:
    # Preferir DIESEL S10; fallback para qualquer combustível
    m = db.query(Material).filter(Material.name == "DIESEL S10").first()
    if m:
        return m
    return db.query(Material).filter(Material.category.ilike("%Combust%"), Material.is_active == True).first()


def simulate():
    db = SessionLocal()
    try:
        equipments = db.query(Equipment).filter(Equipment.status.in_(["ativo", "Operacional"])) .all()
        if not equipments:
            print("❌ Nenhum equipamento ativo encontrado. Execute seed_equipments_5_br.py primeiro.")
            return
        fuel_material = find_fuel_material(db)
        if not fuel_material:
            print("❌ Material de combustível não encontrado. Execute create_fuel_materials.py.")
            return

        total_days = 0
        total_fuelings = 0
        total_logs = 0
        preventive_orders = 0
        corrective_orders = 0

        current = Q1_START
        # Preparar mapa de última sexta-feira abastecida por equipamento
        last_fueling_week = {}

        while current <= Q1_END:
            is_workday = current.weekday() < 5  # 0=Mon .. 4=Fri
            for eq in equipments:
                prev = eq.current_horimeter or 0.0
                if is_workday:
                    hours = round(random.uniform(*WORKDAY_HOURS_RANGE), 1)
                    new_val = prev + hours
                    # Atualizar equipamento e log de horímetro
                    eq.current_horimeter = new_val
                    eq.last_horimeter_update = current
                    db.add(HorimeterLog(
                        equipment_id=eq.id,
                        previous_value=prev,
                        new_value=new_val,
                        difference=hours,
                        recorded_by="Simulação",
                        recorded_at=current,
                        notes=f"Incremento diário em {current.date()}"
                    ))
                    total_logs += 1
                    # Abastecimento uma vez por semana (sexta-feira)
                    if current.weekday() == 4:  # Friday
                        week_key = f"{eq.id}-{current.isocalendar().week}"
                        if last_fueling_week.get(week_key) is None:
                            qty = round(random.uniform(*FUELING_QTY_RANGE), 1)
                            unit_cost = fuel_material.unit_price or fuel_material.average_cost or 5.0
                            total_cost = qty * unit_cost
                            db.add(Fueling(
                                equipment_id=eq.id,
                                material_id=fuel_material.id,
                                date=current,
                                quantity=qty,
                                horimeter=new_val,
                                unit_cost=unit_cost,
                                total_cost=total_cost,
                                operator="Simulação",
                                notes="Abastecimento semanal"
                            ))
                            # Movimentação de estoque (saída)
                            prev_stock = fuel_material.current_stock or 0.0
                            new_stock = prev_stock - qty
                            fuel_material.current_stock = new_stock
                            db.add(StockMovement(
                                material_id=fuel_material.id,
                                type="Saída",
                                quantity=qty,
                                unit_cost=unit_cost,
                                total_cost=total_cost,
                                previous_stock=prev_stock,
                                new_stock=new_stock,
                                reference_document=f"AB-{eq.prefix}-{current.date()}",
                                reason=f"Abastecimento {eq.prefix}",
                                performed_by="Simulação",
                                date=current,
                                equipment_id=eq.id,
                                application="Abastecimento"
                            ))
                            total_fuelings += 1
                            last_fueling_week[week_key] = True
                    # Disparar preventivas conforme horímetro
                    created = asyncio.run(trigger_preventives(eq, db))
                    preventive_orders += len(created)
                    # Chance pequena de corretiva por falha aleatória
                    if random.random() < 0.015:  # ~1.5% por dia
                        # Criar OS corretiva simples
                        last = db.query(WorkOrder).order_by(WorkOrder.id.desc()).first()
                        next_number = 100000 if not last else int(last.number) + 1
                        wo = WorkOrder(
                            number=str(next_number),
                            title=f"Corretiva - Falha aleatória em {eq.prefix}",
                            description=f"Falha simulada em {current.date()} - ruído/vibração anormal",
                            priority=random.choice(["Normal", "Alta"]),
                            type="Corretiva",
                            maintenance_cause=random.choice(["Desgaste natural", "Falha operacional"]),
                            status="Fechada",
                            equipment_id=eq.id,
                            estimated_hours=4.0,
                            actual_hours=round(random.uniform(1.0, 6.0), 1),
                            cost=round(random.uniform(500.0, 2500.0), 2),
                            created_at=current,
                            started_at=current + timedelta(hours=1),
                            completed_at=current + timedelta(hours=6)
                        )
                        db.add(wo)
                        db.flush()
                        # Registrar time log
                        db.add(TimeLog(
                            work_order_id=wo.id,
                            technician="Equipe Simulação",
                            start_time=current + timedelta(hours=1),
                            end_time=current + timedelta(hours=6),
                            hours_worked=5.0,
                            activity_description="Diagnóstico e reparo corretivo",
                            date=current
                        ))
                        corrective_orders += 1
                # fim if is_workday
            # dia processado
            if is_workday:
                total_days += 1
            # commit ao final do dia
            db.commit()
            current += timedelta(days=1)

        print(f"✅ Simulação concluída Jan–Mar/2025")
        print(f"📅 Dias úteis processados: {total_days}")
        print(f"🛢️ Abastecimentos: {total_fuelings}")
        print(f"🕒 Logs de horímetro: {total_logs}")
        print(f"🛠️ Preventivas criadas: {preventive_orders}")
        print(f"🔧 Corretivas simuladas: {corrective_orders}")
    except Exception as e:
        db.rollback()
        print(f"❌ Erro na simulação: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    simulate()