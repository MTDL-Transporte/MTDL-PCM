"""
Router para módulo de Recursos Humanos (RH)
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from app.database import get_db
from app.models.hr import Employee, Shift, EmployeeSchedule, TimeClockLog
from app.schemas.hr import (
    EmployeeCreate, EmployeeUpdate, EmployeeResponse, NextMatriculaResponse,
    ShiftCreate, ShiftUpdate, ShiftResponse,
    EmployeeScheduleCreate, EmployeeScheduleUpdate, EmployeeScheduleResponse,
    TimeClockLogCreate, TimeClockLogResponse,
    PayrollCreate, PayrollResponse,
    ProjectAllocationCreate, ProjectAllocationResponse,
)
from app.templates_config import templates

router = APIRouter()

START_MATRICULA = 50000

@router.get("/hr/employees")
async def hr_employees_page(request: Request):
    """Página de cadastro de funcionários"""
    return templates.TemplateResponse("hr/employees.html", {"request": request})

@router.get("/hr/schedules")
async def hr_schedules_page(request: Request):
    """Página de escalas e jornadas"""
    return templates.TemplateResponse("hr/schedules.html", {"request": request})

@router.get("/hr/payroll")
async def hr_payroll_page(request: Request):
    """Página de folha de pagamento"""
    return templates.TemplateResponse("hr/payroll.html", {"request": request})

@router.get("/hr/time-tracking")
async def hr_time_tracking_page(request: Request):
    """Página de controle de ponto"""
    return templates.TemplateResponse("hr/time_tracking.html", {"request": request})

@router.get("/hr/allocations")
async def hr_allocations_page(request: Request):
    """Página de alocações por obra"""
    return templates.TemplateResponse("hr/allocations.html", {"request": request})

@router.get("/api/hr/employees", response_model=List[EmployeeResponse])
async def list_employees(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    query = db.query(Employee)
    if active_only:
        query = query.filter(Employee.is_active == True)
    employees = query.offset(skip).limit(limit).all()
    return employees

@router.get("/api/hr/employees/{employee_id}", response_model=EmployeeResponse)
async def get_employee(employee_id: int, db: Session = Depends(get_db)):
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Funcionário não encontrado")
    return emp

@router.get("/api/hr/employees/by-matricula/{matricula}", response_model=EmployeeResponse)
async def get_employee_by_matricula(matricula: int, db: Session = Depends(get_db)):
    emp = db.query(Employee).filter(Employee.matricula == matricula).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Funcionário não encontrado")
    return emp

@router.post("/api/hr/employees", response_model=EmployeeResponse)
async def create_employee(employee: EmployeeCreate, db: Session = Depends(get_db)):
    # Gerar matrícula automaticamente
    last = db.query(func.max(Employee.matricula)).scalar()
    next_matricula = (last + 1) if last and last >= START_MATRICULA else START_MATRICULA

    emp = Employee(
        matricula=next_matricula,
        name=employee.name,
        corporate_email=employee.corporate_email,
        personal_email=employee.personal_email,
        phone=employee.phone,
        emergency_contact_name=employee.emergency_contact_name,
        emergency_contact_phone=employee.emergency_contact_phone,
        emergency_contact_relation=employee.emergency_contact_relation,
        labor_type=employee.labor_type,
        sector=employee.sector,
        role=employee.role,
        initial_salary=employee.initial_salary,
        is_active=True
    )
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return emp

@router.put("/api/hr/employees/{employee_id}", response_model=EmployeeResponse)
async def update_employee(employee_id: int, employee_update: EmployeeUpdate, db: Session = Depends(get_db)):
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Funcionário não encontrado")

    # Atualizar campos dinamicamente
    for field, value in employee_update.dict(exclude_unset=True).items():
        setattr(emp, field, value)

    db.commit()
    db.refresh(emp)
    return emp

@router.delete("/api/hr/employees/{employee_id}")
async def delete_employee(employee_id: int, db: Session = Depends(get_db)):
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Funcionário não encontrado")
    db.delete(emp)
    db.commit()
    return {"success": True}

@router.get("/api/hr/next-matricula", response_model=NextMatriculaResponse)
async def get_next_matricula(db: Session = Depends(get_db)):
    last = db.query(func.max(Employee.matricula)).scalar()
    next_matricula = (last + 1) if last and last >= START_MATRICULA else START_MATRICULA
    return {"next_matricula": next_matricula}

@router.get("/api/hr/sectors")
async def get_sectors():
    return {
        "success": True,
        "data": [
            "MANUTENÇÃO",
            "ALMOXARIFADO",
            "RECURSOS HUMANOS",
            "COMERCIAL",
            "APROPRIAÇÃO DE OBRA"
        ]
    }

@router.get("/api/hr/labor-types")
async def get_labor_types():
    return {"success": True, "data": ["Direta", "Indireta"]}

# ---- Escala/Jornada ----
@router.get("/api/hr/shifts", response_model=List[ShiftResponse])
async def list_shifts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Shift).offset(skip).limit(limit).all()

@router.post("/api/hr/shifts", response_model=ShiftResponse)
async def create_shift(shift: ShiftCreate, db: Session = Depends(get_db)):
    s = Shift(name=shift.name, start_time=shift.start_time, end_time=shift.end_time, break_minutes=shift.break_minutes or 0)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s

@router.put("/api/hr/shifts/{shift_id}", response_model=ShiftResponse)
async def update_shift(shift_id: int, data: ShiftUpdate, db: Session = Depends(get_db)):
    s = db.query(Shift).filter(Shift.id == shift_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Turno/Escala não encontrado")
    for k, v in data.dict(exclude_unset=True).items():
        setattr(s, k, v)
    db.commit()
    db.refresh(s)
    return s

@router.delete("/api/hr/shifts/{shift_id}")
async def delete_shift(shift_id: int, db: Session = Depends(get_db)):
    s = db.query(Shift).filter(Shift.id == shift_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Turno/Escala não encontrado")
    db.delete(s)
    db.commit()
    return {"success": True}

@router.get("/api/hr/schedules", response_model=List[EmployeeScheduleResponse])
async def list_schedules(employee_id: Optional[int] = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    q = db.query(EmployeeSchedule)
    if employee_id:
        q = q.filter(EmployeeSchedule.employee_id == employee_id)
    return q.order_by(EmployeeSchedule.valid_from.desc()).offset(skip).limit(limit).all()

@router.post("/api/hr/schedules", response_model=EmployeeScheduleResponse)
async def create_schedule(data: EmployeeScheduleCreate, db: Session = Depends(get_db)):
    sch = EmployeeSchedule(
        employee_id=data.employee_id,
        shift_id=data.shift_id,
        valid_from=data.valid_from,
        valid_to=data.valid_to,
        weekly_hours=data.weekly_hours or 44.0,
    )
    db.add(sch)
    db.commit()
    db.refresh(sch)
    return sch

@router.put("/api/hr/schedules/{schedule_id}", response_model=EmployeeScheduleResponse)
async def update_schedule(schedule_id: int, data: EmployeeScheduleUpdate, db: Session = Depends(get_db)):
    sch = db.query(EmployeeSchedule).filter(EmployeeSchedule.id == schedule_id).first()
    if not sch:
        raise HTTPException(status_code=404, detail="Escala/Jornada não encontrada")
    for k, v in data.dict(exclude_unset=True).items():
        setattr(sch, k, v)
    db.commit()
    db.refresh(sch)
    return sch

@router.delete("/api/hr/schedules/{schedule_id}")
async def delete_schedule(schedule_id: int, db: Session = Depends(get_db)):
    sch = db.query(EmployeeSchedule).filter(EmployeeSchedule.id == schedule_id).first()
    if not sch:
        raise HTTPException(status_code=404, detail="Escala/Jornada não encontrada")
    db.delete(sch)
    db.commit()
    return {"success": True}

# ---- Controle de Ponto ----
@router.get("/api/hr/timeclock", response_model=List[TimeClockLogResponse])
async def list_timeclock(employee_id: Optional[int] = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    q = db.query(TimeClockLog)
    if employee_id:
        q = q.filter(TimeClockLog.employee_id == employee_id)
    return q.order_by(TimeClockLog.timestamp.desc()).offset(skip).limit(limit).all()

@router.post("/api/hr/timeclock", response_model=TimeClockLogResponse)
async def create_timeclock(entry: TimeClockLogCreate, db: Session = Depends(get_db)):
    ts = entry.timestamp or func.now()
    log = TimeClockLog(employee_id=entry.employee_id, timestamp=ts, action=entry.action, source=entry.source or 'web', note=entry.note)
    db.add(log)
    db.commit()
    db.refresh(log)
    return log

# ---- Folha de Pagamento ----
from app.models.hr import Payroll

@router.get("/api/hr/payrolls", response_model=List[PayrollResponse])
async def list_payrolls(employee_id: Optional[int] = None, period: Optional[str] = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    q = db.query(Payroll)
    if employee_id:
        q = q.filter(Payroll.employee_id == employee_id)
    if period:
        q = q.filter(Payroll.period == period)
    return q.order_by(Payroll.processed_at.desc()).offset(skip).limit(limit).all()

@router.post("/api/hr/payrolls", response_model=PayrollResponse)
async def create_payroll(data: PayrollCreate, db: Session = Depends(get_db)):
    emp = db.query(Employee).filter(Employee.id == data.employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Funcionário não encontrado")
    base_salary = data.base_salary if data.base_salary is not None else emp.initial_salary
    overtime_value = data.overtime_value if data.overtime_value is not None else 0.0
    if (data.overtime_hours or 0) > 0 and overtime_value == 0.0:
        hourly_rate = (base_salary or 0) / 220.0
        overtime_value = (data.overtime_hours or 0) * hourly_rate * 1.5
    deductions = data.deductions or 0.0
    net_pay = data.net_pay if data.net_pay is not None else (base_salary + overtime_value - deductions)

    pr = Payroll(
        employee_id=data.employee_id,
        period=data.period,
        base_salary=base_salary,
        overtime_hours=data.overtime_hours or 0.0,
        overtime_value=overtime_value,
        deductions=deductions,
        net_pay=net_pay,
    )
    db.add(pr)
    db.commit()
    db.refresh(pr)
    return pr

@router.delete("/api/hr/payrolls/{payroll_id}")
async def delete_payroll(payroll_id: int, db: Session = Depends(get_db)):
    pr = db.query(Payroll).filter(Payroll.id == payroll_id).first()
    if not pr:
        raise HTTPException(status_code=404, detail="Folha não encontrada")
    db.delete(pr)
    db.commit()
    return {"success": True}

# ---- Alocações por Obra ----
from app.models.hr import ProjectAllocation

@router.get("/api/hr/allocations", response_model=List[ProjectAllocationResponse])
async def list_allocations(employee_id: Optional[int] = None, project_code: Optional[str] = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    q = db.query(ProjectAllocation)
    if employee_id:
        q = q.filter(ProjectAllocation.employee_id == employee_id)
    if project_code:
        q = q.filter(ProjectAllocation.project_code == project_code)
    return q.order_by(ProjectAllocation.created_at.desc()).offset(skip).limit(limit).all()

@router.post("/api/hr/allocations", response_model=ProjectAllocationResponse)
async def create_allocation(data: ProjectAllocationCreate, db: Session = Depends(get_db)):
    emp = db.query(Employee).filter(Employee.id == data.employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Funcionário não encontrado")
    alloc = ProjectAllocation(
        employee_id=data.employee_id,
        project_code=data.project_code,
        start_date=data.start_date,
        end_date=data.end_date,
        allocation_percent=data.allocation_percent or 100.0,
    )
    db.add(alloc)
    db.commit()
    db.refresh(alloc)
    return alloc

@router.delete("/api/hr/allocations/{allocation_id}")
async def delete_allocation(allocation_id: int, db: Session = Depends(get_db)):
    alloc = db.query(ProjectAllocation).filter(ProjectAllocation.id == allocation_id).first()
    if not alloc:
        raise HTTPException(status_code=404, detail="Alocação não encontrada")
    db.delete(alloc)
    db.commit()
    return {"success": True}