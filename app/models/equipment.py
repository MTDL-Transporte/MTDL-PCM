"""
Modelos relacionados a equipamentos
"""

from sqlalchemy import Column, Integer, String, DateTime, Float, Text, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Equipment(Base):
    """Modelo para equipamentos"""
    __tablename__ = "equipments"
    
    id = Column(Integer, primary_key=True, index=True)
    prefix = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    model = Column(String(100))
    manufacturer = Column(String(100))
    year = Column(Integer)
    serial_number = Column(String(100))
    cost_center = Column(String(50))
    company_name = Column(String(10))
    # Dados de empresa/fornecedor (para frota terceirizada, por exemplo)
    cnpj = Column(String(18), nullable=True)
    company_legal_name = Column(String(200), nullable=True)
    status = Column(String(20), default="Operacional")
    mobilization_date = Column(DateTime, nullable=True)
    demobilization_date = Column(DateTime, nullable=True)
    initial_horimeter = Column(Float, nullable=True)  # Horímetro inicial
    current_horimeter = Column(Float, nullable=True)  # Horímetro atual
    equipment_class = Column(String(20), nullable=True)  # Classe do equipamento (linha amarela/branca)
    category = Column(String(100), nullable=True)  # Categoria do equipamento (tipo específico)
    fleet = Column(String(20), nullable=True)  # Frota: Propria/Terceirizada
    monthly_quota = Column(Float, nullable=True)  # Franquia mensal de uso (horas)
    last_horimeter_update = Column(DateTime, default=func.now())
    location = Column(String(100))
    description = Column(Text)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relacionamentos
    work_orders = relationship("WorkOrder", back_populates="equipment", lazy="dynamic")
    maintenance_plans = relationship("MaintenancePlan", back_populates="equipment")
    horimeter_logs = relationship("HorimeterLog", back_populates="equipment")
    technical_profile = relationship(
        "EquipmentTechnicalProfile",
        back_populates="equipment",
        uselist=False,
        cascade="all, delete, delete-orphan",
        passive_deletes=True,
    )

class HorimeterLog(Base):
    """Log de horímetro dos equipamentos"""
    __tablename__ = "horimeter_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    equipment_id = Column(Integer, ForeignKey("equipments.id"), nullable=False)
    previous_value = Column(Float, nullable=False)
    new_value = Column(Float, nullable=False)
    difference = Column(Float, nullable=False)
    recorded_by = Column(String(100))
    recorded_at = Column(DateTime, default=func.now())
    notes = Column(Text)
    
    # Relacionamentos
    equipment = relationship("Equipment", back_populates="horimeter_logs")

class WeeklyHours(Base):
    """Registro de horas semanais dos equipamentos"""
    __tablename__ = "weekly_hours"
    
    id = Column(Integer, primary_key=True, index=True)
    equipment_id = Column(Integer, ForeignKey("equipments.id"), nullable=False)
    week = Column(String(8), nullable=False)  # Formato: 2024-W01
    monday = Column(Float, default=0.0)
    tuesday = Column(Float, default=0.0)
    wednesday = Column(Float, default=0.0)
    thursday = Column(Float, default=0.0)
    friday = Column(Float, default=0.0)
    saturday = Column(Float, default=0.0)
    sunday = Column(Float, default=0.0)
    total_hours = Column(Float, default=0.0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relacionamentos
    equipment = relationship("Equipment")

class EquipmentTechnicalProfile(Base):
    """Perfil técnico gerado automaticamente para o equipamento"""
    __tablename__ = "equipment_technical_profiles"

    id = Column(Integer, primary_key=True, index=True)
    equipment_id = Column(Integer, ForeignKey("equipments.id", ondelete="CASCADE"), unique=True, nullable=False)
    profile_data = Column(JSON, nullable=False)  # Estrutura JSON do perfil técnico
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relacionamentos
    equipment = relationship("Equipment", back_populates="technical_profile")