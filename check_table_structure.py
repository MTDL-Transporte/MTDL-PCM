#!/usr/bin/env python3
"""
Script para verificar a estrutura da tabela materials
"""

import sqlite3
import os

def check_table_structure():
    """Verifica a estrutura da tabela materials"""
    
    db_path = "mtdl_pcm.db"
    
    if not os.path.exists(db_path):
        print("❌ Banco de dados não encontrado!")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔍 Verificando estrutura da tabela materials...")
        
        # Verificar se a tabela existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='materials'")
        table_exists = cursor.fetchone()
        
        if not table_exists:
            print("❌ Tabela 'materials' não existe!")
            return
        
        print("✅ Tabela 'materials' encontrada")
        
        # Obter estrutura da tabela
        cursor.execute("PRAGMA table_info(materials)")
        columns = cursor.fetchall()
        
        print(f"\n📋 Estrutura da tabela (total: {len(columns)} colunas):")
        print("-" * 60)
        for col in columns:
            cid, name, type_, notnull, default, pk = col
            print(f"  {cid:2d}. {name:20s} | {type_:15s} | NOT NULL: {bool(notnull)} | PK: {bool(pk)}")
        
        # Verificar dados existentes
        cursor.execute("SELECT COUNT(*) FROM materials")
        count = cursor.fetchone()[0]
        print(f"\n📊 Total de registros: {count}")
        
        if count > 0:
            # Mostrar alguns registros
            cursor.execute("SELECT * FROM materials LIMIT 3")
            records = cursor.fetchall()
            
            print(f"\n📦 Primeiros registros:")
            column_names = [col[1] for col in columns]
            
            for i, record in enumerate(records, 1):
                print(f"\n  Registro {i}:")
                for j, value in enumerate(record):
                    if j < len(column_names):
                        print(f"    {column_names[j]:20s}: {value}")
        
        # Verificar tabelas relacionadas
        print(f"\n🔗 Outras tabelas no banco:")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        for table in tables:
            print(f"  - {table[0]}")
            
    except sqlite3.Error as e:
        print(f"❌ Erro no banco de dados: {e}")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    check_table_structure()