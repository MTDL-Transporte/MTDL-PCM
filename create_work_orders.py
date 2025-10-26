#!/usr/bin/env python3
"""
Script para criar ordens de serviço de exemplo para testes do sistema
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from sqlalchemy import text
from datetime import datetime, timedelta

def create_work_orders():
    """Criar ordens de serviço de exemplo"""
    db = SessionLocal()
    
    try:
        # Criar tabela de work_orders se não existir
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS work_orders (
                id INTEGER PRIMARY KEY,
                number VARCHAR(20) UNIQUE NOT NULL,
                title VARCHAR(200) NOT NULL,
                description TEXT,
                equipment_id INTEGER NOT NULL,
                priority VARCHAR(20) DEFAULT 'Média',
                type VARCHAR(20) DEFAULT 'Corretiva',
                status VARCHAR(20) DEFAULT 'Aberta',
                requested_by VARCHAR(100),
                assigned_to VARCHAR(100),
                estimated_hours FLOAT,
                actual_hours FLOAT,
                cost DECIMAL(10,2),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                started_at DATETIME,
                completed_at DATETIME,
                due_date DATETIME,
                notes TEXT,
                FOREIGN KEY (equipment_id) REFERENCES equipments (id)
            )
        """))
        
        # Verificar se já existem ordens de serviço
        result = db.execute(text("SELECT COUNT(*) FROM work_orders")).fetchone()
        if result[0] > 0:
            print("⚠️  Já existem ordens de serviço no banco de dados.")
            return
        
        # Buscar equipamentos existentes
        equipments = db.execute(text("SELECT id, name FROM equipments")).fetchall()
        if not equipments:
            print("❌ Nenhum equipamento encontrado. Execute primeiro o script create_sample_data.py")
            return
        
        # Criar ordens de serviço de exemplo
        work_orders_data = [
            {
                "number": "100001",
                "title": "Troca de óleo do motor",
                "description": "Realizar troca de óleo do motor e filtros conforme cronograma de manutenção preventiva",
                "equipment_id": equipments[0][0],
                "priority": "Média",
                "type": "Preventiva",
                "status": "Aberta",
                "requested_by": "Sistema Automático",
                "estimated_hours": 2.0,
                "due_date": (datetime.now() + timedelta(days=3)).isoformat()
            },
            {
                "number": "100002", 
                "title": "Reparo no sistema hidráulico",
                "description": "Vazamento identificado no cilindro hidráulico principal. Necessário substituir vedações e verificar pressão do sistema",
                "equipment_id": equipments[0][0] if len(equipments) >= 1 else equipments[0][0],
                "priority": "Alta",
                "type": "Corretiva",
                "status": "Em andamento",
                "requested_by": "João Silva",
                "assigned_to": "Carlos Santos",
                "estimated_hours": 4.0,
                "actual_hours": 2.5,
                "started_at": (datetime.now() - timedelta(hours=2)).isoformat(),
                "due_date": (datetime.now() + timedelta(days=1)).isoformat()
            },
            {
                "number": "100003",
                "title": "Inspeção geral de segurança",
                "description": "Inspeção completa dos sistemas de segurança, freios, luzes e equipamentos de proteção",
                "equipment_id": equipments[1][0] if len(equipments) >= 2 else equipments[0][0],
                "priority": "Média",
                "type": "Preventiva", 
                "status": "Aberta",
                "requested_by": "Maria Oliveira",
                "estimated_hours": 3.0,
                "due_date": (datetime.now() + timedelta(days=7)).isoformat()
            },
            {
                "number": "100004",
                "title": "Substituição de pneus",
                "description": "Pneus traseiros apresentam desgaste excessivo. Necessário substituição imediata por questões de segurança",
                "equipment_id": equipments[1][0] if len(equipments) >= 2 else equipments[0][0],
                "priority": "Alta",
                "type": "Corretiva",
                "status": "Aberta",
                "requested_by": "Pedro Costa",
                "estimated_hours": 1.5,
                "due_date": (datetime.now() + timedelta(days=2)).isoformat()
            },
            {
                "number": "100005",
                "title": "Manutenção do ar condicionado",
                "description": "Sistema de ar condicionado não está resfriando adequadamente. Verificar gás refrigerante e filtros",
                "equipment_id": equipments[2][0] if len(equipments) >= 3 else equipments[0][0],
                "priority": "Baixa",
                "type": "Corretiva",
                "status": "Fechada",
                "requested_by": "Ana Santos",
                "assigned_to": "Roberto Lima",
                "estimated_hours": 2.0,
                "actual_hours": 1.5,
                "cost": 350.00,
                "started_at": (datetime.now() - timedelta(days=2)).isoformat(),
                "completed_at": (datetime.now() - timedelta(days=1)).isoformat(),
                "notes": "Substituído filtro e completado gás refrigerante. Sistema funcionando normalmente."
            }
        ]
        
        # Inserir ordens de serviço
        for wo_data in work_orders_data:
            db.execute(text("""
                INSERT INTO work_orders (
                    number, title, description, equipment_id, priority, type, status,
                    requested_by, assigned_to, estimated_hours, actual_hours, cost,
                    started_at, completed_at, due_date, notes
                ) VALUES (
                    :number, :title, :description, :equipment_id, :priority, :type, :status,
                    :requested_by, :assigned_to, :estimated_hours, :actual_hours, :cost,
                    :started_at, :completed_at, :due_date, :notes
                )
            """), wo_data)
        
        db.commit()
        print("✅ Ordens de serviço de exemplo criadas com sucesso!")
        
        # Mostrar estatísticas
        wo_count = db.execute(text("SELECT COUNT(*) FROM work_orders")).fetchone()[0]
        status_counts = db.execute(text("""
            SELECT status, COUNT(*) 
            FROM work_orders 
            GROUP BY status
        """)).fetchall()
        
        print(f"📊 Total de ordens de serviço: {wo_count}")
        print("📊 Por status:")
        for status, count in status_counts:
            print(f"   - {status}: {count}")
        
    except Exception as e:
        print(f"❌ Erro ao criar ordens de serviço: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_work_orders()