#!/usr/bin/env python3
"""
Script para testar a API de materiais e identificar problemas
"""

import requests
import json

def test_api_endpoints():
    """Testa os endpoints da API relacionados à edição de materiais"""
    
    print("🔌 Testando endpoints da API...")
    print("=" * 60)
    
    try:
        # 1. Buscar lista de materiais
        print("1️⃣ Testando GET /api/warehouse/materials")
        response = requests.get("http://localhost:8000/api/warehouse/materials")
        response.raise_for_status()
        materials = response.json()
        
        print(f"   ✅ Encontrados {len(materials)} materiais")
        
        if not materials:
            print("   ❌ Nenhum material encontrado para testar")
            return False
        
        # Pegar o primeiro material para teste
        test_material = materials[0]
        material_id = test_material['id']
        
        print(f"   🎯 Usando material ID {material_id} para teste")
        print(f"   📝 Material: {test_material.get('name', 'N/A')}")
        
        # 2. Testar endpoint específico de material (usado pelo editMaterial)
        print(f"\n2️⃣ Testando GET /api/warehouse/api/materials/{material_id}")
        response = requests.get(f"http://localhost:8000/api/warehouse/api/materials/{material_id}")
        
        if response.status_code == 200:
            material_detail = response.json()
            print("   ✅ Endpoint funcionando corretamente")
            print("   📋 Dados retornados:")
            
            # Verificar campos essenciais
            essential_fields = ['id', 'code', 'name', 'reference', 'category', 'unit', 'description', 'unit_price']
            missing_fields = []
            
            for field in essential_fields:
                if field in material_detail:
                    value = material_detail[field]
                    print(f"      ✅ {field}: {value}")
                else:
                    missing_fields.append(field)
                    print(f"      ❌ {field}: AUSENTE")
            
            # Verificar campos de estoque
            stock_fields = ['minimum_stock', 'maximum_stock', 'current_stock']
            print("   📦 Campos de estoque:")
            for field in stock_fields:
                if field in material_detail:
                    value = material_detail[field]
                    print(f"      ✅ {field}: {value}")
                else:
                    print(f"      ⚠️ {field}: AUSENTE")
            
            if missing_fields:
                print(f"\n   ⚠️ Campos essenciais ausentes: {missing_fields}")
                return False
            else:
                print("\n   ✅ Todos os campos essenciais estão presentes")
                return True
                
        else:
            print(f"   ❌ Erro HTTP {response.status_code}: {response.text}")
            return False
        
    except requests.exceptions.ConnectionError:
        print("❌ Erro de conexão - servidor não está rodando?")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return False

def analyze_javascript_function():
    """Analisa a função JavaScript editMaterial"""
    
    print("\n🔍 Analisando função JavaScript...")
    print("-" * 40)
    
    try:
        with open("templates/warehouse/materials.html", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Procurar pela função editMaterial
        if "async function editMaterial(materialId)" in content:
            print("✅ Função editMaterial encontrada")
            
            # Verificar se tem os logs de debug
            if "console.log('🔧 editMaterial chamada com ID:'," in content:
                print("✅ Logs de debug estão presentes")
            else:
                print("❌ Logs de debug não encontrados")
            
            # Verificar se está usando os IDs corretos
            if "document.getElementById('material-code')" in content:
                print("✅ Função usa getElementById para material-code")
            else:
                print("❌ Função não usa getElementById para material-code")
            
            # Verificar URL da API
            if "/api/warehouse/api/materials/" in content:
                print("✅ URL da API está correta")
            else:
                print("❌ URL da API pode estar incorreta")
                
        else:
            print("❌ Função editMaterial não encontrada")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao analisar JavaScript: {e}")
        return False

def check_html_structure():
    """Verifica a estrutura HTML do modal"""
    
    print("\n🏗️ Verificando estrutura HTML...")
    print("-" * 40)
    
    try:
        with open("templates/warehouse/materials.html", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Verificar IDs essenciais do modal de edição
        essential_ids = [
            'material-id', 'material-code', 'material-name', 
            'material-reference', 'material-category', 'material-unit',
            'material-description', 'material-unit-price', 
            'minimum-stock', 'maximum-stock', 'material-status'
        ]
        
        missing_ids = []
        for element_id in essential_ids:
            if f'id="{element_id}"' in content:
                print(f"   ✅ {element_id}")
            else:
                missing_ids.append(element_id)
                print(f"   ❌ {element_id}")
        
        if missing_ids:
            print(f"\n   ⚠️ IDs ausentes: {missing_ids}")
            return False
        else:
            print("\n   ✅ Todos os IDs essenciais estão presentes")
            return True
        
    except Exception as e:
        print(f"❌ Erro ao verificar HTML: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Diagnóstico completo do problema de edição...")
    
    # Teste 1: API
    api_success = test_api_endpoints()
    
    # Teste 2: JavaScript
    js_success = analyze_javascript_function()
    
    # Teste 3: HTML
    html_success = check_html_structure()
    
    print(f"\n📊 Resumo dos resultados:")
    print(f"   API: {'✅ OK' if api_success else '❌ PROBLEMA'}")
    print(f"   JavaScript: {'✅ OK' if js_success else '❌ PROBLEMA'}")
    print(f"   HTML: {'✅ OK' if html_success else '❌ PROBLEMA'}")
    
    if api_success and js_success and html_success:
        print("\n💡 Todos os componentes parecem estar corretos.")
        print("   O problema pode estar na execução do JavaScript no navegador.")
        print("   Recomendação: Verificar console do navegador manualmente.")
    elif not api_success:
        print("\n💡 Problema identificado na API - verificar backend")
    elif not js_success:
        print("\n💡 Problema identificado no JavaScript")
    elif not html_success:
        print("\n💡 Problema identificado na estrutura HTML")
    
    print("\n📋 Próximos passos:")
    print("   1. Abrir http://localhost:8000/materiais no navegador")
    print("   2. Abrir DevTools (F12)")
    print("   3. Ir para aba Console")
    print("   4. Clicar em 'Editar' em qualquer material")
    print("   5. Verificar logs que aparecem no console")
    
    exit(0 if (api_success and js_success and html_success) else 1)