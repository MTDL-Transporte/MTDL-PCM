#!/usr/bin/env python3
"""
Script para criar dados de amostra para testes do sistema de manutenção
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, engine
from sqlalchemy import text
from datetime import datetime, timedelta

def create_sample_data():
    """Criar dados de amostra para testes"""
    db = SessionLocal()
    
    try:
        # Criar tabelas básicas primeiro
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS equipments (
                id INTEGER PRIMARY KEY,
                prefix VARCHAR(20) UNIQUE NOT NULL,
                name VARCHAR(100) NOT NULL,
                model VARCHAR(100),
                manufacturer VARCHAR(100),
                year INTEGER,
                serial_number VARCHAR(100),
                cost_center VARCHAR(50),
                status VARCHAR(20) DEFAULT 'Operacional',
                last_horimeter_update DATETIME DEFAULT CURRENT_TIMESTAMP,
                location VARCHAR(100),
                description TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS maintenance_plans (
                id INTEGER PRIMARY KEY,
                name VARCHAR(200) NOT NULL,
                equipment_id INTEGER NOT NULL,
                type VARCHAR(20) NOT NULL,
                interval_type VARCHAR(20) NOT NULL,
                interval_value INTEGER NOT NULL,
                description TEXT,
                checklist_template JSON,
                is_active BOOLEAN DEFAULT 1,
                last_execution_date DATETIME,
                next_execution_date DATETIME,
                estimated_hours FLOAT,
                priority VARCHAR(20) DEFAULT 'Normal',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (equipment_id) REFERENCES equipments (id)
            )
        """))
        
        # Verificar se já existem equipamentos
        result = db.execute(text("SELECT COUNT(*) FROM equipments")).fetchone()
        if result[0] == 0:
            # Criar equipamentos de amostra
            equipments_data = [
                ("EQ001", "Escavadeira Hidráulica", "PC200", "Komatsu", 2020, "SN123456", "OBRA01", "Operacional", "Canteiro A"),
                ("EQ002", "Caminhão Basculante", "FH540", "Volvo", 2019, "SN789012", "OBRA01", "Operacional", "Canteiro B"),
                ("EQ003", "Motoniveladora", "140M", "Caterpillar", 2021, "SN345678", "OBRA02", "Manutenção", "Oficina")
            ]
            
            for eq_data in equipments_data:
                db.execute(text("""
                    INSERT INTO equipments (prefix, name, model, manufacturer, year, serial_number, cost_center, status, location)
                    VALUES (:prefix, :name, :model, :manufacturer, :year, :serial_number, :cost_center, :status, :location)
                """), {
                    "prefix": eq_data[0], "name": eq_data[1], "model": eq_data[2], "manufacturer": eq_data[3],
                    "year": eq_data[4], "serial_number": eq_data[5], "cost_center": eq_data[6], 
                    "status": eq_data[7], "location": eq_data[8]
                })
        
        # Verificar se já existem planos de manutenção
        result = db.execute(text("SELECT COUNT(*) FROM maintenance_plans")).fetchone()
        if result[0] == 0:
            # Buscar IDs dos equipamentos
            equipment_ids = db.execute(text("SELECT id FROM equipments LIMIT 3")).fetchall()
            
            if equipment_ids:
                # Criar planos de manutenção de amostra
                next_date = datetime.now() + timedelta(days=7)
                plans_data = [
                    ("Manutenção Preventiva - Troca de Óleo", equipment_ids[0][0], "Preventiva", "Tempo", 30, 
                     "Troca de óleo e filtros do equipamento", 1, next_date.isoformat(), 2.0, "Normal"),
                    ("Inspeção Geral", equipment_ids[1][0] if len(equipment_ids) > 1 else equipment_ids[0][0], 
                     "Preventiva", "Tempo", 15, "Inspeção geral dos componentes", 1, next_date.isoformat(), 1.5, "Normal"),
                    ("Manutenção do Sistema Hidráulico", equipment_ids[2][0] if len(equipment_ids) > 2 else equipment_ids[0][0], 
                     "Preventiva", "Tempo", 60, "Verificação e manutenção do sistema hidráulico", 1, next_date.isoformat(), 4.0, "Alta")
                ]
                
                for plan_data in plans_data:
                    db.execute(text("""
                        INSERT INTO maintenance_plans (name, equipment_id, type, interval_type, interval_value, 
                                                     description, is_active, next_execution_date, estimated_hours, priority)
                        VALUES (:name, :equipment_id, :type, :interval_type, :interval_value, 
                                :description, :is_active, :next_execution_date, :estimated_hours, :priority)
                    """), {
                        "name": plan_data[0], "equipment_id": plan_data[1], "type": plan_data[2],
                        "interval_type": plan_data[3], "interval_value": plan_data[4], "description": plan_data[5],
                        "is_active": plan_data[6], "next_execution_date": plan_data[7], 
                        "estimated_hours": plan_data[8], "priority": plan_data[9]
                    })
        
        db.commit()
        print("✅ Dados de amostra criados com sucesso!")
        
        # Mostrar estatísticas
        eq_count = db.execute(text("SELECT COUNT(*) FROM equipments")).fetchone()[0]
        plan_count = db.execute(text("SELECT COUNT(*) FROM maintenance_plans")).fetchone()[0]
        print(f"📊 Equipamentos: {eq_count}")
        print(f"📊 Planos de manutenção: {plan_count}")
        
    except Exception as e:
        print(f"❌ Erro ao criar dados de amostra: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_sample_data()