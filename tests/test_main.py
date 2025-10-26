"""
Testes para a aplicação principal MTDL-PCM
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from app.database import get_db, Base

# Configurar banco de dados de teste em memória
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override da função get_db para usar banco de teste"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


# Override da dependência do banco de dados
app.dependency_overrides[get_db] = override_get_db

# Cliente de teste
client = TestClient(app)


@pytest.fixture(scope="function")
def test_db():
    """Fixture para criar e limpar banco de dados de teste"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


class TestMainApplication:
    """Testes para aplicação principal"""
    
    def test_read_main(self, test_db):
        """Teste da página principal"""
        response = client.get("/")
        assert response.status_code == 200
        assert "MTDL-PCM" in response.text
    
    def test_health_check(self, test_db):
        """Teste do endpoint de health check"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["message"] == "MTDL-PCM está funcionando corretamente"
        assert data["version"] == "1.0.0"
    
    def test_404_handler(self, test_db):
        """Teste do handler de página não encontrada"""
        response = client.get("/pagina-inexistente")
        assert response.status_code == 404
        assert "Página não encontrada" in response.text
    
    def test_static_files(self, test_db):
        """Teste de acesso a arquivos estáticos"""
        # Teste CSS
        response = client.get("/static/css/style.css")
        assert response.status_code == 200
        
        # Teste JavaScript
        response = client.get("/static/js/app.js")
        assert response.status_code == 200


class TestDashboardRoutes:
    """Testes para rotas do dashboard"""
    
    def test_dashboard_metrics(self, test_db):
        """Teste das métricas do dashboard"""
        response = client.get("/api/dashboard/metrics")
        assert response.status_code == 200
        data = response.json()
        
        # Verificar estrutura das métricas
        assert "work_orders" in data
        assert "equipment" in data
        assert "materials" in data
        assert "alerts" in data
    
    def test_dashboard_charts(self, test_db):
        """Teste dos dados para gráficos"""
        response = client.get("/api/dashboard/charts")
        assert response.status_code == 200
        data = response.json()
        
        # Verificar estrutura dos gráficos
        assert "work_orders_by_status" in data
        assert "maintenance_costs" in data
        assert "equipment_status" in data


class TestMaintenanceRoutes:
    """Testes para rotas de manutenção"""
    
    def test_work_orders_page(self, test_db):
        """Teste da página de ordens de serviço"""
        response = client.get("/maintenance/work-orders")
        assert response.status_code == 200
        assert "Ordens de Serviço" in response.text
    
    def test_work_orders_api(self, test_db):
        """Teste da API de ordens de serviço"""
        response = client.get("/maintenance/api/work-orders")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_equipment_api(self, test_db):
        """Teste da API de equipamentos"""
        response = client.get("/maintenance/api/equipment")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestWarehouseRoutes:
    """Testes para rotas do almoxarifado"""
    
    def test_materials_page(self, test_db):
        """Teste da página de materiais"""
        response = client.get("/warehouse/materials")
        assert response.status_code == 200
        assert "Gestão de Materiais" in response.text
    
    def test_materials_api(self, test_db):
        """Teste da API de materiais"""
        response = client.get("/warehouse/api/materials")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_stock_movements_api(self, test_db):
        """Teste da API de movimentações de estoque"""
        response = client.get("/warehouse/api/stock-movements")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestReportsRoutes:
    """Testes para rotas de relatórios"""
    
    def test_reports_page(self, test_db):
        """Teste da página de relatórios"""
        response = client.get("/reports")
        assert response.status_code == 200
        assert "Relatórios" in response.text
    
    def test_maintenance_metrics(self, test_db):
        """Teste das métricas de manutenção"""
        response = client.get("/reports/api/maintenance-metrics")
        assert response.status_code == 200
        data = response.json()
        
        # Verificar estrutura das métricas
        assert "mttr" in data
        assert "mtbf" in data
        assert "total_costs" in data
    
    def test_warehouse_metrics(self, test_db):
        """Teste das métricas do almoxarifado"""
        response = client.get("/reports/api/warehouse-metrics")
        assert response.status_code == 200
        data = response.json()
        
        # Verificar estrutura das métricas
        assert "abc_analysis" in data
        assert "stock_turnover" in data
        assert "supplier_performance" in data


class TestAPIValidation:
    """Testes de validação da API"""
    
    def test_create_work_order_validation(self, test_db):
        """Teste de validação ao criar ordem de serviço"""
        # Dados inválidos
        invalid_data = {
            "title": "",  # Título vazio
            "equipment_id": "invalid",  # ID inválido
            "priority": "invalid_priority"  # Prioridade inválida
        }
        
        response = client.post("/maintenance/api/work-orders", json=invalid_data)
        assert response.status_code == 422  # Unprocessable Entity
    
    def test_create_material_validation(self, test_db):
        """Teste de validação ao criar material"""
        # Dados inválidos
        invalid_data = {
            "name": "",  # Nome vazio
            "unit_price": -10,  # Preço negativo
            "minimum_stock": -5  # Estoque mínimo negativo
        }
        
        response = client.post("/warehouse/api/materials", json=invalid_data)
        assert response.status_code == 422  # Unprocessable Entity


if __name__ == "__main__":
    pytest.main([__file__])