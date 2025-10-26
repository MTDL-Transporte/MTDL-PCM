"""
Schemas para módulo de almoxarifado
"""

from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import datetime

class MaterialBase(BaseModel):
    name: str
    description: Optional[str] = None
    reference: Optional[str] = None  # Campo de referência para facilitar identificação
    category: Optional[str] = None
    unit: str  # UN, KG, L, M, etc.
    minimum_stock: float  # Obrigatório
    maximum_stock: float  # Obrigatório
    location: Optional[str] = None
    barcode: Optional[str] = None

class MaterialCreate(MaterialBase):
    @validator('minimum_stock')
    def validate_minimum_stock(cls, v):
        if v < 0:
            raise ValueError('Estoque mínimo deve ser maior ou igual a zero')
        return v
    
    @validator('maximum_stock')
    def validate_maximum_stock(cls, v, values):
        if v < 0:
            raise ValueError('Estoque máximo deve ser maior ou igual a zero')
        if 'minimum_stock' in values and v < values['minimum_stock']:
            raise ValueError('Estoque máximo deve ser maior que o estoque mínimo')
        return v
    
    @validator('unit')
    def validate_unit(cls, v):
        allowed = ['UN', 'KG', 'L', 'M', 'M²', 'M³', 'PC', 'CX', 'PCT']
        if v not in allowed:
            raise ValueError(f'Unidade deve ser uma das seguintes: {", ".join(allowed)}')
        return v

class MaterialUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    reference: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    minimum_stock: Optional[float] = None
    maximum_stock: Optional[float] = None
    unit_price: Optional[float] = None
    location: Optional[str] = None
    barcode: Optional[str] = None
    is_active: Optional[bool] = None
    
    @validator('minimum_stock')
    def validate_minimum_stock(cls, v):
        if v is not None and v < 0:
            raise ValueError('Estoque mínimo deve ser maior ou igual a zero')
        return v
    
    @validator('maximum_stock')
    def validate_maximum_stock(cls, v):
        if v is not None and v < 0:
            raise ValueError('Estoque máximo deve ser maior ou igual a zero')
        return v
    
    @validator('unit')
    def validate_unit(cls, v):
        if v is not None:
            allowed = ['UN', 'KG', 'L', 'M', 'M²', 'M³', 'PC', 'CX', 'PCT']
            if v not in allowed:
                raise ValueError(f'Unidade deve ser uma das seguintes: {", ".join(allowed)}')
        return v
    
    @validator('unit_price')
    def validate_unit_price(cls, v):
        if v is not None and v < 0:
            raise ValueError('Preço unitário deve ser maior ou igual a zero')
        return v

class MaterialResponse(MaterialBase):
    id: int
    code: str  # Código gerado automaticamente
    current_stock: float
    average_consumption: float  # Consumo médio calculado automaticamente
    average_cost: float
    unit_price: float
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True
        from_attributes = True

class StockMovementBase(BaseModel):
    material_id: int
    type: str  # Entrada, Saída, Ajuste
    quantity: float
    unit_cost: Optional[float] = None
    reference_document: Optional[str] = None
    reason: Optional[str] = None
    performed_by: Optional[str] = None
    notes: Optional[str] = None
    cost_center: Optional[str] = None
    equipment_id: Optional[int] = None
    application: Optional[str] = None

class StockMovementCreate(StockMovementBase):
    @validator('type')
    def validate_type(cls, v):
        allowed = ['Entrada', 'Saída', 'Ajuste']
        if v not in allowed:
            raise ValueError(f'Tipo deve ser um dos seguintes: {", ".join(allowed)}')
        return v
    
    @validator('quantity')
    def validate_quantity(cls, v):
        if v == 0:
            raise ValueError('Quantidade não pode ser zero')
        return v

class StockMovementResponse(StockMovementBase):
    id: int
    total_cost: Optional[float] = None
    previous_stock: float
    new_stock: float
    date: datetime
    cost_center: Optional[str] = None
    equipment_id: Optional[int] = None
    application: Optional[str] = None
    
    class Config:
        orm_mode = True
        from_attributes = True

class SupplierBase(BaseModel):
    name: str
    cnpj: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    rating: Optional[float] = None

class SupplierCreate(SupplierBase):
    @validator('rating')
    def validate_rating(cls, v):
        if v is not None and (v < 0 or v > 5):
            raise ValueError('Avaliação deve estar entre 0 e 5')
        return v

class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    cnpj: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    rating: Optional[float] = None
    is_active: Optional[bool] = None
    
    @validator('rating')
    def validate_rating(cls, v):
        if v is not None and (v < 0 or v > 5):
            raise ValueError('Avaliação deve estar entre 0 e 5')
        return v

class SupplierResponse(SupplierBase):
    id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        orm_mode = True
        from_attributes = True

class PurchaseRequestBase(BaseModel):
    requester: str
    department: Optional[str] = None
    justification: Optional[str] = None
    priority: str = "Normal"
    supplier_id: Optional[int] = None
    cost_center: Optional[str] = None
    stock_justification: Optional[str] = None

class PurchaseRequestCreate(PurchaseRequestBase):
    @validator('priority')
    def validate_priority(cls, v):
        allowed = ['Baixa', 'Normal', 'Alta', 'Urgente']
        if v not in allowed:
            raise ValueError(f'Prioridade deve ser uma das seguintes: {", ".join(allowed)}')
        return v

class PurchaseRequestUpdate(BaseModel):
    requester: Optional[str] = None
    department: Optional[str] = None
    justification: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    supplier_id: Optional[int] = None
    approved_by: Optional[str] = None
    cost_center: Optional[str] = None
    stock_justification: Optional[str] = None
    
    @validator('priority')
    def validate_priority(cls, v):
        if v is not None:
            allowed = ['Baixa', 'Normal', 'Alta', 'Urgente']
            if v not in allowed:
                raise ValueError(f'Prioridade deve ser uma das seguintes: {", ".join(allowed)}')
        return v
    
    @validator('status')
    def validate_status(cls, v):
        if v is not None:
            allowed = ['Pendente', 'Aprovada', 'Rejeitada', 'Comprada']
            if v not in allowed:
                raise ValueError(f'Status deve ser um dos seguintes: {", ".join(allowed)}')
        return v

class PurchaseRequestResponse(PurchaseRequestBase):
    id: int
    number: str
    status: str
    total_value: Optional[float] = 0.0
    requested_date: Optional[datetime] = None
    approved_date: Optional[datetime] = None
    approved_by: Optional[str] = None
    
    class Config:
        orm_mode = True
        from_attributes = True

class PurchaseRequestItemBase(BaseModel):
    material_id: int
    quantity: float
    unit_price: Optional[float] = None
    specifications: Optional[str] = None

class PurchaseRequestItemCreate(PurchaseRequestItemBase):
    @validator('quantity')
    def validate_quantity(cls, v):
        if v <= 0:
            raise ValueError('Quantidade deve ser maior que zero')
        return v

class PurchaseRequestItemResponse(PurchaseRequestItemBase):
    id: int
    purchase_request_id: int
    total_price: Optional[float] = None
    
    class Config:
        orm_mode = True
        from_attributes = True

# Purchase Order Schemas
class PurchaseOrderBase(BaseModel):
    purchase_request_id: int
    supplier_id: int
    total_value: float
    delivery_date: Optional[datetime] = None
    payment_terms: Optional[str] = None
    notes: Optional[str] = None

class PurchaseOrderCreate(PurchaseOrderBase):
    @validator('total_value')
    def validate_total_value(cls, v):
        if v <= 0:
            raise ValueError('Valor total deve ser maior que zero')
        return v

class PurchaseOrderUpdate(BaseModel):
    supplier_id: Optional[int] = None
    total_value: Optional[float] = None
    delivery_date: Optional[datetime] = None
    payment_terms: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None

class PurchaseOrderResponse(PurchaseOrderBase):
    id: int
    number: str
    status: str
    created_at: datetime
    supplier_name: Optional[str] = None
    
    class Config:
        orm_mode = True
        from_attributes = True

# Purchase Order Quotation Schemas
class PurchaseOrderQuotationBase(BaseModel):
    supplier_id: int
    supplier_name: str
    contact_name: str
    contact_phone: str
    total_value: float
    delivery_time: Optional[int] = None
    payment_terms: Optional[str] = None
    attachment_path: Optional[str] = None
    notes: Optional[str] = None
    is_selected: bool = False

class PurchaseOrderQuotationCreate(BaseModel):
    supplier_id: int
    supplier_name: str
    contact_name: str
    contact_phone: str
    total_value: float
    delivery_time: Optional[int] = None
    payment_terms: Optional[str] = None
    notes: Optional[str] = None
    
    @validator('total_value')
    def validate_total_value(cls, v):
        if v <= 0:
            raise ValueError('Valor total deve ser maior que zero')
        return v

class PurchaseOrderQuotationResponse(PurchaseOrderQuotationBase):
    id: int
    created_at: datetime
    
    class Config:
        orm_mode = True
        from_attributes = True