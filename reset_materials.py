#!/usr/bin/env python3
"""
Script para resetar materiais - excluir existentes e criar novo para teste
"""

import sqlite3
import os
from datetime import datetime

def reset_materials():
    """Exclui todos os materiais e cria um novo para teste"""
    
    # Caminho do banco de dados
    db_path = "mtdl_pcm.db"
    
    if not os.path.exists(db_path):
        print("❌ Banco de dados não encontrado!")
        return False
    
    try:
        # Conectar ao banco
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🗑️ Excluindo materiais existentes...")
        
        # Excluir todos os materiais
        cursor.execute("DELETE FROM materials")
        deleted_count = cursor.rowcount
        print(f"✅ {deleted_count} materiais excluídos")
        
        print("📦 Criando novo material para teste...")
        
        # Criar novo material com estrutura correta
        material_data = {
            'code': 'TEST001',
            'name': 'Material de Teste',
            'reference': 'REF-TEST-001',
            'category': 'Teste',
            'unit': 'UN',
            'description': 'Material criado para testar a função de edição',
            'unit_price': 25.50,
            'minimum_stock': 5.0,
            'maximum_stock': 50.0,
            'current_stock': 20.0,
            'average_cost': 22.00,
            'location': 'Estoque A',
            'barcode': 'TEST001BAR',
            'is_active': 1,
            'average_consumption': 2.5
        }
        
        cursor.execute("""
            INSERT INTO materials (
                code, name, reference, category, unit, description,
                unit_price, minimum_stock, maximum_stock, current_stock,
                average_cost, location, barcode, is_active, average_consumption,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            material_data['code'],
            material_data['name'],
            material_data['reference'],
            material_data['category'],
            material_data['unit'],
            material_data['description'],
            material_data['unit_price'],
            material_data['minimum_stock'],
            material_data['maximum_stock'],
            material_data['current_stock'],
            material_data['average_cost'],
            material_data['location'],
            material_data['barcode'],
            material_data['is_active'],
            material_data['average_consumption'],
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        
        # Confirmar as alterações
        conn.commit()
        
        # Verificar se foi criado
        cursor.execute("SELECT id, code, name FROM materials WHERE code = ?", (material_data['code'],))
        new_material = cursor.fetchone()
        
        if new_material:
            print(f"✅ Novo material criado:")
            print(f"   ID: {new_material[0]}")
            print(f"   Código: {new_material[1]}")
            print(f"   Nome: {new_material[2]}")
            
            # Mostrar todos os campos para verificação
            cursor.execute("SELECT * FROM materials WHERE id = ?", (new_material[0],))
            material_full = cursor.fetchone()
            
            print(f"\n📋 Dados completos do material:")
            cursor.execute("PRAGMA table_info(materials)")
            columns = [col[1] for col in cursor.fetchall()]
            
            for i, column in enumerate(columns):
                print(f"   {column}: {material_full[i]}")
            
            return True
        else:
            print("❌ Erro ao criar novo material")
            return False
            
    except sqlite3.Error as e:
        print(f"❌ Erro no banco de dados: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return False
    finally:
        if conn:
            conn.close()

def verify_materials():
    """Verifica quantos materiais existem no banco"""
    db_path = "mtdl_pcm.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM materials")
        count = cursor.fetchone()[0]
        
        print(f"📊 Total de materiais no banco: {count}")
        
        if count > 0:
            cursor.execute("SELECT id, code, name, is_active FROM materials LIMIT 5")
            materials = cursor.fetchall()
            
            print("📦 Materiais encontrados:")
            for material in materials:
                status = "Ativo" if material[3] else "Inativo"
                print(f"   ID: {material[0]} | Código: {material[1]} | Nome: {material[2]} | Status: {status}")
        
        return count
        
    except sqlite3.Error as e:
        print(f"❌ Erro ao verificar materiais: {e}")
        return 0
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("🔄 Iniciando reset de materiais...")
    print("=" * 50)
    
    # Verificar estado atual
    print("📊 Estado atual:")
    verify_materials()
    
    print("\n" + "=" * 50)
    
    # Resetar materiais
    if reset_materials():
        print("\n" + "=" * 50)
        print("📊 Estado após reset:")
        verify_materials()
        print("\n✅ Reset concluído com sucesso!")
        print("🧪 Agora você pode testar a função de edição com o novo material.")
    else:
        print("\n❌ Falha no reset dos materiais.")