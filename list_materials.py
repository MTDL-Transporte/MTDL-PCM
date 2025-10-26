#!/usr/bin/env python3
"""
Listar todos os materiais disponíveis no sistema
"""

import requests
import json

def list_materials():
    base_url = "http://localhost:8000"
    
    print("=== LISTANDO MATERIAIS ===\n")
    
    # Buscar materiais
    response = requests.get(f'{base_url}/api/warehouse/materials')
    if response.status_code == 200:
        materials = response.json()
        print(f'Total de materiais: {len(materials)}')
        
        print('\nTodos os materiais:')
        for m in materials:
            print(f'- ID: {m.get("id")}, Nome: {m.get("name")}, Categoria: {m.get("category")}, Unidade: {m.get("unit")}')
            
        # Procurar por combustíveis
        fuel_materials = []
        for m in materials:
            name = m.get('name', '').lower()
            category = m.get('category', '').lower()
            if any(keyword in name for keyword in ['diesel', 'combustível', 'gasolina', 'óleo', 'fuel']) or \
               any(keyword in category for keyword in ['combustível', 'combustíveis', 'fuel']):
                fuel_materials.append(m)
        
        if fuel_materials:
            print('\nMateriais de combustível encontrados:')
            for fuel in fuel_materials:
                print(f'- ID: {fuel.get("id")}, Nome: {fuel.get("name")}, Categoria: {fuel.get("category")}')
        else:
            print('\nNenhum material de combustível específico encontrado.')
            print('Vou criar um material de combustível para o teste...')
            
            # Criar material de combustível
            fuel_data = {
                "code": "COMB001",
                "name": "Diesel S10",
                "description": "Combustível diesel S10 para equipamentos",
                "category": "Combustível",
                "unit": "L",
                "current_stock": 1000.0,
                "minimum_stock": 100.0,
                "maximum_stock": 2000.0,
                "average_cost": 5.50,
                "location": "Tanque Principal",
                "is_active": True
            }
            
            response = requests.post(f'{base_url}/api/warehouse/materials', json=fuel_data)
            if response.status_code == 200:
                new_material = response.json()
                print(f'Material criado: ID {new_material.get("id")} - {new_material.get("name")}')
            else:
                print(f'Erro ao criar material: {response.status_code} - {response.text}')
    else:
        print(f'Erro ao buscar materiais: {response.status_code} - {response.text}')

if __name__ == "__main__":
    list_materials()