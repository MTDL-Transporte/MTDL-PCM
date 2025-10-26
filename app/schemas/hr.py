"""
Schemas Pydantic para módulo de Recursos Humanos (RH)
"""

from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime, date

ALLOWED_SECTORS = [
    "Manutenção",
    "Suprimentos",
    "Qualidade",
    "Engenharia",
    "Segurança do Trabalho",
    "Administrativo",
]

ALLOWED_LABOR_TYPES = ["Direta", "Indireta"]

class EmployeeBase(BaseModel):
    name: str
    corporate_email: Optional[str] = None
    personal_email: Optional[str] = None
    phone: Optional[str] = None

    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relation: Optional[str] = None

    labor_type: str
    sector: str

    role: str
    initial_salary: float

    @validator('labor_type')
    def validate_labor_type(cls, v):
        if v not in ALLOWED_LABOR_TYPES:
            raise ValueError(f"labor_type must be one of {ALLOWED_LABOR_TYPES}")
        return v

    @validator('sector')
    def validate_sector(cls, v):
        if v not in ALLOWED_SECTORS:
            raise ValueError(f"sector must be one of {ALLOWED_SECTORS}")
        return v

    @validator('initial_salary')
    def validate_initial_salary(cls, v):
        if v <= 0:
            raise ValueError('initial_salary must be greater than 0')
        return v

class EmployeeCreate(EmployeeBase):
    pass

class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    corporate_email: Optional[str] = None
    personal_email: Optional[str] = None
    phone: Optional[str] = None

    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relation: Optional[str] = None

    labor_type: Optional[str] = None
    sector: Optional[str] = None

    role: Optional[str] = None
    initial_salary: Optional[float] = None
    is_active: Optional[bool] = None

    @validator('labor_type')
    def validate_labor_type(cls, v):
        if v is not None and v not in ALLOWED_LABOR_TYPES:
            raise ValueError(f"labor_type must be one of {ALLOWED_LABOR_TYPES}")
        return v

    @validator('sector')
    def validate_sector(cls, v):
        if v is not None and v not in ALLOWED_SECTORS:
            raise ValueError(f"sector must be one of {ALLOWED_SECTORS}")
        return v

    @validator('initial_salary')
    def validate_initial_salary(cls, v):
        if v is not None and v <= 0:
            raise ValueError('initial_salary must be greater than 0')
        return v

class EmployeeResponse(EmployeeBase):
    id: int
    matricula: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class NextMatriculaResponse(BaseModel):
    next_matricula: int

# ---- Escala/Jornada ----
class ShiftBase(BaseModel):
    name: str
    start_time: str  # HH:MM
    end_time: str    # HH:MM
    break_minutes: Optional[int] = 0

    @validator('start_time', 'end_time')
    def validate_time(cls, v):
        if not isinstance(v, str) or len(v) != 5 or v[2] != ':':
            raise ValueError('time must be in HH:MM')
        return v

class ShiftCreate(ShiftBase):
    pass

class ShiftUpdate(BaseModel):
    name: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    break_minutes: Optional[int] = None

class ShiftResponse(ShiftBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

class EmployeeScheduleBase(BaseModel):
    employee_id: int
    shift_id: int
    valid_from: datetime
    valid_to: Optional[datetime] = None
    weekly_hours: Optional[float] = 44.0

class EmployeeScheduleCreate(EmployeeScheduleBase):
    pass

class EmployeeScheduleUpdate(BaseModel):
    shift_id: Optional[int] = None
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    weekly_hours: Optional[float] = None

class EmployeeScheduleResponse(EmployeeScheduleBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

# ---- Controle de Ponto ----
class TimeClockLogBase(BaseModel):
    employee_id: int
    timestamp: Optional[datetime] = None
    action: str  # in | out
    source: Optional[str] = 'web'
    note: Optional[str] = None

    @validator('action')
    def validate_action(cls, v):
        if v not in ['in', 'out']:
            raise ValueError("action must be 'in' or 'out'")
        return v

class TimeClockLogCreate(TimeClockLogBase):
    pass

class TimeClockLogResponse(TimeClockLogBase):
    id: int
    timestamp: datetime
    class Config:
        from_attributes = True

# ---- Folha de Pagamento ----
class PayrollBase(BaseModel):
    employee_id: int
    period: str  # YYYY-MM
    base_salary: Optional[float] = None
    overtime_hours: Optional[float] = 0.0
    overtime_value: Optional[float] = 0.0
    deductions: Optional[float] = 0.0
    net_pay: Optional[float] = None

class PayrollCreate(PayrollBase):
    pass

class PayrollResponse(PayrollBase):
    id: int
    processed_at: datetime
    class Config:
        from_attributes = True

# ---- Alocações por Obra ----
class ProjectAllocationBase(BaseModel):
    employee_id: int
    project_code: str
    start_date: datetime
    end_date: Optional[datetime] = None
    allocation_percent: Optional[float] = 100.0

class ProjectAllocationCreate(ProjectAllocationBase):
    pass

class ProjectAllocationResponse(ProjectAllocationBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True