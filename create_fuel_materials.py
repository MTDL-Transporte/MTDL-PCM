#!/usr/bin/env python3
"""
Script para criar materiais de combustível para o módulo de abastecimento
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from sqlalchemy import text

def create_fuel_materials():
    """Criar materiais de combustível para testes"""
    db = SessionLocal()
    
    try:
        # Verificar se já existem combustíveis
        result = db.execute(text("SELECT COUNT(*) FROM materials WHERE category = 'Combustível'")).fetchone()
        
        if result[0] == 0:
            # Materiais de combustível
            fuel_materials = [
                {
                    "code": "DSL-S10",
                    "name": "DIESEL S10",
                    "description": "Óleo diesel S10 para equipamentos pesados",
                    "unit": "Litro",
                    "average_cost": 5.85,
                    "current_stock": 1000.0,
                    "minimum_stock": 200.0,
                    "maximum_stock": 2000.0,
                    "location": "TANQUE-01",
                    "is_active": True,
                    "category": "Combustível"
                },
                {
                    "code": "DSL-S500",
                    "name": "DIESEL S500",
                    "description": "Óleo diesel S500 para equipamentos antigos",
                    "unit": "Litro",
                    "average_cost": 5.75,
                    "current_stock": 500.0,
                    "minimum_stock": 100.0,
                    "maximum_stock": 1000.0,
                    "location": "TANQUE-02",
                    "is_active": True,
                    "category": "Combustível"
                },
                {
                    "code": "GAS-COM",
                    "name": "GASOLINA COMUM",
                    "description": "Gasolina comum para equipamentos leves",
                    "unit": "Litro",
                    "average_cost": 6.20,
                    "current_stock": 200.0,
                    "minimum_stock": 50.0,
                    "maximum_stock": 500.0,
                    "location": "TANQUE-03",
                    "is_active": True,
                    "category": "Combustível"
                }
            ]
            
            # Inserir combustíveis
            for fuel in fuel_materials:
                db.execute(text("""
                    INSERT INTO materials (
                        code, name, description, unit, average_cost, current_stock,
                        minimum_stock, maximum_stock, location, is_active, category
                    ) VALUES (
                        :code, :name, :description, :unit, :average_cost, :current_stock,
                        :minimum_stock, :maximum_stock, :location, :is_active, :category
                    )
                """), fuel)
            
            db.commit()
            print("✅ Combustível criado com sucesso!")
        else:
            print("ℹ️ Combustível já existe no sistema")
        
        # Mostrar combustíveis disponíveis
        fuels = db.execute(text("""
            SELECT code, name, current_stock, unit, average_cost
            FROM materials 
            WHERE category = 'Combustível' AND is_active = 1
            ORDER BY code
        """)).fetchall()
        
        print("\n⛽ Combustível disponível:")
        for fuel in fuels:
            print(f"  {fuel[0]} - {fuel[1]} | Estoque: {fuel[2]} {fuel[3]} | Custo: R$ {fuel[4]:.2f}/{fuel[3]}")
        
    except Exception as e:
        print(f"❌ Erro ao criar combustíveis: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_fuel_materials()