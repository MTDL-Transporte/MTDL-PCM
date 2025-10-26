import requests
import sqlite3

# Testar APIs atualizadas
print("=== Testando APIs atualizadas ===")

# Testar API de combustíveis com preço médio
try:
    response = requests.get("http://localhost:8000/api/warehouse/fuels")
    print(f"API Combustíveis: Status {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Combustíveis encontrados: {len(data['fuels'])}")
        for fuel in data['fuels']:
            print(f"  - {fuel['name']}: Preço médio R$ {fuel['average_price']:.2f}")
    else:
        print(f"Erro: {response.text}")
except Exception as e:
    print(f"Erro ao testar API de combustíveis: {e}")

print()

# Testar API específica de preço médio
fuel_ids = [2, 3, 4]  # IDs dos combustíveis de exemplo
for fuel_id in fuel_ids:
    try:
        response = requests.get(f"http://localhost:8000/api/warehouse/fuels/{fuel_id}/average-price")
        print(f"API Preço Médio (ID {fuel_id}): Status {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Preço médio: R$ {data['average_price']:.2f} ({data['entries_count']} entradas)")
        else:
            print(f"  Erro: {response.text}")
    except Exception as e:
        print(f"  Erro ao testar API de preço médio: {e}")

print()

# Testar API de equipamentos
try:
    response = requests.get("http://localhost:8000/api/warehouse/equipment/for-fueling")
    print(f"API Equipamentos: Status {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Equipamentos encontrados: {len(data['equipment'])}")
        for eq in data['equipment']:
            print(f"  - {eq['name']} (Horímetro: {eq['current_horimeter']})")
    else:
        print(f"Erro: {response.text}")
except Exception as e:
    print(f"Erro ao testar API de equipamentos: {e}")