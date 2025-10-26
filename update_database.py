#!/usr/bin/env python3
"""
Script para atualizar o banco de dados com novas colunas:
- work_orders.maintenance_cause
- users.company_code
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from app.database import DATABASE_URL

def add_column_if_missing(conn, table, column, ddl_type):
    result = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    columns = [row[1] for row in result]
    if column not in columns:
        print(f"Adicionando coluna {table}.{column}...")
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}"))
        conn.commit()
        print(f"✅ Coluna {table}.{column} adicionada com sucesso!")
    else:
        print(f"✅ Coluna {table}.{column} já existe!")


def update_database():
    """Atualizar banco de dados com novas colunas"""
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            # work_orders.maintenance_cause
            add_column_if_missing(conn, 'work_orders', 'maintenance_cause', 'VARCHAR(50)')
            print("\nColunas atuais da tabela work_orders:")
            result = conn.execute(text("PRAGMA table_info(work_orders)")).fetchall()
            for row in result:
                print(f"  - {row[1]}: {row[2]}")

            # users.company_code (3 dígitos, opcional)
            add_column_if_missing(conn, 'users', 'company_code', 'VARCHAR(3)')
            print("\nColunas atuais da tabela users:")
            result = conn.execute(text("PRAGMA table_info(users)")).fetchall()
            for row in result:
                print(f"  - {row[1]}: {row[2]}")
                
    except Exception as e:
        print(f"❌ Erro ao atualizar banco de dados: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🔧 Atualizando banco de dados MTDL-PCM...")
    if update_database():
        print("✅ Banco de dados atualizado com sucesso!")
    else:
        print("❌ Falha ao atualizar banco de dados!")