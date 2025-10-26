#!/usr/bin/env python3
"""
Script para criar materiais de teste com diferentes cenários de estoque
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from sqlalchemy import text

def create_test_materials():
    """Criar materiais de teste com diferentes cenários de estoque"""
    db = SessionLocal()
    
    try:
        # Limpar materiais existentes (apenas para teste)
        db.execute(text("DELETE FROM materials"))
        
        # Materiais de teste com diferentes cenários
        materials_data = [
            {
                "code": "FCD-0191",
                "name": "FILTRO DE COMBUSTÍVEL",
                "description": "Filtro de Combustível com Dreno Separador de Água - Caterpillar 1R-0762",
                "unit": "Peça",
                "average_cost": 130.00,
                "current_stock": 0,  # SEM ESTOQUE
                "minimum_stock": 5,
                "maximum_stock": 20,
                "location": "C/16",
                "is_active": True,
                "category": "Filtros"
            },
            {
                "code": "OLE-0001",
                "name": "ÓLEO MOTOR 15W40",
                "description": "Óleo lubrificante para motores diesel - Shell Rimula R4 X",
                "unit": "Litro",
                "average_cost": 25.50,
                "current_stock": 3,  # ESTOQUE BAIXO (abaixo do mínimo)
                "minimum_stock": 10,
                "maximum_stock": 50,
                "location": "A/12",
                "is_active": True,
                "category": "Lubrificantes"
            },
            {
                "code": "FLT-0002",
                "name": "FILTRO DE AR",
                "description": "Filtro de ar primário para equipamentos pesados",
                "unit": "Peça",
                "average_cost": 85.00,
                "current_stock": 15,  # ESTOQUE NORMAL
                "minimum_stock": 8,
                "maximum_stock": 30,
                "location": "B/05",
                "is_active": True,
                "category": "Filtros"
            },
            {
                "code": "VED-0003",
                "name": "VEDAÇÃO HIDRÁULICA",
                "description": "Kit de vedações para cilindro hidráulico",
                "unit": "Kit",
                "average_cost": 45.00,
                "current_stock": 2,  # ESTOQUE BAIXO
                "minimum_stock": 5,
                "maximum_stock": 15,
                "location": "D/08",
                "is_active": True,
                "category": "Vedações"
            },
            {
                "code": "GRA-0004",
                "name": "GRAXA MULTIUSO",
                "description": "Graxa multiuso para rolamentos e articulações",
                "unit": "Kg",
                "average_cost": 18.00,
                "current_stock": 0,  # SEM ESTOQUE
                "minimum_stock": 3,
                "maximum_stock": 12,
                "location": "A/15",
                "is_active": True,
                "category": "Lubrificantes"
            },
            {
                "code": "PAR-0005",
                "name": "PARAFUSO M12x50",
                "description": "Parafuso sextavado M12x50 classe 8.8",
                "unit": "Peça",
                "average_cost": 2.50,
                "current_stock": 25,  # ESTOQUE NORMAL
                "minimum_stock": 20,
                "maximum_stock": 100,
                "location": "E/02",
                "is_active": True,
                "category": "Fixadores"
            }
        ]
        
        # Inserir materiais
        for material in materials_data:
            db.execute(text("""
                INSERT INTO materials (
                    code, name, description, unit, average_cost, current_stock,
                    minimum_stock, maximum_stock, location, is_active, category
                ) VALUES (
                    :code, :name, :description, :unit, :average_cost, :current_stock,
                    :minimum_stock, :maximum_stock, :location, :is_active, :category
                )
            """), material)
        
        db.commit()
        print("✅ Materiais de teste criados com sucesso!")
        
        # Mostrar estatísticas
        total_materials = db.execute(text("SELECT COUNT(*) FROM materials WHERE is_active = 1")).fetchone()[0]
        low_stock = db.execute(text("SELECT COUNT(*) FROM materials WHERE current_stock < minimum_stock AND current_stock > 0")).fetchone()[0]
        zero_stock = db.execute(text("SELECT COUNT(*) FROM materials WHERE current_stock = 0")).fetchone()[0]
        total_value = db.execute(text("SELECT COALESCE(SUM(current_stock * average_cost), 0) FROM materials WHERE current_stock > 0")).fetchone()[0]
        
        print(f"📊 Total de Materiais: {total_materials}")
        print(f"🟠 Estoque Baixo: {low_stock}")
        print(f"🔴 Sem Estoque: {zero_stock}")
        print(f"💰 Valor Total: R$ {total_value:.2f}")
        
        # Listar materiais criados
        print("\n📋 Materiais criados:")
        materials = db.execute(text("""
            SELECT code, name, current_stock, minimum_stock, 
                   CASE 
                       WHEN current_stock = 0 THEN 'SEM ESTOQUE'
                       WHEN current_stock < minimum_stock THEN 'ESTOQUE BAIXO'
                       ELSE 'NORMAL'
                   END as status
            FROM materials 
            ORDER BY code
        """)).fetchall()
        
        for material in materials:
            print(f"  {material[0]} - {material[1]} | Estoque: {material[2]} | Status: {material[4]}")
        
    except Exception as e:
        print(f"❌ Erro ao criar materiais de teste: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_test_materials()