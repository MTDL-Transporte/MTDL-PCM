#!/usr/bin/env python3
"""
Teste dos endpoints de equipamentos
"""

import requests
import json

def test_equipment_endpoints():
    base_url = "http://localhost:8000"
    
    print("=== TESTE DOS ENDPOINTS DE EQUIPAMENTOS ===\n")
    
    # Testar listagem de equipamentos
    print("1. Testando listagem de equipamentos...")
    response = requests.get(f'{base_url}/maintenance/equipment')
    print(f'   Status: {response.status_code}')
    
    if response.status_code == 200:
        equipment_list = response.json()
        print(f'   Equipamentos encontrados: {len(equipment_list)}')
        for eq in equipment_list[:3]:
            print(f'   - ID: {eq.get("id")}, Nome: {eq.get("name")}, Horímetro: {eq.get("current_horimeter")}h')
        
        # Se temos equipamentos, testar endpoint individual
        if equipment_list:
            first_eq_id = equipment_list[0].get("id")
            print(f'\n2. Testando equipamento individual (ID: {first_eq_id})...')
            response = requests.get(f'{base_url}/maintenance/equipment/{first_eq_id}')
            print(f'   Status: {response.status_code}')
            if response.status_code == 200:
                equipment = response.json()
                print(f'   Nome: {equipment.get("name")}')
                print(f'   Horímetro atual: {equipment.get("current_horimeter")}h')
                print(f'   Horímetro inicial: {equipment.get("initial_horimeter")}h')
            else:
                print(f'   Erro: {response.text}')
    else:
        print(f'   Erro: {response.text}')
    
    # Testar alertas preventivos
    print(f'\n3. Testando alertas preventivos...')
    response = requests.get(f'{base_url}/maintenance/preventive-alerts')
    print(f'   Status: {response.status_code}')
    if response.status_code == 200:
        alerts = response.json()
        print(f'   Total de alertas: {alerts["total_alerts"]}')
        for alert in alerts['alerts']:
            print(f'   - {alert["equipment_name"]}: {alert["message"]}')
    else:
        print(f'   Erro: {response.text}')

if __name__ == "__main__":
    test_equipment_endpoints()