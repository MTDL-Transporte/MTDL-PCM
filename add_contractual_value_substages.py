#!/usr/bin/env python3
"""
Script para adicionar a coluna contractual_value à tabela construction_sub_stages
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from app.database import DATABASE_URL

def add_contractual_value_column():
    """Adicionar coluna contractual_value à tabela construction_sub_stages"""
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            # Verificar se a coluna já existe
            result = conn.execute(text("PRAGMA table_info(construction_sub_stages)")).fetchall()
            columns = [row[1] for row in result]
            
            if 'contractual_value' not in columns:
                print("Adicionando coluna contractual_value à tabela construction_sub_stages...")
                conn.execute(text("ALTER TABLE construction_sub_stages ADD COLUMN contractual_value REAL DEFAULT 0.0"))
                conn.commit()
                print("✅ Coluna contractual_value adicionada com sucesso!")
            else:
                print("✅ Coluna contractual_value já existe!")
                
            print("\nColunas atuais da tabela construction_sub_stages:")
            result = conn.execute(text("PRAGMA table_info(construction_sub_stages)")).fetchall()
            for row in result:
                print(f"  - {row[1]}: {row[2]}")
                
    except Exception as e:
        print(f"❌ Erro ao atualizar banco de dados: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🔧 Adicionando coluna contractual_value à tabela construction_sub_stages...")
    if add_contractual_value_column():
        print("✅ Banco de dados atualizado com sucesso!")
    else:
        print("❌ Falha ao atualizar banco de dados!")