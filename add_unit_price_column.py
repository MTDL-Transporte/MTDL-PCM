#!/usr/bin/env python3
"""
Script para adicionar a coluna unit_price à tabela materials
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from app.database import DATABASE_URL

def add_unit_price_column():
    """Adicionar coluna unit_price à tabela materials"""
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            # Verificar se a coluna já existe
            result = conn.execute(text("PRAGMA table_info(materials)")).fetchall()
            columns = [row[1] for row in result]
            
            if 'unit_price' not in columns:
                print("Adicionando coluna unit_price à tabela materials...")
                conn.execute(text("ALTER TABLE materials ADD COLUMN unit_price REAL DEFAULT 0.0"))
                conn.commit()
                print("✅ Coluna unit_price adicionada com sucesso!")
                
                # Atualizar materiais existentes com o valor do average_cost
                print("Atualizando materiais existentes...")
                conn.execute(text("UPDATE materials SET unit_price = average_cost WHERE average_cost > 0"))
                conn.commit()
                print("✅ Materiais existentes atualizados!")
            else:
                print("✅ Coluna unit_price já existe!")
                
            print("\nColunas atuais da tabela materials:")
            result = conn.execute(text("PRAGMA table_info(materials)")).fetchall()
            for row in result:
                print(f"  - {row[1]}: {row[2]}")
                
    except Exception as e:
        print(f"❌ Erro ao atualizar banco de dados: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🔧 Adicionando coluna unit_price à tabela materials...")
    if add_unit_price_column():
        print("✅ Banco de dados atualizado com sucesso!")
    else:
        print("❌ Falha ao atualizar banco de dados!")