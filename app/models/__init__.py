# Modelos do banco de dados

# Importar todos os modelos para garantir que os relacionamentos funcionem
from .equipment import Equipment, HorimeterLog
from .maintenance import WorkOrder, MaintenancePlan, MaintenancePlanMaterial, MaintenancePlanAction, MaintenanceAlert, WorkOrderMaterial, TimeLog, WorkOrderChecklist, Technician
from .warehouse import Material, Supplier, StockMovement, PurchaseRequest, PurchaseRequestItem, Fueling
from .hr import Employee
from .construction import MacroStage, SubStage, Task, TaskMeasurement

# Exportar todos os modelos
__all__ = [
    "Equipment", "HorimeterLog",
    "WorkOrder", "MaintenancePlan", "MaintenancePlanMaterial", "MaintenancePlanAction", 
    "MaintenanceAlert", "WorkOrderMaterial", "TimeLog", "WorkOrderChecklist", "Technician",
    "Material", "Supplier", "StockMovement", "PurchaseRequest", "PurchaseRequestItem", "Fueling",
    "Employee",
    "MacroStage", "SubStage", "Task", "TaskMeasurement"
]