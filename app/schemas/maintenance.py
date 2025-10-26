"""
Schemas para módulo de manutenção
"""

from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import datetime

class WorkOrderBase(BaseModel):
    title: str
    description: Optional[str] = None
    priority: str = "Normal"
    type: str
    maintenance_cause: Optional[str] = None
    equipment_id: int
    technician_id: Optional[int] = None
    requested_by: Optional[str] = None
    assigned_to: Optional[str] = None
    estimated_hours: Optional[float] = None
    due_date: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None

class WorkOrderCreate(WorkOrderBase):
    horimeter: Optional[float] = None
    @validator('priority')
    def validate_priority(cls, v):
        allowed = ['Baixa', 'Normal', 'Alta', 'Crítica']
        if v not in allowed:
            raise ValueError(f'Priority must be one of {allowed}')
        return v
    
    @validator('type')
    def validate_type(cls, v):
        allowed = ['Preventiva', 'Corretiva', 'Preditiva']
        if v not in allowed:
            raise ValueError(f'Type must be one of {allowed}')
        return v
    
    @validator('maintenance_cause')
    def validate_maintenance_cause(cls, v):
        if v is not None:
            allowed = ['Falha operacional', 'Desgaste natural', 'Ambas']
            if v not in allowed:
                raise ValueError(f'Maintenance cause must be one of {allowed}')
        return v

class WorkOrderUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    maintenance_cause: Optional[str] = None
    technician_id: Optional[int] = None
    assigned_to: Optional[str] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    cost: Optional[float] = None
    due_date: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None
    
    @validator('status')
    def validate_status(cls, v):
        if v is not None:
            allowed = ['Aberta', 'Em andamento', 'Fechada']
            if v not in allowed:
                raise ValueError(f'Status must be one of {allowed}')
        return v

class WorkOrderResponse(WorkOrderBase):
    id: int
    number: str
    status: str
    cost: float
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    actual_hours: Optional[float] = None
    
    class Config:
        from_attributes = True

class TimeLogBase(BaseModel):
    technician: str
    start_time: str
    end_time: str
    activity_description: Optional[str] = None

class TimeLogCreate(TimeLogBase):
    pass

class TimeLogResponse(TimeLogBase):
    id: int
    work_order_id: int
    hours_worked: float
    date: datetime
    
    class Config:
        from_attributes = True

class EquipmentBase(BaseModel):
    prefix: str
    name: str
    model: Optional[str] = None
    manufacturer: Optional[str] = None
    year: Optional[int] = None
    serial_number: Optional[str] = None
    cost_center: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None

class EquipmentCreate(EquipmentBase):
    pass

class EquipmentUpdate(BaseModel):
    name: Optional[str] = None
    model: Optional[str] = None
    manufacturer: Optional[str] = None
    year: Optional[int] = None
    serial_number: Optional[str] = None
    cost_center: Optional[str] = None
    status: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    
    @validator('status')
    def validate_status(cls, v):
        if v is not None:
            allowed = ['Operacional', 'Manutenção', 'Inativo']
            if v not in allowed:
                raise ValueError(f'Status must be one of {allowed}')
        return v

class EquipmentResponse(EquipmentBase):
    id: int
    status: str
    horimeter: float
    last_horimeter_update: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True

class MaintenancePlanBase(BaseModel):
    name: str
    equipment_id: int
    type: str
    interval_type: str
    interval_value: int
    description: Optional[str] = None

class MaintenancePlanCreate(MaintenancePlanBase):
    @validator('type')
    def validate_type(cls, v):
        allowed = ['Preventiva', 'Preditiva']
        if v not in allowed:
            raise ValueError(f'Type must be one of {allowed}')
        return v
    
    @validator('interval_type')
    def validate_interval_type(cls, v):
        allowed = ['Tempo', 'Horímetro']
        if v not in allowed:
            raise ValueError(f'Interval type must be one of {allowed}')
        return v

class MaintenancePlanResponse(MaintenancePlanBase):
    id: int
    is_active: bool
    last_execution: Optional[datetime] = None
    next_execution: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class TechnicianBase(BaseModel):
    name: str
    function: str
    hourly_rate: float
    hr_matricula: Optional[int] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    specialties: Optional[str] = None

class TechnicianCreate(TechnicianBase):
    @validator('function')
    def validate_function(cls, v):
        allowed = ['Ajudante de manutenção', 'Mecânico', 'Eletricista', 'Técnico']
        if v not in allowed:
            raise ValueError(f'Function must be one of {allowed}')
        return v
    
    @validator('hourly_rate')
    def validate_hourly_rate(cls, v):
        if v <= 0:
            raise ValueError('Hourly rate must be greater than 0')
        return v

class TechnicianUpdate(BaseModel):
    name: Optional[str] = None
    function: Optional[str] = None
    hourly_rate: Optional[float] = None
    hr_matricula: Optional[int] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    specialties: Optional[str] = None
    is_active: Optional[bool] = None
    
    @validator('function')
    def validate_function(cls, v):
        if v is not None:
            allowed = ['Ajudante de manutenção', 'Mecânico', 'Eletricista', 'Técnico']
            if v not in allowed:
                raise ValueError(f'Function must be one of {allowed}')
        return v
    
    @validator('hourly_rate')
    def validate_hourly_rate(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Hourly rate must be greater than 0')
        return v

class TechnicianResponse(TechnicianBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True