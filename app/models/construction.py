"""
Modelos do módulo de Apropriação de Obra (Construção)
"""

from sqlalchemy import Column, Integer, String, Date, DateTime, Float, Text, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class MacroStage(Base):
    """Macroetapas da obra"""
    __tablename__ = "construction_macro_stages"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relacionamentos
    sub_stages = relationship("SubStage", back_populates="macro_stage", cascade="all, delete-orphan")

class SubStage(Base):
    """Subetapas dentro de cada macroetapa"""
    __tablename__ = "construction_sub_stages"

    id = Column(Integer, primary_key=True, index=True)
    macro_stage_id = Column(Integer, ForeignKey("construction_macro_stages.id"), nullable=False)
    name = Column(String(200), nullable=False)
    order = Column(Integer, default=0)
    contractual_value = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relacionamentos
    macro_stage = relationship("MacroStage", back_populates="sub_stages")
    tasks = relationship("Task", back_populates="sub_stage", cascade="all, delete-orphan")

class Task(Base):
    """Tarefas dentro de cada subetapa"""
    __tablename__ = "construction_tasks"

    id = Column(Integer, primary_key=True, index=True)
    sub_stage_id = Column(Integer, ForeignKey("construction_sub_stages.id"), nullable=False)

    # Campos principais
    name = Column(String(200), nullable=False)
    task_type = Column(String(50), nullable=False)  # Escavação, Compactação, Nivelamento
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    unit = Column(String(20), nullable=False)  # m³, m², m, unidade
    quantity_planned = Column(Float, nullable=False, default=0.0)
    notes = Column(Text)

    # Planejamento de recursos (listas de objetos)
    labor_plan = Column(JSON)        # [{"role":"Ajudante","quantity":2,"unit_value":250.0,"unit":"dia"}, ...]
    equipment_plan = Column(JSON)    # [{"type":"Escavadeira Hidráulica","quantity":1,"tariff":180.0,"hours":16}, ...]

    # Totais previstos (derivados; opcionalmente preenchidos para performance)
    total_labor_planned = Column(Float, default=0.0)
    total_equipment_planned = Column(Float, default=0.0)
    total_cost_planned = Column(Float, default=0.0)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relacionamentos
    sub_stage = relationship("SubStage", back_populates="tasks")
    measurements = relationship("TaskMeasurement", back_populates="task", cascade="all, delete-orphan")

class TaskMeasurement(Base):
    """Medições de execução da tarefa, incluindo recursos realizados"""
    __tablename__ = "construction_task_measurements"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("construction_tasks.id"), nullable=False)

    date = Column(Date, nullable=False)
    quantity_executed = Column(Float, nullable=False, default=0.0)
    notes = Column(Text)
    photo_path = Column(String(300))  # opcional

    # Recursos realizados (listas de objetos)
    labor_realized = Column(JSON)        # [{"role":"Ajudante","quantity":2,"unit_value":250.0,"time_unit":"dia","time_qty":1}, ...]
    equipment_used = Column(JSON)        # [{"equipment":"Escavadeira Hidráulica","hours":8,"tariff":180.0}, ...]

    # Totais realizados (derivados; opcionalmente preenchidos)
    total_labor_realized = Column(Float, default=0.0)
    total_equipment_realized = Column(Float, default=0.0)
    total_cost_realized = Column(Float, default=0.0)

    created_at = Column(DateTime, default=func.now())

    # Relacionamentos
    task = relationship("Task", back_populates="measurements")