#!/usr/bin/env python3
"""
Script para testar especificamente a função editMaterial
"""

import requests
import json

def test_edit_material_api():
    """Testa se a API está funcionando para o material criado"""
    
    print("🧪 Testando API para função editMaterial...")
    print("=" * 50)
    
    base_url = "http://localhost:8000"
    
    try:
        # 1. Testar endpoint de listagem
        print("1️⃣ Testando GET /api/warehouse/materials")
        response = requests.get(f"{base_url}/api/warehouse/materials")
        
        if response.status_code == 200:
            materials = response.json()
            print(f"✅ API funcionando - {len(materials)} materiais encontrados")
            
            if materials:
                material = materials[0]
                material_id = material['id']
                print(f"📦 Material de teste: ID {material_id} - {material['name']}")
                
                # 2. Testar endpoint específico do material
                print(f"\n2️⃣ Testando GET /api/warehouse/api/materials/{material_id}")
                detail_response = requests.get(f"{base_url}/api/warehouse/api/materials/{material_id}")
                
                if detail_response.status_code == 200:
                    material_detail = detail_response.json()
                    print("✅ Endpoint específico funcionando")
                    print("📋 Dados retornados:")
                    
                    # Verificar campos essenciais
                    essential_fields = [
                        'id', 'code', 'name', 'reference', 'category', 
                        'unit', 'description', 'unit_price', 'minimum_stock', 
                        'maximum_stock', 'current_stock'
                    ]
                    
                    for field in essential_fields:
                        value = material_detail.get(field, 'CAMPO AUSENTE')
                        print(f"   {field:20s}: {value}")
                    
                    # 3. Verificar se todos os campos necessários estão presentes
                    missing_fields = [field for field in essential_fields if field not in material_detail]
                    
                    if missing_fields:
                        print(f"\n❌ Campos ausentes: {missing_fields}")
                        return False
                    else:
                        print(f"\n✅ Todos os campos essenciais estão presentes")
                        
                        # 4. Simular o que a função editMaterial deveria fazer
                        print(f"\n3️⃣ Simulando preenchimento dos campos do modal:")
                        field_mapping = {
                            'material-id': material_detail['id'],
                            'material-code': material_detail['code'],
                            'material-name': material_detail['name'],
                            'material-reference': material_detail.get('reference', ''),
                            'material-category': material_detail['category'],
                            'material-unit': material_detail['unit'],
                            'material-description': material_detail.get('description', ''),
                            'material-unit-price': material_detail.get('unit_price', 0),
                            'minimum-stock': material_detail.get('minimum_stock', 0),
                            'maximum-stock': material_detail.get('maximum_stock', 0)
                        }
                        
                        for field_id, value in field_mapping.items():
                            print(f"   {field_id:25s} = {value}")
                        
                        return True
                else:
                    print(f"❌ Erro no endpoint específico: {detail_response.status_code}")
                    print(f"   Resposta: {detail_response.text}")
                    return False
            else:
                print("❌ Nenhum material encontrado")
                return False
        else:
            print(f"❌ Erro na API: {response.status_code}")
            print(f"   Resposta: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Erro de conexão - servidor não está rodando?")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return False

def create_debug_html():
    """Cria um arquivo HTML para testar a função editMaterial diretamente"""
    
    html_content = '''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Debug EditMaterial</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/axios/dist/axios.min.js"></script>
</head>
<body>
    <div class="container mt-5">
        <h2>🔧 Debug da Função editMaterial</h2>
        
        <div class="alert alert-info">
            <strong>Instruções:</strong>
            <ol>
                <li>Abra o DevTools (F12) e vá para a aba Console</li>
                <li>Clique no botão "Testar editMaterial" abaixo</li>
                <li>Observe os logs no console</li>
                <li>Verifique se os campos são preenchidos</li>
            </ol>
        </div>
        
        <button class="btn btn-primary mb-4" onclick="testEditMaterial()">
            🧪 Testar editMaterial com ID 1
        </button>
        
        <!-- Modal de teste (cópia do original) -->
        <div class="modal fade" id="materialModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Editar Material - Teste</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <form>
                            <input type="hidden" id="material-id">
                            
                            <div class="row">
                                <div class="col-md-4">
                                    <label for="material-code" class="form-label">Código</label>
                                    <input type="text" class="form-control" id="material-code" readonly>
                                </div>
                                <div class="col-md-4">
                                    <label for="material-reference" class="form-label">Referência</label>
                                    <input type="text" class="form-control" id="material-reference">
                                </div>
                                <div class="col-md-4">
                                    <label for="material-name" class="form-label">Nome</label>
                                    <input type="text" class="form-control" id="material-name">
                                </div>
                            </div>
                            
                            <div class="row mt-3">
                                <div class="col-md-6">
                                    <label for="material-category" class="form-label">Categoria</label>
                                    <select class="form-select" id="material-category">
                                        <option value="">Selecione uma categoria</option>
                                        <option value="Peças">Peças</option>
                                        <option value="Teste">Teste</option>
                                    </select>
                                </div>
                                <div class="col-md-6">
                                    <label for="material-unit" class="form-label">Unidade</label>
                                    <select class="form-select" id="material-unit">
                                        <option value="">Selecione uma unidade</option>
                                        <option value="UN">Unidade</option>
                                        <option value="PC">Peça</option>
                                    </select>
                                </div>
                            </div>
                            
                            <div class="mt-3">
                                <label for="material-description" class="form-label">Descrição</label>
                                <textarea class="form-control" id="material-description" rows="3"></textarea>
                            </div>
                            
                            <div class="row mt-3">
                                <div class="col-md-3">
                                    <label for="material-unit-price" class="form-label">Valor Unitário</label>
                                    <input type="number" class="form-control" id="material-unit-price" step="0.01">
                                </div>
                                <div class="col-md-3">
                                    <label for="minimum-stock" class="form-label">Estoque Mínimo</label>
                                    <input type="number" class="form-control" id="minimum-stock" step="0.01">
                                </div>
                                <div class="col-md-3">
                                    <label for="maximum-stock" class="form-label">Estoque Máximo</label>
                                    <input type="number" class="form-control" id="maximum-stock" step="0.01">
                                </div>
                                <div class="col-md-3">
                                    <label for="current-stock" class="form-label">Estoque Atual</label>
                                    <input type="number" class="form-control" id="current-stock" step="0.01" readonly>
                                </div>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    
    <script>
        // Função editMaterial copiada do original
        async function editMaterial(materialId) {
            console.log('🔧 editMaterial chamada com ID:', materialId);
            
            try {
                console.log('📡 Fazendo requisição para:', `/api/warehouse/api/materials/${materialId}`);
                
                const response = await axios.get(`/api/warehouse/api/materials/${materialId}`);
                console.log('📦 Dados recebidos:', response.data);
                
                const material = response.data;
                
                // Verificar se todos os elementos existem
                const elements = {
                    'material-id': document.getElementById('material-id'),
                    'material-code': document.getElementById('material-code'),
                    'material-name': document.getElementById('material-name'),
                    'material-reference': document.getElementById('material-reference'),
                    'material-category': document.getElementById('material-category'),
                    'material-unit': document.getElementById('material-unit'),
                    'material-description': document.getElementById('material-description'),
                    'material-unit-price': document.getElementById('material-unit-price'),
                    'minimum-stock': document.getElementById('minimum-stock'),
                    'maximum-stock': document.getElementById('maximum-stock'),
                    'current-stock': document.getElementById('current-stock')
                };
                
                console.log('🔍 Verificando elementos do DOM:');
                for (const [id, element] of Object.entries(elements)) {
                    if (element) {
                        console.log(`✅ ${id}: encontrado`);
                    } else {
                        console.error(`❌ ${id}: NÃO encontrado`);
                    }
                }
                
                // Preencher campos
                if (elements['material-id']) {
                    elements['material-id'].value = material.id || '';
                    console.log('✅ Preenchendo material-id com:', material.id);
                }
                
                if (elements['material-code']) {
                    elements['material-code'].value = material.code || '';
                    console.log('✅ Preenchendo material-code com:', material.code);
                }
                
                if (elements['material-name']) {
                    elements['material-name'].value = material.name || '';
                    console.log('✅ Preenchendo material-name com:', material.name);
                }
                
                if (elements['material-reference']) {
                    elements['material-reference'].value = material.reference || '';
                    console.log('✅ Preenchendo material-reference com:', material.reference);
                }
                
                if (elements['material-category']) {
                    elements['material-category'].value = material.category || '';
                    console.log('✅ Preenchendo material-category com:', material.category);
                }
                
                if (elements['material-unit']) {
                    elements['material-unit'].value = material.unit || '';
                    console.log('✅ Preenchendo material-unit com:', material.unit);
                }
                
                if (elements['material-description']) {
                    elements['material-description'].value = material.description || '';
                    console.log('✅ Preenchendo material-description com:', material.description);
                }
                
                if (elements['material-unit-price']) {
                    elements['material-unit-price'].value = material.unit_price || '';
                    console.log('✅ Preenchendo material-unit-price com:', material.unit_price);
                }
                
                if (elements['minimum-stock']) {
                    elements['minimum-stock'].value = material.minimum_stock || '';
                    console.log('✅ Preenchendo minimum-stock com:', material.minimum_stock);
                }
                
                if (elements['maximum-stock']) {
                    elements['maximum-stock'].value = material.maximum_stock || '';
                    console.log('✅ Preenchendo maximum-stock com:', material.maximum_stock);
                }
                
                if (elements['current-stock']) {
                    elements['current-stock'].value = material.current_stock || '';
                    console.log('✅ Preenchendo current-stock com:', material.current_stock);
                }
                
                // Abrir modal
                console.log('🎭 Abrindo modal...');
                const modal = new bootstrap.Modal(document.getElementById('materialModal'));
                modal.show();
                
                console.log('✅ editMaterial concluída com sucesso!');
                
            } catch (error) {
                console.error('❌ Erro na editMaterial:', error);
                if (error.response) {
                    console.error('📡 Resposta do servidor:', error.response.data);
                    console.error('📡 Status:', error.response.status);
                }
            }
        }
        
        function testEditMaterial() {
            console.log('🧪 Iniciando teste da função editMaterial...');
            editMaterial(1);
        }
        
        // Verificar se Axios e Bootstrap estão carregados
        window.addEventListener('DOMContentLoaded', function() {
            console.log('🔍 Verificando dependências:');
            console.log('📦 Axios:', typeof axios !== 'undefined' ? '✅ Carregado' : '❌ Não carregado');
            console.log('📦 Bootstrap:', typeof bootstrap !== 'undefined' ? '✅ Carregado' : '❌ Não carregado');
        });
    </script>
</body>
</html>'''
    
    with open('debug_edit_material.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print("📄 Arquivo debug_edit_material.html criado!")
    print("🌐 Abra este arquivo no navegador para testar a função editMaterial")

if __name__ == "__main__":
    print("🔧 Iniciando debug da função editMaterial...")
    print("=" * 60)
    
    # Testar API
    if test_edit_material_api():
        print("\n" + "=" * 60)
        print("✅ API está funcionando corretamente!")
        
        # Criar arquivo de debug
        print("\n" + "=" * 60)
        create_debug_html()
        
        print("\n" + "=" * 60)
        print("📋 PRÓXIMOS PASSOS:")
        print("1. Abra debug_edit_material.html no navegador")
        print("2. Abra o DevTools (F12) e vá para Console")
        print("3. Clique em 'Testar editMaterial'")
        print("4. Observe os logs e verifique se os campos são preenchidos")
        print("5. Compare com o comportamento na aplicação original")
    else:
        print("\n❌ Problemas encontrados na API - verifique o servidor")