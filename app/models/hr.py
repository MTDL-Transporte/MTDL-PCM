"""
Modelos do módulo de Recursos Humanos (RH)
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.sql import func
from app.database import Base

class Employee(Base):
    """Modelo para cadastro de funcionário"""
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    # Matrícula única, iniciando em 50000 e incrementando +1 por colaborador
    matricula = Column(Integer, unique=True, index=True, nullable=False)

    # Informações pessoais
    name = Column(String(200), nullable=False)
    corporate_email = Column(String(200))
    personal_email = Column(String(200))
    phone = Column(String(50))

    # Contato de emergência
    emergency_contact_name = Column(String(200))
    emergency_contact_phone = Column(String(50))
    emergency_contact_relation = Column(String(100))

    # Classificação e setor
    labor_type = Column(String(20), nullable=False)  # Direta | Indireta
    sector = Column(String(100), nullable=False)     # Manutenção, Suprimentos, Qualidade, Engenharia, Segurança do Trabalho, Administrativo

    # Informações profissionais
    role = Column(String(100), nullable=False)       # Função/Cargo
    initial_salary = Column(Float, nullable=False)

    # Controle
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class Shift(Base):
    __tablename__ = "hr_shifts"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    start_time = Column(String(5), nullable=False)  # HH:MM
    end_time = Column(String(5), nullable=False)    # HH:MM
    break_minutes = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())

# Associação de funcionário à escala/turno
class EmployeeSchedule(Base):
    __tablename__ = "hr_employee_schedules"
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, nullable=False)
    shift_id = Column(Integer, nullable=False)
    valid_from = Column(DateTime, nullable=False)
    valid_to = Column(DateTime)
    weekly_hours = Column(Float, default=44.0)
    created_at = Column(DateTime, default=func.now())

# Controle de ponto
class TimeClockLog(Base):
    __tablename__ = "hr_timeclock_logs"
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=func.now())
    action = Column(String(10), nullable=False)  # in | out
    source = Column(String(20), default="web")
    note = Column(String(200))

# Folha de pagamento
class Payroll(Base):
    __tablename__ = "hr_payrolls"
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, nullable=False)
    period = Column(String(7), nullable=False)  # YYYY-MM
    base_salary = Column(Float, nullable=False)
    overtime_hours = Column(Float, default=0.0)
    overtime_value = Column(Float, default=0.0)
    deductions = Column(Float, default=0.0)
    net_pay = Column(Float, default=0.0)
    processed_at = Column(DateTime, default=func.now())

# Alocações por obra
class ProjectAllocation(Base):
    __tablename__ = "hr_project_allocations"
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, nullable=False)
    project_code = Column(String(100), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime)
    allocation_percent = Column(Float, default=100.0)
    created_at = Column(DateTime, default=func.now())