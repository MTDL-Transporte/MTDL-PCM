import requests

base_url = 'http://localhost:8000'

print("=== TESTE DE ENDPOINTS DE ORDENS DE TRABALHO ===")

# Testar diferentes endpoints possíveis
endpoints = [
    '/api/maintenance/work-orders',
    '/maintenance/api/work-orders',
    '/work-orders',
    '/api/work-orders'
]

for endpoint in endpoints:
    print(f"\nTestando: {endpoint}")
    try:
        response = requests.get(f'{base_url}{endpoint}')
        print(f'   Status: {response.status_code}')
        if response.status_code == 200:
            try:
                data = response.json()
                print(f'   Dados: {type(data)} com {len(data) if isinstance(data, list) else "N/A"} itens')
                if isinstance(data, list) and len(data) > 0:
                    print(f'   Primeiro item: {data[0]}')
            except:
                print(f'   Resposta não é JSON válido')
        else:
            print(f'   Erro: {response.text[:100]}...')
    except Exception as e:
        print(f'   Exceção: {e}')