#!/usr/bin/env python3
"""
Script para limpar completamente a base de dados MTDL PCM
Remove todos os dados das tabelas mantendo a estrutura
"""

import sqlite3
import os
from pathlib import Path

def clean_database():
    """Limpa todas as tabelas da base de dados"""
    
    db_path = "mtdl_pcm.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Base de dados {db_path} não encontrada!")
        return False
    
    try:
        # Conectar à base de dados
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🧹 LIMPEZA DA BASE DE DADOS - MTDL PCM")
        print("=" * 50)
        
        # Desabilitar verificações de chave estrangeira temporariamente
        cursor.execute("PRAGMA foreign_keys = OFF")
        
        # Obter lista de todas as tabelas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = cursor.fetchall()
        
        if not tables:
            print("ℹ️  Nenhuma tabela encontrada na base de dados")
            return True
        
        print(f"📋 Encontradas {len(tables)} tabelas:")
        for table in tables:
            print(f"   - {table[0]}")
        
        print("\n🗑️  Limpando tabelas...")
        
        # Limpar cada tabela
        cleaned_tables = 0
        for table in tables:
            table_name = table[0]
            try:
                # Contar registros antes da limpeza
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count_before = cursor.fetchone()[0]
                
                # Limpar a tabela
                cursor.execute(f"DELETE FROM {table_name}")
                
                # Resetar o auto-increment se existir
                cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table_name}'")
                
                print(f"   ✅ {table_name}: {count_before} registros removidos")
                cleaned_tables += 1
                
            except Exception as e:
                print(f"   ❌ Erro ao limpar {table_name}: {e}")
        
        # Reabilitar verificações de chave estrangeira
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # Confirmar alterações
        conn.commit()
        
        # Executar VACUUM para otimizar a base de dados
        print("\n🔧 Otimizando base de dados...")
        cursor.execute("VACUUM")
        
        print(f"\n✅ LIMPEZA CONCLUÍDA!")
        print(f"📊 {cleaned_tables} tabelas limpas com sucesso")
        print(f"💾 Base de dados otimizada")
        
        # Verificar se as tabelas estão realmente vazias
        print("\n🔍 Verificação final:")
        total_records = 0
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            total_records += count
            if count > 0:
                print(f"   ⚠️  {table_name}: {count} registros restantes")
            else:
                print(f"   ✅ {table_name}: vazia")
        
        if total_records == 0:
            print(f"\n🎉 BASE DE DADOS COMPLETAMENTE LIMPA!")
        else:
            print(f"\n⚠️  Ainda existem {total_records} registros na base de dados")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao limpar a base de dados: {e}")
        return False
    
    finally:
        if 'conn' in locals():
            conn.close()

def create_backup():
    """Cria backup da base de dados antes da limpeza"""
    
    db_path = "mtdl_pcm.db"
    
    if not os.path.exists(db_path):
        return None
    
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"mtdl_pcm_backup_before_clean_{timestamp}.db"
    
    try:
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"💾 Backup criado: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"⚠️  Erro ao criar backup: {e}")
        return None

if __name__ == "__main__":
    print("🚨 ATENÇÃO: Esta operação irá remover TODOS os dados da base de dados!")
    print("Deseja continuar? (s/N): ", end="")
    
    # Para execução automática em scripts, aceitar automaticamente
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--auto":
        response = "s"
        print("s (modo automático)")
    else:
        response = input().lower().strip()
    
    if response in ['s', 'sim', 'y', 'yes']:
        # Criar backup antes da limpeza
        backup_path = create_backup()
        
        # Executar limpeza
        success = clean_database()
        
        if success:
            print("\n🎯 A base de dados está pronta para novos testes!")
            if backup_path:
                print(f"📁 Backup disponível em: {backup_path}")
        else:
            print("\n❌ Falha na limpeza da base de dados!")
    else:
        print("❌ Operação cancelada pelo usuário")