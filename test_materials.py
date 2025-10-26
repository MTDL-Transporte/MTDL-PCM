import requests
import json

# Criar alguns materiais de teste
materials_data = [
    {
        'name': 'Parafuso M8x20',
        'reference': 'PAR-M8-20',
        'category': 'Peças',
        'unit': 'UN',
        'description': 'Parafuso sextavado M8 x 20mm',
        'minimum_stock': 100,
        'maximum_stock': 500,
        'unit_price': 0.50,
        'location': 'Prateleira A1',
        'status': 'Ativo'
    },
    {
        'name': 'Óleo Hidráulico ISO 68',
        'reference': 'OIL-HID-68',
        'category': 'Lubrificantes',
        'unit': 'L',
        'description': 'Óleo hidráulico ISO VG 68',
        'minimum_stock': 20,
        'maximum_stock': 100,
        'unit_price': 25.00,
        'location': 'Almoxarifado B',
        'status': 'Ativo'
    },
    {
        'name': 'Rolamento 6205',
        'reference': 'ROL-6205',
        'category': 'Peças',
        'unit': 'UN',
        'description': 'Rolamento rígido de esferas 6205',
        'minimum_stock': 10,
        'maximum_stock': 50,
        'unit_price': 45.00,
        'location': 'Prateleira C2',
        'status': 'Ativo'
    }
]

print('Criando materiais de teste...')
for i, material in enumerate(materials_data, 1):
    try:
        response = requests.post('http://localhost:8000/api/materials', json=material)
        if response.status_code == 200:
            print(f'✅ Material {i} criado: {material["name"]}')
        else:
            print(f'❌ Erro ao criar material {i}: {response.text}')
    except Exception as e:
        print(f'❌ Erro de conexão: {e}')

print('\nCriação de materiais concluída!')

# Testar recálculo de consumo médio
print('\nTestando recálculo de consumo médio...')
try:
    response = requests.post('http://localhost:8000/api/warehouse/recalculate-all-consumption')
    if response.status_code == 200:
        result = response.json()
        print(f'✅ Recálculo concluído: {result["message"]}')
        print(f'📊 Materiais processados: {result["processed_count"]}')
        print(f'🔄 Materiais atualizados: {result["updated_count"]}')
    else:
        print(f'❌ Erro no recálculo: {response.text}')
except Exception as e:
    print(f'❌ Erro de conexão: {e}')