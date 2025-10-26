import requests
from datetime import datetime

base_url = 'http://localhost:8000'

def test_step_by_step():
    print("=== TESTE PASSO A PASSO ===")
    
    # 1. Verificar horímetro atual
    print("\n1. Verificando horímetro atual...")
    try:
        response = requests.get(f'{base_url}/maintenance/equipment/1')
        if response.status_code == 200:
            equipment = response.json()
            current_horimeter = equipment.get('current_horimeter', 0)
            print(f'   Horímetro atual: {current_horimeter}h')
        else:
            print(f'   Erro ao buscar equipamento: {response.status_code}')
            return
    except Exception as e:
        print(f'   Erro: {e}')
        return
    
    # 2. Tentar registrar abastecimento com horímetro maior
    new_horimeter = current_horimeter + 10
    print(f"\n2. Tentando registrar abastecimento com horímetro {new_horimeter}h...")
    
    fueling_data = {
        'equipment_id': 1,
        'material_id': 2,  # DIESEL S10
        'quantity': 50.0,
        'unit_price': 5.50,
        'supplier': 'Posto Shell',
        'horimeter': new_horimeter,
        'date': datetime.now().isoformat(),
        'notes': 'Teste simples'
    }
    
    try:
        response = requests.post(f'{base_url}/api/warehouse/fueling', json=fueling_data)
        print(f'   Status: {response.status_code}')
        if response.status_code == 200:
            print(f'   Abastecimento registrado com sucesso!')
        else:
            print(f'   Erro: {response.text}')
            return
    except Exception as e:
        print(f'   Erro: {e}')
        return
    
    # 3. Verificar se horímetro foi atualizado
    print(f"\n3. Verificando se horímetro foi atualizado...")
    try:
        response = requests.get(f'{base_url}/maintenance/equipment/1')
        if response.status_code == 200:
            equipment = response.json()
            updated_horimeter = equipment.get('current_horimeter', 0)
            print(f'   Horímetro atualizado: {updated_horimeter}h')
        else:
            print(f'   Erro ao verificar equipamento: {response.status_code}')
    except Exception as e:
        print(f'   Erro: {e}')
    
    # 4. Verificar alertas
    print(f"\n4. Verificando alertas preventivos...")
    try:
        response = requests.get(f'{base_url}/maintenance/preventive-alerts')
        if response.status_code == 200:
            alerts = response.json()
            print(f'   Total de alertas: {len(alerts.get("alerts", []))}')
            for alert in alerts.get('alerts', []):
                print(f'   - {alert.get("equipment_name", "N/A")}: {alert.get("message", "N/A")}')
        else:
            print(f'   Erro ao buscar alertas: {response.status_code}')
    except Exception as e:
        print(f'   Erro: {e}')
    
    # 5. Verificar ordens de trabalho
    print(f"\n5. Verificando ordens de trabalho...")
    try:
        response = requests.get(f'{base_url}/maintenance/api/work-orders')
        if response.status_code == 200:
            work_orders = response.json()
            print(f'   Total de ordens: {len(work_orders)}')
            if len(work_orders) > 0:
                for wo in work_orders[-3:]:
                    print(f'   - #{wo.get("number", "N/A")}: {wo.get("title", "N/A")} - Status: {wo.get("status", "N/A")}')
        else:
            print(f'   Erro ao buscar ordens: {response.status_code}')
    except Exception as e:
        print(f'   Erro: {e}')
    
    print("\n=== TESTE CONCLUÍDO ===")

if __name__ == "__main__":
    test_step_by_step()