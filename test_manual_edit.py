#!/usr/bin/env python3
"""
Script para testar manualmente a função editMaterial
"""

import requests
import json
import time

def test_manual_edit():
    """Simula o processo manual de edição"""
    
    print("🧪 Teste Manual da Função editMaterial")
    print("=" * 50)
    
    try:
        # 1. Buscar materiais disponíveis
        print("1️⃣ Buscando materiais disponíveis...")
        response = requests.get("http://localhost:8000/api/warehouse/materials")
        response.raise_for_status()
        materials = response.json()
        
        if not materials:
            print("❌ Nenhum material encontrado")
            return False
        
        material = materials[0]
        material_id = material['id']
        
        print(f"   ✅ Material encontrado: {material['name']} (ID: {material_id})")
        
        # 2. Simular a chamada da função editMaterial
        print(f"\n2️⃣ Simulando editMaterial({material_id})...")
        
        # Esta é exatamente a mesma requisição que a função JavaScript faz
        api_url = f"http://localhost:8000/api/warehouse/api/materials/{material_id}"
        print(f"   📡 URL da API: {api_url}")
        
        response = requests.get(api_url)
        
        if response.status_code == 200:
            material_data = response.json()
            print("   ✅ Dados recebidos com sucesso!")
            
            # 3. Verificar todos os campos que seriam preenchidos
            print(f"\n3️⃣ Dados que seriam preenchidos no modal:")
            print(f"   🆔 ID: {material_data.get('id', 'N/A')}")
            print(f"   🔢 Código: {material_data.get('code', 'N/A')}")
            print(f"   📝 Nome: {material_data.get('name', 'N/A')}")
            print(f"   🔗 Referência: {material_data.get('reference', 'N/A')}")
            print(f"   📂 Categoria: {material_data.get('category', 'N/A')}")
            print(f"   📏 Unidade: {material_data.get('unit', 'N/A')}")
            print(f"   📄 Descrição: {material_data.get('description', 'N/A')}")
            print(f"   💰 Preço Unitário: R$ {material_data.get('unit_price', 'N/A')}")
            print(f"   📦 Estoque Mínimo: {material_data.get('minimum_stock', 'N/A')}")
            print(f"   📦 Estoque Máximo: {material_data.get('maximum_stock', 'N/A')}")
            print(f"   ✅ Status: {'Ativo' if material_data.get('is_active', False) else 'Inativo'}")
            
            # 4. Verificar se todos os campos essenciais estão presentes
            required_fields = ['id', 'code', 'name', 'reference', 'category', 'unit', 'description', 'unit_price']
            missing_fields = []
            
            for field in required_fields:
                if field not in material_data or material_data[field] is None:
                    missing_fields.append(field)
            
            if missing_fields:
                print(f"\n   ⚠️ Campos ausentes ou nulos: {missing_fields}")
                return False
            else:
                print(f"\n   ✅ Todos os campos essenciais estão presentes e preenchidos!")
                return True
                
        else:
            print(f"   ❌ Erro HTTP {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Erro durante o teste: {e}")
        return False

def check_browser_compatibility():
    """Verifica se há problemas de compatibilidade"""
    
    print(f"\n🌐 Verificação de Compatibilidade")
    print("-" * 30)
    
    # Verificar se o axios está disponível
    try:
        response = requests.get("http://localhost:8000/static/js/axios.min.js")
        if response.status_code == 200:
            print("   ✅ Axios disponível")
        else:
            print("   ❌ Axios não encontrado")
    except:
        print("   ⚠️ Não foi possível verificar Axios")
    
    # Verificar se o Bootstrap está disponível
    try:
        response = requests.get("http://localhost:8000/static/css/bootstrap.min.css")
        if response.status_code == 200:
            print("   ✅ Bootstrap CSS disponível")
        else:
            print("   ❌ Bootstrap CSS não encontrado")
    except:
        print("   ⚠️ Não foi possível verificar Bootstrap CSS")
    
    try:
        response = requests.get("http://localhost:8000/static/js/bootstrap.bundle.min.js")
        if response.status_code == 200:
            print("   ✅ Bootstrap JS disponível")
        else:
            print("   ❌ Bootstrap JS não encontrado")
    except:
        print("   ⚠️ Não foi possível verificar Bootstrap JS")

if __name__ == "__main__":
    print("🚀 Iniciando teste manual completo...")
    
    # Teste principal
    success = test_manual_edit()
    
    # Verificação de compatibilidade
    check_browser_compatibility()
    
    print(f"\n📊 Resultado Final:")
    if success:
        print("   ✅ TESTE PASSOU - A função deveria funcionar corretamente")
        print("\n💡 Se o problema persiste, pode ser:")
        print("   • Cache do navegador")
        print("   • JavaScript desabilitado")
        print("   • Erro de sintaxe não detectado")
        print("   • Conflito com outras bibliotecas")
        
        print(f"\n📋 Para verificar manualmente:")
        print("   1. Abra http://localhost:8000/materiais")
        print("   2. Pressione F12 para abrir DevTools")
        print("   3. Vá para a aba Console")
        print("   4. Clique em 'Editar' em qualquer material")
        print("   5. Verifique se aparecem os logs começando com '🔧 editMaterial chamada com ID:'")
        
    else:
        print("   ❌ TESTE FALHOU - Há problema na API ou dados")
    
    exit(0 if success else 1)