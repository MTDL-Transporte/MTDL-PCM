"""
Modelos relacionados à manutenção
"""

from sqlalchemy import Column, Integer, String, DateTime, Float, Text, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class WorkOrder(Base):
    """Modelo para Ordens de Serviço"""
    __tablename__ = "work_orders"
    
    id = Column(Integer, primary_key=True, index=True)
    number = Column(String(20), unique=True, index=True, nullable=False)  # Inicia em 100000
    title = Column(String(200), nullable=False)
    description = Column(Text)
    priority = Column(String(20), default="Normal")  # Baixa, Normal, Alta, Crítica
    type = Column(String(20), nullable=False)  # Preventiva, Corretiva, Preditiva
    maintenance_cause = Column(String(50))  # Falha operacional, Desgaste natural
    status = Column(String(20), default="Aberta")  # Aberta, Em andamento, Fechada
    equipment_id = Column(Integer, ForeignKey("equipments.id"), nullable=False)
    technician_id = Column(Integer, ForeignKey("technicians.id"))  # Técnico responsável
    requested_by = Column(String(100))
    assigned_to = Column(String(100))
    estimated_hours = Column(Float)
    actual_hours = Column(Float)
    cost = Column(Float, default=0.0)
    created_at = Column(DateTime, default=func.now())
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    due_date = Column(DateTime)
    notes = Column(Text)
    
    # Relacionamentos
    equipment = relationship("Equipment", back_populates="work_orders")
    technician = relationship("Technician", back_populates="work_orders")
    # materials_used = relationship("WorkOrderMaterial", back_populates="work_order")  # TEMPORARIAMENTE DESABILITADO
    time_logs = relationship("TimeLog", back_populates="work_order")
    checklists = relationship("WorkOrderChecklist", back_populates="work_order")

class MaintenancePlan(Base):
    """Planos de manutenção preventiva"""
    __tablename__ = "maintenance_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    equipment_id = Column(Integer, ForeignKey("equipments.id"), nullable=False)
    type = Column(String(20), nullable=False)  # Preventiva, Preditiva
    interval_type = Column(String(20), nullable=False)  # Tempo, Horímetro, Quilometragem
    interval_value = Column(Integer, nullable=False)  # Dias, horas ou km
    description = Column(Text)
    checklist_template = Column(JSON)  # Template do checklist
    is_active = Column(Boolean, default=True)
    # last_execution_horimeter = Column(Float)  # TEMPORARIAMENTE REMOVIDO - SEM HORÍMETRO
    last_execution_date = Column(DateTime)
    # next_execution_horimeter = Column(Float)  # TEMPORARIAMENTE REMOVIDO - SEM HORÍMETRO
    next_execution_date = Column(DateTime)
    estimated_hours = Column(Float)  # Horas estimadas para execução
    priority = Column(String(20), default="Normal")  # Baixa, Normal, Alta, Crítica
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relacionamentos
    equipment = relationship("Equipment", back_populates="maintenance_plans")
    plan_materials = relationship("MaintenancePlanMaterial", back_populates="maintenance_plan")
    plan_actions = relationship("MaintenancePlanAction", back_populates="maintenance_plan")

class MaintenancePlanMaterial(Base):
    """Materiais necessários para um plano de manutenção"""
    __tablename__ = "maintenance_plan_materials"
    
    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("maintenance_plans.id"), nullable=False)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String(20), default="un")
    is_critical = Column(Boolean, default=False)  # Material crítico para a manutenção
    
    # Relacionamentos
    maintenance_plan = relationship("MaintenancePlan", back_populates="plan_materials")
    # material = relationship("Material", back_populates="maintenance_plan_materials")  # TEMPORARIAMENTE DESABILITADO

class MaintenancePlanAction(Base):
    """Ações/tarefas de um plano de manutenção"""
    __tablename__ = "maintenance_plan_actions"
    
    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("maintenance_plans.id"), nullable=False)
    description = Column(Text, nullable=False)
    action_type = Column(String(50), nullable=False)  # Inspeção, Troca, Ajuste, etc.
    sequence_order = Column(Integer, default=1)
    estimated_time_minutes = Column(Integer)  # Tempo estimado em minutos
    requires_specialist = Column(Boolean, default=False)
    safety_notes = Column(Text)
    
    # Relacionamentos
    maintenance_plan = relationship("MaintenancePlan", back_populates="plan_actions")

class MaintenanceAlert(Base):
    """Alertas de manutenção preventiva"""
    __tablename__ = "maintenance_alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    equipment_id = Column(Integer, ForeignKey("equipments.id"), nullable=False)
    maintenance_plan_id = Column(Integer, ForeignKey("maintenance_plans.id"), nullable=False)
    alert_type = Column(String(20), nullable=False)  # Previsto, Vencido, Crítico
    current_horimeter = Column(Float, nullable=False)
    target_horimeter = Column(Float, nullable=False)
    hours_remaining = Column(Float)  # Horas restantes (pode ser negativo se vencido)
    message = Column(Text)
    is_acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(String(100))
    acknowledged_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    
    # Relacionamentos
    equipment = relationship("Equipment")
    maintenance_plan = relationship("MaintenancePlan")

class WorkOrderMaterial(Base):
    """Materiais utilizados nas OS"""
    __tablename__ = "work_order_materials"
    
    id = Column(Integer, primary_key=True, index=True)
    work_order_id = Column(Integer, ForeignKey("work_orders.id"), nullable=False)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False)
    quantity_used = Column(Float, nullable=False)
    unit_cost = Column(Float)
    total_cost = Column(Float)
    
    # Relacionamentos
    # work_order = relationship("WorkOrder", back_populates="materials_used")  # TEMPORARIAMENTE DESABILITADO
    # material = relationship("Material", back_populates="work_order_materials")  # TEMPORARIAMENTE DESABILITADO

class TimeLog(Base):
    """Registro de horas trabalhadas"""
    __tablename__ = "time_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    work_order_id = Column(Integer, ForeignKey("work_orders.id"), nullable=False)
    technician = Column(String(100), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    hours_worked = Column(Float, nullable=False)
    activity_description = Column(Text)
    date = Column(DateTime, default=func.now())
    
    # Relacionamentos
    work_order = relationship("WorkOrder", back_populates="time_logs")

class WorkOrderChecklist(Base):
    """Checklist de ordem de serviço"""
    __tablename__ = "work_order_checklists"
    
    id = Column(Integer, primary_key=True, index=True)
    work_order_id = Column(Integer, ForeignKey("work_orders.id"), nullable=False)
    checklist_data = Column(JSON)  # Dados do checklist preenchido
    completed_by = Column(String(100))
    completed_at = Column(DateTime, default=func.now())
    
    # Relacionamentos
    work_order = relationship("WorkOrder", back_populates="checklists")

class Technician(Base):
    """Modelo para profissionais de manutenção"""
    __tablename__ = "technicians"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    function = Column(String(50), nullable=False)  # Ajudante, Mecânico, Eletricista, Técnico
    hourly_rate = Column(Float, nullable=False)  # Valor da hora de trabalho
    hr_matricula = Column(Integer)  # Matrícula do funcionário no RH (opcional)
    phone = Column(String(20))
    email = Column(String(100))
    specialties = Column(Text)  # Especialidades do técnico
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relacionamentos
    work_orders = relationship("WorkOrder", back_populates="technician")