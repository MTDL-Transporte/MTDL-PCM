#!/usr/bin/env python3
"""
Script para criar planos de manutenção baseados em horímetro
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from sqlalchemy import text

def create_horimeter_plans():
    """Criar planos de manutenção baseados em horímetro"""
    db = SessionLocal()
    
    try:
        # Buscar equipamentos disponíveis
        equipments = db.execute(text("SELECT id, prefix, name FROM equipments LIMIT 3")).fetchall()
        
        if not equipments:
            print("❌ Nenhum equipamento encontrado. Execute primeiro o script create_sample_data.py")
            return
        
        # Verificar se já existem planos baseados em horímetro
        result = db.execute(text("SELECT COUNT(*) FROM maintenance_plans WHERE interval_type = 'Horímetro'")).fetchone()
        
        if result[0] == 0:
            # Criar planos baseados em horímetro
            horimeter_plans = [
                {
                    "name": "Troca de Óleo - 250h",
                    "equipment_id": equipments[0][0],
                    "type": "Preventiva",
                    "interval_type": "Horímetro",
                    "interval_value": 250,
                    "description": "Troca de óleo do motor e filtros a cada 250 horas",
                    "is_active": True,
                    "estimated_hours": 2.0,
                    "priority": "Alta"
                },
                {
                    "name": "Inspeção Geral - 500h",
                    "equipment_id": equipments[0][0],
                    "type": "Preventiva", 
                    "interval_type": "Horímetro",
                    "interval_value": 500,
                    "description": "Inspeção geral dos sistemas a cada 500 horas",
                    "is_active": True,
                    "estimated_hours": 4.0,
                    "priority": "Normal"
                }
            ]
            
            if len(equipments) > 1:
                horimeter_plans.append({
                    "name": "Manutenção Hidráulica - 1000h",
                    "equipment_id": equipments[1][0],
                    "type": "Preventiva",
                    "interval_type": "Horímetro", 
                    "interval_value": 1000,
                    "description": "Manutenção completa do sistema hidráulico a cada 1000 horas",
                    "is_active": True,
                    "estimated_hours": 8.0,
                    "priority": "Alta"
                })
            
            # Inserir planos
            for plan in horimeter_plans:
                db.execute(text("""
                    INSERT INTO maintenance_plans (
                        name, equipment_id, type, interval_type, interval_value,
                        description, is_active, estimated_hours, priority
                    ) VALUES (
                        :name, :equipment_id, :type, :interval_type, :interval_value,
                        :description, :is_active, :estimated_hours, :priority
                    )
                """), plan)
            
            db.commit()
            print("✅ Planos de manutenção por horímetro criados com sucesso!")
        else:
            print("ℹ️ Planos de manutenção por horímetro já existem")
        
        # Mostrar planos criados
        plans = db.execute(text("""
            SELECT mp.name, e.prefix, mp.interval_value, mp.priority
            FROM maintenance_plans mp
            JOIN equipments e ON mp.equipment_id = e.id
            WHERE mp.interval_type = 'Horímetro' AND mp.is_active = 1
            ORDER BY e.prefix, mp.interval_value
        """)).fetchall()
        
        print("\n🔧 Planos de manutenção por horímetro:")
        for plan in plans:
            print(f"  {plan[1]} - {plan[0]} | A cada {plan[2]}h | Prioridade: {plan[3]}")
        
        # Atualizar horímetros dos equipamentos para teste
        print("\n⏱️ Atualizando horímetros para teste...")
        for i, equipment in enumerate(equipments):
            # Definir horímetros que irão gerar alertas
            horimeter_values = [220, 480, 950]  # Próximos aos intervalos de manutenção
            if i < len(horimeter_values):
                db.execute(text("""
                    UPDATE equipments 
                    SET current_horimeter = :horimeter,
                        last_horimeter_update = CURRENT_TIMESTAMP
                    WHERE id = :equipment_id
                """), {
                    "horimeter": horimeter_values[i],
                    "equipment_id": equipment[0]
                })
                print(f"  {equipment[1]} - Horímetro: {horimeter_values[i]}h")
        
        db.commit()
        print("✅ Horímetros atualizados!")
        
    except Exception as e:
        print(f"❌ Erro ao criar planos de horímetro: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_horimeter_plans()