"""
Modelos relacionados ao almoxarifado
"""

from sqlalchemy import Column, Integer, String, DateTime, Float, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from typing import Optional
from app.database import Base

class Material(Base):
    """Modelo para materiais do estoque"""
    __tablename__ = "materials"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False)  # Gerado automaticamente a partir de 100000
    name = Column(String(200), nullable=False)
    description = Column(Text)
    reference = Column(String(100))  # Campo de referência para facilitar identificação
    category = Column(String(100))
    unit = Column(String(20), nullable=False)  # UN, KG, L, M, etc.
    current_stock = Column(Float, default=0.0)
    minimum_stock = Column(Float, nullable=False)  # Obrigatório
    maximum_stock = Column(Float, nullable=False)  # Obrigatório
    average_consumption = Column(Float, default=0.0)  # Substituiu current_stock como campo calculado
    average_cost = Column(Float, default=0.0)
    unit_price = Column(Float, default=0.0)  # Preço unitário do material
    location = Column(String(100))
    barcode = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relacionamentos
    stock_movements = relationship("StockMovement", back_populates="material")
    purchase_requests = relationship("PurchaseRequestItem", back_populates="material")
    # work_order_materials = relationship("WorkOrderMaterial", back_populates="material")  # TEMPORARIAMENTE DESABILITADO
    # maintenance_plan_materials = relationship("MaintenancePlanMaterial", back_populates="material")  # TEMPORARIAMENTE DESABILITADO

class StockMovement(Base):
    """Movimentações de estoque"""
    __tablename__ = "stock_movements"
    
    id = Column(Integer, primary_key=True, index=True)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False)
    type = Column(String(20), nullable=False)  # Entrada, Saída, Ajuste
    quantity = Column(Float, nullable=False)
    unit_cost = Column(Float)
    total_cost = Column(Float)
    previous_stock = Column(Float, nullable=False)
    new_stock = Column(Float, nullable=False)
    reference_document = Column(String(100))  # NF, OS, etc.
    reason = Column(String(200))
    performed_by = Column(String(100))
    date = Column(DateTime, default=func.now())
    notes = Column(Text)
    cost_center = Column(String(100))
    equipment_id = Column(Integer, ForeignKey("equipments.id"))
    application = Column(String(200))
    
    # Relacionamentos
    material = relationship("Material", back_populates="stock_movements")
    equipment = relationship("Equipment")

class Supplier(Base):
    """Fornecedores"""
    __tablename__ = "suppliers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    cnpj = Column(String(18))
    contact_person = Column(String(100))
    phone = Column(String(20))
    email = Column(String(100))
    address = Column(Text)
    is_active = Column(Boolean, default=True)
    rating = Column(Float)  # Avaliação do fornecedor
    created_at = Column(DateTime, default=func.now())
    
    # Relacionamentos
    purchase_requests = relationship("PurchaseRequest", back_populates="supplier")
    quotations = relationship("Quotation", back_populates="supplier")

class PurchaseRequest(Base):
    """Requisições de compra"""
    __tablename__ = "purchase_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    number = Column(String(20), unique=True, index=True, nullable=False)
    requester = Column(String(100), nullable=False)
    department = Column(String(100))
    cost_center = Column(String(100))  # Centro de custo
    justification = Column(Text)
    stock_justification = Column(Text)  # Justificativa quando há estoque disponível
    status = Column(String(20), default="Pendente")  # Pendente, Aprovada, Rejeitada, Comprada
    priority = Column(String(20), default="Normal")
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    total_value = Column(Float, default=0.0)
    requested_date = Column(DateTime, default=func.now())
    approved_date = Column(DateTime)
    approved_by = Column(String(100))
    
    # Relacionamentos
    supplier = relationship("Supplier", back_populates="purchase_requests")
    items = relationship("PurchaseRequestItem", back_populates="purchase_request")
    purchase_orders = relationship("PurchaseOrder", back_populates="purchase_request")

class PurchaseRequestItem(Base):
    """Itens das requisições de compra"""
    __tablename__ = "purchase_request_items"
    
    id = Column(Integer, primary_key=True, index=True)
    purchase_request_id = Column(Integer, ForeignKey("purchase_requests.id"), nullable=False)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    unit_price = Column(Float)
    total_price = Column(Float)
    specifications = Column(Text)
    
    # Relacionamentos
    purchase_request = relationship("PurchaseRequest", back_populates="items")
    material = relationship("Material", back_populates="purchase_requests")

class Quotation(Base):
    """Cotações de preços"""
    __tablename__ = "quotations"
    
    id = Column(Integer, primary_key=True, index=True)
    number = Column(String(20), unique=True, index=True, nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    purchase_request_id = Column(Integer, ForeignKey("purchase_requests.id"))
    status = Column(String(20), default="Pendente")  # Pendente, Recebida, Aprovada, Rejeitada
    total_value = Column(Float, default=0.0)
    delivery_time = Column(Integer)  # Dias
    payment_terms = Column(String(200))
    validity_date = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    
    # Relacionamentos
    supplier = relationship("Supplier", back_populates="quotations")
    items = relationship("QuotationItem", back_populates="quotation")

class QuotationItem(Base):
    """Itens das cotações"""
    __tablename__ = "quotation_items"
    
    id = Column(Integer, primary_key=True, index=True)
    quotation_id = Column(Integer, ForeignKey("quotations.id"), nullable=False)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    
    # Relacionamentos
    quotation = relationship("Quotation", back_populates="items")

class StockNotification(Base):
    """Notificações de estoque para manutenção preventiva"""
    __tablename__ = "stock_notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    work_order_id = Column(Integer, ForeignKey("work_orders.id"), nullable=False)
    equipment_id = Column(Integer, ForeignKey("equipments.id"), nullable=False)
    maintenance_plan_id = Column(Integer, ForeignKey("maintenance_plans.id"), nullable=False)
    status = Column(String(20), default="Pendente")  # Pendente, Atendida, Cancelada
    priority = Column(String(20), default="Normal")  # Baixa, Normal, Alta, Crítica
    message = Column(Text)
    created_at = Column(DateTime, default=func.now())
    attended_at = Column(DateTime)
    attended_by = Column(String(100))
    notes = Column(Text)
    
    # Relacionamentos - Comentados temporariamente para evitar problemas de importação circular
    # work_order = relationship("WorkOrder")
    # equipment = relationship("Equipment")
    # maintenance_plan = relationship("MaintenancePlan")

class StockNotificationItem(Base):
    """Itens de material necessários para a notificação de estoque"""
    __tablename__ = "stock_notification_items"
    
    id = Column(Integer, primary_key=True, index=True)
    notification_id = Column(Integer, ForeignKey("stock_notifications.id"), nullable=False)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False)
    quantity_needed = Column(Float, nullable=False)
    quantity_available = Column(Float, nullable=False)
    quantity_reserved = Column(Float, default=0.0)
    status = Column(String(20), default="Pendente")  # Pendente, Reservado, Entregue
    
    # Relacionamentos
    notification = relationship("StockNotification")
    material = relationship("Material")

class InventoryHistory(Base):
    """Histórico de inventários realizados"""
    __tablename__ = "inventory_history"
    
    id = Column(Integer, primary_key=True, index=True)
    inventory_number = Column(String(20), unique=True, index=True, nullable=False)  # Número único do inventário
    process_date = Column(DateTime, default=func.now())
    processed_by = Column(String(100))
    total_items = Column(Integer, nullable=False)
    items_counted = Column(Integer, nullable=False)
    items_correct = Column(Integer, nullable=False)
    items_with_difference = Column(Integer, nullable=False)
    accuracy_percentage = Column(Float, nullable=False)
    total_adjustments = Column(Integer, default=0)
    notes = Column(Text)
    
    # Relacionamentos
    items = relationship("InventoryHistoryItem", back_populates="inventory")

class InventoryHistoryItem(Base):
    """Itens do histórico de inventário"""
    __tablename__ = "inventory_history_items"
    
    id = Column(Integer, primary_key=True, index=True)
    inventory_id = Column(Integer, ForeignKey("inventory_history.id"), nullable=False)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False)
    system_stock = Column(Float, nullable=False)  # Estoque no sistema
    physical_count = Column(Float, nullable=False)  # Contagem física
    difference = Column(Float, nullable=False)  # Diferença (físico - sistema)
    adjustment_made = Column(Boolean, default=False)  # Se foi feito ajuste
    
    # Relacionamentos
    inventory = relationship("InventoryHistory", back_populates="items")
    material = relationship("Material")

class Fueling(Base):
    """Modelo para registro de abastecimento de equipamentos"""
    __tablename__ = "fuelings"
    
    id = Column(Integer, primary_key=True, index=True)
    equipment_id = Column(Integer, ForeignKey("equipments.id"), nullable=False)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False)  # Tipo de combustível
    date = Column(DateTime, nullable=False, default=func.now())
    quantity = Column(Float, nullable=False)  # Quantidade abastecida
    horimeter = Column(Float, nullable=False)  # Horímetro no momento do abastecimento
    unit_cost = Column(Float)  # Custo unitário do combustível
    total_cost = Column(Float)  # Custo total do abastecimento
    operator = Column(String(100))  # Operador que registrou
    notes = Column(Text)  # Observações
    created_at = Column(DateTime, default=func.now())
    
    # Relacionamentos
    equipment = relationship("Equipment")
    material = relationship("Material")  # Combustível usado

class PurchaseOrder(Base):
    """Pedidos de Compra"""
    __tablename__ = "purchase_orders"
    
    id = Column(Integer, primary_key=True, index=True)
    number = Column(String(20), unique=True, index=True, nullable=False)  # Número único do pedido
    purchase_request_id = Column(Integer, ForeignKey("purchase_requests.id"), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    status = Column(String(20), default="Pendente")  # Pendente, Enviado, Confirmado, Entregue, Cancelado
    total_value = Column(Float, nullable=False)
    delivery_date = Column(DateTime)
    payment_terms = Column(String(200))
    notes = Column(Text)
    created_by = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=func.now())
    sent_at = Column(DateTime)  # Quando foi enviado ao fornecedor
    confirmed_at = Column(DateTime)  # Quando foi confirmado pelo fornecedor
    
    # Relacionamentos
    purchase_request = relationship("PurchaseRequest", back_populates="purchase_orders")
    supplier = relationship("Supplier")
    items = relationship("PurchaseOrderItem", back_populates="purchase_order")
    quotations = relationship("PurchaseOrderQuotation", back_populates="purchase_order")

    @property
    def supplier_name(self) -> Optional[str]:
        """Retorna o nome do fornecedor associado ao pedido (se disponível)."""
        try:
            return self.supplier.name if getattr(self, 'supplier', None) else None
        except Exception:
            return None

class PurchaseOrderItem(Base):
    """Itens do Pedido de Compra"""
    __tablename__ = "purchase_order_items"
    
    id = Column(Integer, primary_key=True, index=True)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    specifications = Column(Text)
    
    # Relacionamentos
    purchase_order = relationship("PurchaseOrder", back_populates="items")
    material = relationship("Material")

class PurchaseOrderQuotation(Base):
    """Cotações para Pedidos de Compra (3 fornecedores)"""
    __tablename__ = "purchase_order_quotations"
    
    id = Column(Integer, primary_key=True, index=True)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    supplier_name = Column(String(200), nullable=False)  # Nome do fornecedor
    contact_name = Column(String(100), nullable=False)   # Nome do contato
    contact_phone = Column(String(20), nullable=False)   # Telefone do contato
    total_value = Column(Float, nullable=False)          # Valor total cotado
    delivery_time = Column(Integer)                      # Prazo de entrega em dias
    payment_terms = Column(String(200))                  # Condições de pagamento
    attachment_path = Column(String(500))                # Caminho do anexo (orçamento)
    is_selected = Column(Boolean, default=False)         # Se foi o fornecedor selecionado
    notes = Column(Text)
    created_at = Column(DateTime, default=func.now())
    
    # Relacionamentos
    purchase_order = relationship("PurchaseOrder", back_populates="quotations")
    supplier = relationship("Supplier")
    items = relationship("PurchaseOrderQuotationItem", back_populates="quotation")

class PurchaseOrderQuotationItem(Base):
    """Itens das Cotações"""
    __tablename__ = "purchase_order_quotation_items"
    
    id = Column(Integer, primary_key=True, index=True)
    quotation_id = Column(Integer, ForeignKey("purchase_order_quotations.id"), nullable=False)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    
    # Relacionamentos
    quotation = relationship("PurchaseOrderQuotation", back_populates="items")
    material = relationship("Material")