"""
Testes para os modelos do banco de dados MTDL-PCM
"""

import pytest
from datetime import datetime, date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.equipment import Equipment, HorimeterLog
from app.models.maintenance import WorkOrder, MaintenancePlan, WorkOrderMaterial, TimeLog, WorkOrderChecklist
from app.models.warehouse import Material, StockMovement, Supplier, PurchaseRequest, PurchaseRequestItem, Quotation, QuotationItem

# Configurar banco de dados de teste em memória
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Fixture para sessão do banco de dados de teste"""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


class TestEquipmentModels:
    """Testes para modelos de equipamentos"""
    
    def test_create_equipment(self, db_session):
        """Teste de criação de equipamento"""
        equipment = Equipment(
            prefix="EQ001",
            name="Escavadeira Hidráulica",
            model="PC200",
            manufacturer="Komatsu",
            year=2020,
            serial_number="ABC123456",
            status="operacional",
            current_horimeter=1500.5
        )
        
        db_session.add(equipment)
        db_session.commit()
        
        # Verificar se foi salvo corretamente
        saved_equipment = db_session.query(Equipment).filter_by(prefix="EQ001").first()
        assert saved_equipment is not None
        assert saved_equipment.name == "Escavadeira Hidráulica"
        assert saved_equipment.current_horimeter == 1500.5
        assert saved_equipment.status == "operacional"
    
    def test_horimeter_log(self, db_session):
        """Teste de log de horímetro"""
        # Criar equipamento
        equipment = Equipment(
            prefix="EQ002",
            name="Trator",
            model="T100",
            manufacturer="John Deere",
            year=2019,
            current_horimeter=1000.0
        )
        db_session.add(equipment)
        db_session.commit()
        
        # Criar log de horímetro
        horimeter_log = HorimeterLog(
            equipment_id=equipment.id,
            previous_reading=1000.0,
            current_reading=1050.5,
            hours_worked=50.5,
            recorded_by="Operador João"
        )
        
        db_session.add(horimeter_log)
        db_session.commit()
        
        # Verificar relacionamento
        saved_log = db_session.query(HorimeterLog).first()
        assert saved_log.equipment.prefix == "EQ002"
        assert saved_log.hours_worked == 50.5


class TestMaintenanceModels:
    """Testes para modelos de manutenção"""
    
    def test_create_work_order(self, db_session):
        """Teste de criação de ordem de serviço"""
        # Criar equipamento primeiro
        equipment = Equipment(
            prefix="EQ003",
            name="Caminhão",
            model="Actros",
            manufacturer="Mercedes-Benz",
            year=2021
        )
        db_session.add(equipment)
        db_session.commit()
        
        # Criar ordem de serviço
        work_order = WorkOrder(
            number="100001",
            title="Troca de óleo",
            description="Troca de óleo do motor",
            equipment_id=equipment.id,
            priority="media",
            status="aberta",
            requested_by="Supervisor",
            estimated_hours=2.0
        )
        
        db_session.add(work_order)
        db_session.commit()
        
        # Verificar se foi salvo corretamente
        saved_wo = db_session.query(WorkOrder).filter_by(number="100001").first()
        assert saved_wo is not None
        assert saved_wo.title == "Troca de óleo"
        assert saved_wo.equipment.prefix == "EQ003"
        assert saved_wo.priority == "media"
    
    def test_maintenance_plan(self, db_session):
        """Teste de plano de manutenção"""
        # Criar equipamento
        equipment = Equipment(
            prefix="EQ004",
            name="Gerador",
            model="G500",
            manufacturer="Caterpillar",
            year=2020
        )
        db_session.add(equipment)
        db_session.commit()
        
        # Criar plano de manutenção
        plan = MaintenancePlan(
            name="Manutenção Preventiva Gerador",
            equipment_id=equipment.id,
            maintenance_type="preventiva",
            interval_type="horas",
            interval_value=500,
            description="Inspeção geral e troca de filtros"
        )
        
        db_session.add(plan)
        db_session.commit()
        
        # Verificar relacionamento
        saved_plan = db_session.query(MaintenancePlan).first()
        assert saved_plan.equipment.prefix == "EQ004"
        assert saved_plan.interval_value == 500
    
    def test_time_log(self, db_session):
        """Teste de registro de tempo"""
        # Criar equipamento e ordem de serviço
        equipment = Equipment(prefix="EQ005", name="Empilhadeira")
        db_session.add(equipment)
        db_session.commit()
        
        work_order = WorkOrder(
            number="100002",
            title="Reparo hidráulico",
            equipment_id=equipment.id,
            status="em_andamento"
        )
        db_session.add(work_order)
        db_session.commit()
        
        # Criar registro de tempo
        time_log = TimeLog(
            work_order_id=work_order.id,
            technician="João Silva",
            start_time=datetime(2024, 1, 15, 8, 0),
            end_time=datetime(2024, 1, 15, 12, 0),
            hours_worked=4.0,
            description="Desmontagem do sistema hidráulico"
        )
        
        db_session.add(time_log)
        db_session.commit()
        
        # Verificar relacionamento
        saved_log = db_session.query(TimeLog).first()
        assert saved_log.work_order.number == "100002"
        assert saved_log.hours_worked == 4.0


class TestWarehouseModels:
    """Testes para modelos do almoxarifado"""
    
    def test_create_material(self, db_session):
        """Teste de criação de material"""
        material = Material(
            code="MAT001",
            name="Óleo Motor 15W40",
            description="Óleo lubrificante para motores diesel",
            unit="litro",
            unit_price=25.50,
            current_stock=100,
            minimum_stock=20,
            maximum_stock=200,
            location="A1-B2-C3"
        )
        
        db_session.add(material)
        db_session.commit()
        
        # Verificar se foi salvo corretamente
        saved_material = db_session.query(Material).filter_by(code="MAT001").first()
        assert saved_material is not None
        assert saved_material.name == "Óleo Motor 15W40"
        assert saved_material.unit_price == 25.50
        assert saved_material.current_stock == 100
    
    def test_stock_movement(self, db_session):
        """Teste de movimentação de estoque"""
        # Criar material
        material = Material(
            code="MAT002",
            name="Filtro de Óleo",
            unit="unidade",
            unit_price=15.00,
            current_stock=50
        )
        db_session.add(material)
        db_session.commit()
        
        # Criar movimentação
        movement = StockMovement(
            material_id=material.id,
            movement_type="saida",
            quantity=5,
            unit_price=15.00,
            total_value=75.00,
            reason="Aplicação em manutenção",
            reference_document="OS-100001",
            moved_by="Almoxarife"
        )
        
        db_session.add(movement)
        db_session.commit()
        
        # Verificar relacionamento
        saved_movement = db_session.query(StockMovement).first()
        assert saved_movement.material.code == "MAT002"
        assert saved_movement.quantity == 5
        assert saved_movement.movement_type == "saida"
    
    def test_supplier(self, db_session):
        """Teste de fornecedor"""
        supplier = Supplier(
            name="Distribuidora ABC Ltda",
            cnpj="12.345.678/0001-90",
            contact_person="Maria Santos",
            phone="(11) 1234-5678",
            email="contato@abc.com.br",
            address="Rua das Flores, 123",
            city="São Paulo",
            state="SP",
            zip_code="01234-567",
            status="ativo"
        )
        
        db_session.add(supplier)
        db_session.commit()
        
        # Verificar se foi salvo corretamente
        saved_supplier = db_session.query(Supplier).filter_by(cnpj="12.345.678/0001-90").first()
        assert saved_supplier is not None
        assert saved_supplier.name == "Distribuidora ABC Ltda"
        assert saved_supplier.status == "ativo"
    
    def test_purchase_request(self, db_session):
        """Teste de requisição de compra"""
        # Criar material
        material = Material(
            code="MAT003",
            name="Pneu 295/80R22.5",
            unit="unidade",
            unit_price=800.00
        )
        db_session.add(material)
        db_session.commit()
        
        # Criar requisição
        request = PurchaseRequest(
            number="REQ001",
            requested_by="Supervisor Manutenção",
            department="Manutenção",
            justification="Reposição de pneus desgastados",
            status="pendente",
            priority="alta"
        )
        db_session.add(request)
        db_session.commit()
        
        # Criar item da requisição
        item = PurchaseRequestItem(
            purchase_request_id=request.id,
            material_id=material.id,
            quantity=4,
            unit_price=800.00,
            total_price=3200.00,
            specifications="Pneu radial para caminhão"
        )
        db_session.add(item)
        db_session.commit()
        
        # Verificar relacionamentos
        saved_request = db_session.query(PurchaseRequest).first()
        assert saved_request.number == "REQ001"
        assert len(saved_request.items) == 1
        assert saved_request.items[0].material.code == "MAT003"


class TestModelValidations:
    """Testes de validações dos modelos"""
    
    def test_equipment_unique_prefix(self, db_session):
        """Teste de unicidade do prefixo do equipamento"""
        # Criar primeiro equipamento
        equipment1 = Equipment(prefix="EQ999", name="Equipamento 1")
        db_session.add(equipment1)
        db_session.commit()
        
        # Tentar criar segundo equipamento com mesmo prefixo
        equipment2 = Equipment(prefix="EQ999", name="Equipamento 2")
        db_session.add(equipment2)
        
        with pytest.raises(Exception):  # Deve gerar erro de integridade
            db_session.commit()
    
    def test_material_unique_code(self, db_session):
        """Teste de unicidade do código do material"""
        # Criar primeiro material
        material1 = Material(code="MAT999", name="Material 1", unit="unidade")
        db_session.add(material1)
        db_session.commit()
        
        # Tentar criar segundo material com mesmo código
        material2 = Material(code="MAT999", name="Material 2", unit="unidade")
        db_session.add(material2)
        
        with pytest.raises(Exception):  # Deve gerar erro de integridade
            db_session.commit()


if __name__ == "__main__":
    pytest.main([__file__])