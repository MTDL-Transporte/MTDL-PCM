#!/usr/bin/env python3
"""
Script para testar o registro de abastecimento após correção dos parâmetros
"""

import requests
import json

def test_fueling():
    """Testa o registro de abastecimento"""
    
    # URL da API
    url = "http://localhost:8000/api/warehouse/fueling"
    
    # Dados do abastecimento
    fueling_data = {
        "equipment_id": 1,  # BR20/E048
        "material_id": 1,   # DIESEL S10
        "quantity": 50.0,
        "horimeter": 225.0,  # Aumentando para 225h para gerar alerta
        "unit_cost": 5.50,
        "operator": "Operador Teste",
        "notes": "Teste de abastecimento para gerar alerta de manutenção"
    }
    
    try:
        print("Registrando abastecimento...")
        print(f"Dados: {json.dumps(fueling_data, indent=2)}")
        
        response = requests.post(url, json=fueling_data)
        
        print(f"Status: {response.status_code}")
        print(f"Resposta: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            print("\n✅ Abastecimento registrado com sucesso!")
            print(f"ID do abastecimento: {result.get('id')}")
            
            # Verificar se alertas foram gerados
            if result.get('maintenance_alerts'):
                print(f"\n🔔 Alertas de manutenção gerados: {len(result['maintenance_alerts'])}")
                for alert in result['maintenance_alerts']:
                    print(f"  - {alert}")
            else:
                print("\n⚠️ Nenhum alerta de manutenção foi gerado")
                
        else:
            print(f"\n❌ Erro no registro: {response.text}")
            
    except Exception as e:
        print(f"❌ Erro na requisição: {str(e)}")

if __name__ == "__main__":
    test_fueling()