#!/usr/bin/env python3
"""
Script para testar se o modal de edição está preenchendo os campos corretamente
"""

import requests
import json

def test_edit_modal_functionality():
    """Testa se a funcionalidade de edição está funcionando corretamente"""
    
    base_url = "http://localhost:8000"
    
    print("🧪 Testando funcionalidade do modal de edição...")
    print("=" * 50)
    
    try:
        # 1. Buscar materiais existentes
        print("1. Buscando materiais existentes...")
        response = requests.get(f"{base_url}/api/warehouse/materials")
        response.raise_for_status()
        materials = response.json()
        
        if not materials:
            print("❌ Nenhum material encontrado para teste")
            return False
            
        # Pegar o primeiro material para teste
        test_material = materials[0]
        material_id = test_material['id']
        
        print(f"✅ Material encontrado para teste:")
        print(f"   ID: {material_id}")
        print(f"   Código: {test_material.get('code', 'N/A')}")
        print(f"   Nome: {test_material.get('name', 'N/A')}")
        print(f"   Categoria: {test_material.get('category', 'N/A')}")
        print(f"   Unidade: {test_material.get('unit', 'N/A')}")
        print(f"   Preço Unitário: R$ {test_material.get('unit_price', 0):.2f}")
        print()
        
        # 2. Testar endpoint específico de busca por ID (usado pelo modal de edição)
        print("2. Testando endpoint de busca por ID...")
        response = requests.get(f"{base_url}/api/warehouse/api/materials/{material_id}")
        response.raise_for_status()
        material_detail = response.json()
        
        print("✅ Dados retornados pelo endpoint de edição:")
        print(f"   ID: {material_detail.get('id')}")
        print(f"   Código: {material_detail.get('code')}")
        print(f"   Nome: {material_detail.get('name')}")
        print(f"   Referência: {material_detail.get('reference', 'N/A')}")
        print(f"   Categoria: {material_detail.get('category')}")
        print(f"   Unidade: {material_detail.get('unit')}")
        print(f"   Descrição: {material_detail.get('description', 'N/A')}")
        print(f"   Preço Unitário: R$ {material_detail.get('unit_price', 0):.2f}")
        print(f"   Estoque Mínimo: {material_detail.get('minimum_stock', 0)}")
        print(f"   Estoque Máximo: {material_detail.get('maximum_stock', 0)}")
        print(f"   Status Ativo: {material_detail.get('is_active', False)}")
        print()
        
        # 3. Verificar se todos os campos necessários estão presentes
        print("3. Verificando campos obrigatórios...")
        required_fields = ['id', 'code', 'name', 'category', 'unit', 'minimum_stock', 'maximum_stock']
        missing_fields = []
        
        for field in required_fields:
            if field not in material_detail or material_detail[field] is None:
                missing_fields.append(field)
        
        if missing_fields:
            print(f"❌ Campos obrigatórios ausentes: {missing_fields}")
            return False
        else:
            print("✅ Todos os campos obrigatórios estão presentes")
        
        print()
        print("🎉 Teste concluído com sucesso!")
        print("📝 Instruções para teste manual:")
        print("   1. Acesse http://localhost:8000")
        print("   2. Vá para a seção 'Estoque' > 'Materiais'")
        print(f"   3. Clique no botão de editar do material '{test_material.get('name')}'")
        print("   4. Verifique se todos os campos são preenchidos automaticamente")
        print("   5. Os campos devem mostrar os valores listados acima")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro de conexão: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return False

if __name__ == "__main__":
    success = test_edit_modal_functionality()
    exit(0 if success else 1)