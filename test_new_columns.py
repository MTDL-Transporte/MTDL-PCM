#!/usr/bin/env python3
"""
Script para testar as novas colunas da tabela de estoque
Adiciona alguns materiais de exemplo
"""

import sqlite3
from pathlib import Path

def add_test_materials():
    """Adiciona materiais de teste para verificar as novas colunas"""
    
    db_path = Path(__file__).parent / "mtdl_pcm.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔧 Adicionando materiais de teste...")
        
        # Materiais de teste com todos os campos necessários
        test_materials = [
            {
                'code': 'MAT001',
                'name': 'Filtro de Óleo Hidráulico',
                'category': 'Filtros',
                'unit': 'UN',
                'average_cost': 45.50,
                'minimum_stock': 5,
                'maximum_stock': 20,
                'current_stock': 12,
                'location': 'A1-B2',
                'description': 'Filtro para sistema hidráulico',
                'status': 'Ativo'
            },
            {
                'code': 'MAT002', 
                'name': 'Óleo Hidráulico ISO 68',
                'category': 'Lubrificantes',
                'unit': 'L',
                'average_cost': 25.80,
                'minimum_stock': 10,
                'maximum_stock': 50,
                'current_stock': 3,  # Baixo estoque
                'location': 'B2-C1',
                'description': 'Óleo hidráulico para equipamentos',
                'status': 'Ativo'
            },
            {
                'code': 'MAT003',
                'name': 'Rolamento 6205-2RS',
                'category': 'Rolamentos',
                'unit': 'UN',
                'average_cost': 35.90,
                'minimum_stock': 8,
                'maximum_stock': 30,
                'current_stock': 15,
                'location': 'C1-D3',
                'description': 'Rolamento blindado',
                'status': 'Ativo'
            },
            {
                'code': 'MAT004',
                'name': 'Correia V - A50',
                'category': 'Correias',
                'unit': 'UN',
                'average_cost': 18.75,
                'minimum_stock': 3,
                'maximum_stock': 15,
                'current_stock': 8,
                'location': 'D3-E1',
                'description': 'Correia em V para transmissão',
                'status': 'Ativo'
            },
            {
                'code': 'MAT005',
                'name': 'Parafuso M8x25',
                'category': 'Parafusos',
                'unit': 'UN',
                'average_cost': 2.50,
                'minimum_stock': 50,
                'maximum_stock': 200,
                'current_stock': 125,
                'location': 'E1-F2',
                'description': 'Parafuso sextavado M8x25mm',
                'status': 'Ativo'
            }
        ]
        
        for material in test_materials:
            cursor.execute("""
                INSERT INTO materials (
                    code, name, category, unit, average_cost, minimum_stock, 
                    maximum_stock, current_stock, location, description, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                material['code'], material['name'], material['category'],
                material['unit'], material['average_cost'], material['minimum_stock'],
                material['maximum_stock'], material['current_stock'], 
                material['location'], material['description'], True
            ))
            
            print(f"   ✅ {material['code']} - {material['name']}")
        
        conn.commit()
        print(f"\n🎉 {len(test_materials)} materiais de teste adicionados com sucesso!")
        
        # Verificar dados inseridos
        cursor.execute("SELECT COUNT(*) FROM materials")
        total = cursor.fetchone()[0]
        print(f"📊 Total de materiais no banco: {total}")
        
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Erro ao adicionar materiais: {e}")
        return False
    
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("🧪 TESTE DAS NOVAS COLUNAS - MTDL PCM")
    print("=" * 50)
    
    success = add_test_materials()
    
    if success:
        print("\n🎯 MATERIAIS DE TESTE CRIADOS!")
        print("Acesse http://localhost:8000 e vá para Estoque para ver as novas colunas")
        print("=" * 50)
    else:
        print("\n❌ FALHA AO CRIAR MATERIAIS DE TESTE!")
        print("=" * 50)