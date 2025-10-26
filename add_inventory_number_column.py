#!/usr/bin/env python3
"""
Script para adicionar o campo inventory_number à tabela inventory_history
"""

import sqlite3
import os
from datetime import datetime

def add_inventory_number_column():
    """Adiciona o campo inventory_number à tabela inventory_history"""
    
    # Caminho do banco de dados
    db_path = "mtdl_pcm.db"
    
    if not os.path.exists(db_path):
        print(f"Erro: Banco de dados {db_path} não encontrado!")
        return False
    
    try:
        # Conectar ao banco
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar se a coluna já existe
        cursor.execute("PRAGMA table_info(inventory_history)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'inventory_number' in columns:
            print("Campo 'inventory_number' já existe na tabela inventory_history")
            return True
        
        # Adicionar a coluna inventory_number
        print("Adicionando campo 'inventory_number' à tabela inventory_history...")
        cursor.execute("""
            ALTER TABLE inventory_history 
            ADD COLUMN inventory_number VARCHAR(20)
        """)
        
        # Criar índice único para o campo inventory_number
        print("Criando índice único para inventory_number...")
        cursor.execute("""
            CREATE UNIQUE INDEX idx_inventory_number 
            ON inventory_history(inventory_number)
        """)
        
        # Atualizar registros existentes com números de inventário retroativos
        print("Atualizando registros existentes com números de inventário...")
        cursor.execute("""
            SELECT id, process_date 
            FROM inventory_history 
            WHERE inventory_number IS NULL 
            ORDER BY process_date
        """)
        
        existing_records = cursor.fetchall()
        
        for i, (record_id, process_date) in enumerate(existing_records, 1):
            # Converter a data para o formato do número de inventário
            if process_date:
                try:
                    # Tentar diferentes formatos de data
                    try:
                        date_obj = datetime.fromisoformat(process_date.replace('Z', '+00:00'))
                    except:
                        date_obj = datetime.strptime(process_date, '%Y-%m-%d %H:%M:%S')
                    
                    date_prefix = date_obj.strftime("INV-%Y%m%d")
                    inventory_number = f"{date_prefix}-{i:03d}"
                except:
                    # Se não conseguir parsear a data, usar data atual
                    date_prefix = datetime.now().strftime("INV-%Y%m%d")
                    inventory_number = f"{date_prefix}-{i:03d}"
            else:
                # Se não há data, usar data atual
                date_prefix = datetime.now().strftime("INV-%Y%m%d")
                inventory_number = f"{date_prefix}-{i:03d}"
            
            cursor.execute("""
                UPDATE inventory_history 
                SET inventory_number = ? 
                WHERE id = ?
            """, (inventory_number, record_id))
            
            print(f"  Registro {record_id}: {inventory_number}")
        
        # Confirmar as alterações
        conn.commit()
        print("Migração concluída com sucesso!")
        
        # Verificar o resultado
        cursor.execute("SELECT COUNT(*) FROM inventory_history WHERE inventory_number IS NOT NULL")
        count = cursor.fetchone()[0]
        print(f"Total de registros com inventory_number: {count}")
        
        return True
        
    except Exception as e:
        print(f"Erro durante a migração: {str(e)}")
        conn.rollback()
        return False
        
    finally:
        conn.close()

if __name__ == "__main__":
    print("=== Migração: Adicionando campo inventory_number ===")
    success = add_inventory_number_column()
    
    if success:
        print("\n✅ Migração executada com sucesso!")
    else:
        print("\n❌ Erro na execução da migração!")