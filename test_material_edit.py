#!/usr/bin/env python3
"""
Script para testar a funcionalidade de edição de materiais
"""

import sys
import os
import requests
import json

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_material_edit():
    """Testar a edição de material"""
    base_url = "http://localhost:8000"
    
    try:
        # 1. Buscar o material existente
        print("1. Buscando material existente...")
        response = requests.get(f"{base_url}/api/warehouse/api/materials/1")
        if response.status_code == 200:
            material = response.json()
            print(f"   ✅ Material encontrado: {material['name']}")
            print(f"   📊 Código: {material['code']}")
            print(f"   💰 Preço atual: R$ {material.get('unit_price', 0):.2f}")
            print(f"   📦 Estoque atual: {material.get('current_stock', 0)}")
        else:
            print(f"   ❌ Erro ao buscar material: {response.status_code}")
            return False
        
        # 2. Testar atualização do preço unitário
        print("\n2. Testando atualização do preço unitário...")
        new_price = 150.00
        update_data = {"unit_price": new_price}
        
        response = requests.put(f"{base_url}/api/warehouse/api/materials/1", json=update_data)
        if response.status_code == 200:
            updated_material = response.json()
            print(f"   ✅ Preço atualizado para: R$ {updated_material.get('unit_price', 0):.2f}")
        else:
            print(f"   ❌ Erro ao atualizar preço: {response.status_code}")
            return False
        
        # 3. Verificar se a atualização foi persistida
        print("\n3. Verificando persistência da atualização...")
        response = requests.get(f"{base_url}/api/warehouse/api/materials/1")
        if response.status_code == 200:
            material = response.json()
            if material.get('unit_price') == new_price:
                print(f"   ✅ Preço persistido corretamente: R$ {material.get('unit_price', 0):.2f}")
            else:
                print(f"   ❌ Preço não foi persistido corretamente")
                return False
        else:
            print(f"   ❌ Erro ao verificar material: {response.status_code}")
            return False
        
        # 4. Calcular valor total
        print("\n4. Calculando valor total...")
        current_stock = material.get('current_stock', 0)
        unit_price = material.get('unit_price', 0)
        total_value = current_stock * unit_price
        print(f"   📦 Estoque atual: {current_stock}")
        print(f"   💰 Preço unitário: R$ {unit_price:.2f}")
        print(f"   💎 Valor total: R$ {total_value:.2f}")
        
        print("\n✅ Todos os testes passaram com sucesso!")
        return True
        
    except Exception as e:
        print(f"❌ Erro durante o teste: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testando funcionalidade de edição de materiais...")
    if test_material_edit():
        print("🎉 Funcionalidade funcionando corretamente!")
    else:
        print("💥 Funcionalidade com problemas!")