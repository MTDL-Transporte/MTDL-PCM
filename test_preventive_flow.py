#!/usr/bin/env python3
"""
Teste do fluxo completo de manutenção preventiva automatizada
"""

import requests
import json
from datetime import datetime

def test_preventive_maintenance_flow():
    base_url = "http://localhost:8000"
    
    print("=== TESTE DO FLUXO COMPLETO DE MANUTENÇÃO PREVENTIVA ===\n")
    
    # 1. Verificar horímetro atual
    print("1. Verificando horímetro atual...")
    response = requests.get(f'{base_url}/maintenance/equipment/1')
    equipment = response.json()
    print(f'   Horímetro atual: {equipment["current_horimeter"]}h')
    
    # 2. Registrar abastecimento que aumenta horímetro para 260h (acima da meta de 250h)
    print("\n2. Registrando abastecimento...")
    fueling_data = {
        'equipment_id': 1,
        'material_id': 2,  # DIESEL S10
        'quantity': 50.0,
        'unit_price': 5.50,
        'supplier': 'Posto Shell',
        'horimeter': 300.0,  # Aumentando para 300h (acima da meta de 250h)
        'date': datetime.now().isoformat(),
        'notes': 'Teste de fluxo completo - horímetro acima da meta'
    }
    
    print(f'   Registrando abastecimento com horímetro: {fueling_data["horimeter"]}h')
    response = requests.post(f'{base_url}/api/warehouse/fueling', json=fueling_data)
    print(f'   Status abastecimento: {response.status_code}')
    if response.status_code == 200:
        result = response.json()
        if 'id' in result:
            print(f'   Abastecimento registrado: {result["id"]}')
        else:
            print(f'   Abastecimento registrado com sucesso')
    else:
        print(f'   Erro: {response.text}')
        return
    
    # 3. Verificar se horímetro foi atualizado
    print("\n3. Verificando atualização do horímetro...")
    response = requests.get(f'{base_url}/maintenance/equipment/1')
    equipment = response.json()
    print(f'   Horímetro após abastecimento: {equipment["current_horimeter"]}h')
    
    # 4. Verificar alertas preventivos
    print("\n4. Verificando alertas preventivos...")
    response = requests.get(f'{base_url}/maintenance/preventive-alerts')
    alerts = response.json()
    print(f'   Total de alertas: {alerts["total_alerts"]}')
    print(f'   Vencidos: {alerts["overdue_count"]}')
    print(f'   Próximos: {alerts["upcoming_count"]}')
    
    for alert in alerts['alerts']:
        print(f'   - {alert["equipment_name"]}: {alert["message"]} ({alert["alert_type"]})')
    
    # 5. Verificar se foram geradas ordens de trabalho automaticamente
    print("\n5. Verificando ordens de trabalho...")
    response = requests.get(f'{base_url}/maintenance/api/work-orders')
    print(f'   Status da resposta: {response.status_code}')
    if response.status_code == 200:
        work_orders = response.json()
        print(f'   Total de ordens: {len(work_orders)}')
        
        # Mostrar as últimas 3 ordens
        for wo in work_orders[-3:]:
            print(f'   - #{wo["number"]}: {wo["title"]} - Status: {wo["status"]}')
    else:
        print(f'   Erro ao buscar ordens de trabalho: {response.status_code}')
        print(f'   Resposta: {response.text[:200]}...')
        return
    
    # 6. Testar geração automática de ordem de trabalho
    print("\n6. Testando geração automática de ordem de trabalho...")
    response = requests.post(f'{base_url}/maintenance/generate-preventive-work-orders')
    print(f'   Status geração: {response.status_code}')
    if response.status_code == 200:
        result = response.json()
        print(f'   Ordens geradas: {result.get("generated_count", 0)}')
        if "work_orders" in result:
            for wo in result["work_orders"]:
                print(f'   - Nova ordem: #{wo["number"]} - {wo["title"]}')
    else:
        print(f'   Erro: {response.text}')
    
    print("\n=== TESTE CONCLUÍDO ===")

if __name__ == "__main__":
    test_preventive_maintenance_flow()