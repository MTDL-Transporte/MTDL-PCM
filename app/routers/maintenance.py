"""
Router para módulo de manutenção
"""

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Body, Form
import httpx
from fastapi.responses import Response, FileResponse
from sqlalchemy.orm import Session, joinedload, load_only
from sqlalchemy import and_, or_, func
from typing import List, Optional
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import io
import os
import json
import shutil
from app.database import get_db
from app.models.maintenance import WorkOrder, MaintenancePlan, TimeLog, Technician, MaintenancePlanAction, MaintenancePlanMaterial
from sqlalchemy import and_, or_
from app.models.equipment import Equipment, WeeklyHours, HorimeterLog, EquipmentTechnicalProfile
from app.models.warehouse import Fueling, StockNotification, StockNotificationItem, Material
from app.schemas.maintenance import WorkOrderCreate, WorkOrderUpdate, TimeLogCreate, TechnicianCreate, TechnicianUpdate, TechnicianResponse
from app.templates_config import templates
from starlette.responses import RedirectResponse
from app.routers.admin import get_user_from_request_token, get_user_modules

router = APIRouter()

# Acesso: autenticação e licença do módulo Manutenção

def ensure_maintenance_access(request: Request, db: Session):
    user = get_user_from_request_token(request, db)
    if not user:
        return None, RedirectResponse(url="/admin/login", status_code=302)
    # Admin tem acesso irrestrito
    if getattr(user, "is_admin", False):
        return user, None
    modules = get_user_modules(user.id, db)
    if "maintenance" in modules:
        return user, None
    raise HTTPException(status_code=403, detail="Acesso restrito ao módulo Manutenção")

# Páginas HTML
@router.get("/work-orders")
async def work_orders_page(request: Request, db: Session = Depends(get_db)):
    """Página de ordens de serviço"""
    user, redirect = ensure_maintenance_access(request, db)
    if redirect:
        return redirect
    return templates.TemplateResponse("maintenance/work_orders.html", {"request": request})

@router.get("/equipment")
async def equipment(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Página de equipamentos ou API"""
    # Verificar se é uma requisição para HTML ou JSON
    accept_header = request.headers.get("accept", "")
    
    if "text/html" in accept_header:
        user, redirect = ensure_maintenance_access(request, db)
        if redirect:
            return redirect
        return templates.TemplateResponse("maintenance/equipment.html", {"request": request})
    else:
        # Retornar dados JSON (API)
        try:
            equipment = db.query(Equipment).options(load_only(
                Equipment.id, Equipment.prefix, Equipment.name, Equipment.model, Equipment.manufacturer, Equipment.year,
                Equipment.serial_number, Equipment.status, Equipment.location, Equipment.cost_center, Equipment.description,
                Equipment.mobilization_date, Equipment.initial_horimeter, Equipment.current_horimeter, Equipment.equipment_class, Equipment.monthly_quota,
                Equipment.created_at
            )).all()
            return equipment
        except Exception as e:
            return {"error": str(e), "equipment": []}

@router.get("/equipment/list")
async def equipment_list(db: Session = Depends(get_db)):
    """API para listar equipamentos"""
    equipment = db.query(Equipment).options(load_only(
        Equipment.id, Equipment.prefix, Equipment.name, Equipment.model, Equipment.manufacturer, Equipment.year,
        Equipment.serial_number, Equipment.status, Equipment.location, Equipment.cost_center, Equipment.description,
        Equipment.mobilization_date, Equipment.initial_horimeter, Equipment.current_horimeter, Equipment.equipment_class, Equipment.monthly_quota,
        Equipment.created_at
    )).all()
    return [{
        "id": eq.id,
        "prefix": eq.prefix,
        "name": eq.name,
        "model": eq.model,
        "manufacturer": eq.manufacturer,
        "year": eq.year,
        "serial_number": eq.serial_number,
        "status": eq.status,
        "location": eq.location,
        "cost_center": eq.cost_center,
        "description": eq.description,
        "mobilization_date": eq.mobilization_date.isoformat() if eq.mobilization_date else None,
        "initial_horimeter": float(eq.initial_horimeter) if eq.initial_horimeter else None,
        "current_horimeter": float(eq.current_horimeter) if eq.current_horimeter else None,
        "equipment_class": eq.equipment_class,
        "category": eq.__dict__.get("category", None),
        "monthly_quota": float(eq.__dict__.get("monthly_quota")) if eq.__dict__.get("monthly_quota") is not None else None,
        "created_at": eq.created_at.isoformat() if eq.created_at else None
    } for eq in equipment]

@router.get("/list")
async def equipment_list_simple(db: Session = Depends(get_db)):
    """API para listar equipamentos (para uso com prefixo /equipment)"""
    equipment = db.query(Equipment).all()
    return [{"id": eq.id, "name": eq.name, "status": eq.status, "category": eq.__dict__.get("category", None)} for eq in equipment]

@router.get("/plans")
async def maintenance_plans(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    equipment_id: Optional[int] = None,
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """Página de planos de manutenção ou API"""
    # Verificar se é uma requisição para HTML ou JSON
    accept_header = request.headers.get("accept", "")
    
    if "text/html" in accept_header:
        user, redirect = ensure_maintenance_access(request, db)
        if redirect:
            return redirect
        return templates.TemplateResponse("maintenance/plans.html", {"request": request})
    else:
        # Retornar dados JSON (API)
        query = db.query(MaintenancePlan)
        
        if active_only:
            query = query.filter(MaintenancePlan.is_active == True)
        if equipment_id:
            query = query.filter(MaintenancePlan.equipment_id == equipment_id)
        
        plans = query.offset(skip).limit(limit).all()
        result = []
        
        for plan in plans:
            # Obter equipamento relacionado
            equipment = db.query(Equipment).filter(Equipment.id == plan.equipment_id).first()
            equipment_name = equipment.name if equipment else "N/A"
            equipment_prefix = equipment.prefix if equipment else "N/A"
            
            plan_data = {
                "id": plan.id,
                "name": plan.name,
                "type": plan.type,
                "interval_type": plan.interval_type,
                "interval_value": plan.interval_value,
                "equipment_id": plan.equipment_id,
                "equipment_name": equipment_name,
                "equipment_prefix": equipment_prefix,
                "priority": plan.priority,
                "estimated_hours": plan.estimated_hours,
                "is_active": plan.is_active,
                "description": plan.description,
                "next_execution": None,  # Pode ser implementado depois
                "created_at": plan.created_at.isoformat() if plan.created_at else None
            }
            result.append(plan_data)
        
        return result

@router.get("/schedules")
async def maintenance_schedules(request: Request, db: Session = Depends(get_db)):
    """Página de cronogramas de manutenção"""
    # Verificar se é uma requisição para HTML ou JSON
    accept_header = request.headers.get("accept", "")
    
    if "text/html" in accept_header:
        user, redirect = ensure_maintenance_access(request, db)
        if redirect:
            return redirect
        return templates.TemplateResponse("maintenance/schedules.html", {"request": request})
    else:
        # Retornar dados JSON (API)
        plans = db.query(MaintenancePlan).filter(MaintenancePlan.is_active == True).all()
        return [{"id": p.id, "name": p.name, "interval_type": p.interval_type, "interval_value": p.interval_value, "equipment_id": p.equipment_id} for p in plans]

@router.get("/schedules/list")
async def schedules_list(db: Session = Depends(get_db)):
    """API para lista de cronogramas com informações detalhadas"""
    plans = db.query(MaintenancePlan).filter(MaintenancePlan.is_active == True).all()
    
    result = []
    for plan in plans:
        # Buscar informações do equipamento
        equipment = db.query(Equipment).filter(Equipment.id == plan.equipment_id).first()
        
        # Calcular próxima execução (simplificado)
        next_execution = None
        from datetime import timedelta
        if plan.last_execution_date:
            if plan.interval_type == "days":
                next_execution = plan.last_execution_date + timedelta(days=plan.interval_value)
            elif plan.interval_type == "weeks":
                next_execution = plan.last_execution_date + timedelta(weeks=plan.interval_value)
            elif plan.interval_type == "months":
                # Aproximação para meses
                next_execution = plan.last_execution_date + timedelta(days=plan.interval_value * 30)
        elif plan.next_execution_date:
            next_execution = plan.next_execution_date
        
        result.append({
            "id": plan.id,
            "name": plan.name,
            "type": plan.type,
            "interval_type": plan.interval_type,
            "interval_value": plan.interval_value,
            "equipment_id": plan.equipment_id,
            "equipment_name": equipment.name if equipment else "N/A",
            "description": plan.description,
            "is_active": plan.is_active,
            "last_execution": plan.last_execution_date.isoformat() if plan.last_execution_date else None,
            "next_execution": next_execution.isoformat() if next_execution else None,
            "created_at": plan.created_at.isoformat() if plan.created_at else None
        })
    
    return result

@router.get("/history")
async def maintenance_history(request: Request, db: Session = Depends(get_db)):
    """Página de histórico de manutenção"""
    # Verificar se é uma requisição para HTML ou JSON
    accept_header = request.headers.get("accept", "")
    
    if "text/html" in accept_header:
        user, redirect = ensure_maintenance_access(request, db)
        if redirect:
            return redirect
        return templates.TemplateResponse("maintenance/history.html", {"request": request})
    else:
        # Retornar dados JSON (API)
        work_orders = db.query(WorkOrder).filter(WorkOrder.status == "Fechada").all()
        return [{"id": wo.id, "title": wo.title, "completed_at": wo.completed_at, "equipment_id": wo.equipment_id} for wo in work_orders]

@router.get("/history/list")
async def history_list(db: Session = Depends(get_db)):
    """API para lista de histórico com informações detalhadas"""
    work_orders = db.query(WorkOrder).filter(WorkOrder.status == "Fechada").all()
    
    result = []
    for wo in work_orders:
        # Buscar informações do equipamento
        equipment = db.query(Equipment).filter(Equipment.id == wo.equipment_id).first()
        
        result.append({
            "id": wo.id,
            "title": wo.title,
            "description": wo.description,
            "type": wo.type,
            "priority": wo.priority,
            "status": wo.status,
            "equipment_id": wo.equipment_id,
            "equipment_name": equipment.name if equipment else "N/A",
            "equipment_model": equipment.model if equipment else "N/A",
            "requested_by": wo.requested_by,
            "assigned_to": wo.assigned_to,
            "estimated_hours": wo.estimated_hours,
            "actual_hours": wo.actual_hours,
            "cost": float(wo.cost) if wo.cost else 0.0,
            "created_at": wo.created_at.isoformat() if wo.created_at else None,
            "started_at": wo.started_at.isoformat() if wo.started_at else None,
            "completed_at": wo.completed_at.isoformat() if wo.completed_at else None,
            "due_date": wo.due_date.isoformat() if wo.due_date else None,
            "notes": wo.notes
        })
    
    return result

# API Endpoints - Work Orders
@router.get("/api/work-orders")
async def get_work_orders(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    equipment_id: Optional[int] = None,
    technician_id: Optional[int] = None,
    opened_date: Optional[str] = None,
    number: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Listar ordens de serviço com filtros opcionais"""
    from app.models.equipment import Equipment
    from datetime import datetime
    from sqlalchemy import and_
    
    query = db.query(WorkOrder).join(Equipment)
    
    if status:
        query = query.filter(WorkOrder.status == status)
    if equipment_id:
        query = query.filter(WorkOrder.equipment_id == equipment_id)
    if technician_id:
        query = query.filter(WorkOrder.technician_id == technician_id)
    if number:
        query = query.filter(WorkOrder.number == str(number))
    if opened_date:
        # Aceitar formato YYYY-MM-DD; filtrar por intervalo do dia
        try:
            try:
                base_dt = datetime.fromisoformat(opened_date)
            except ValueError:
                base_dt = datetime.strptime(opened_date, "%Y-%m-%d")
            start_dt = datetime(base_dt.year, base_dt.month, base_dt.day, 0, 0, 0)
            end_dt = datetime(base_dt.year, base_dt.month, base_dt.day, 23, 59, 59)
            query = query.filter(and_(WorkOrder.created_at >= start_dt, WorkOrder.created_at <= end_dt))
        except Exception:
            # Se a data vier em formato inesperado, ignorar filtro para não quebrar
            pass
    
    work_orders = query.offset(skip).limit(limit).all()
    
    # Formatar resposta com dados do equipamento e técnico
    result = []
    for wo in work_orders:
        result.append({
            "id": wo.id,
            "number": wo.number,
            "title": wo.title,
            "description": wo.description,
            "priority": wo.priority,
            "type": wo.type,
            "status": wo.status,
            "equipment_id": wo.equipment_id,
            "equipment_name": wo.equipment.name if wo.equipment else "N/A",
            "equipment_prefix": wo.equipment.prefix if wo.equipment else None,
            "requested_by": wo.requested_by,
            "assigned_to": wo.assigned_to,
            "technician_id": wo.technician_id,
            "technician_name": wo.technician.name if getattr(wo, "technician", None) else (wo.assigned_to or None),
            "estimated_hours": wo.estimated_hours,
            "actual_hours": wo.actual_hours,
            "cost": wo.cost,
            "created_at": wo.created_at.isoformat() if wo.created_at else None,
            "started_at": wo.started_at.isoformat() if wo.started_at else None,
            "completed_at": wo.completed_at.isoformat() if wo.completed_at else None,
            "due_date": wo.due_date.isoformat() if wo.due_date else None,
            "notes": wo.notes
        })
    
    return result

@router.post("/api/work-orders")
async def create_work_order(work_order: WorkOrderCreate, db: Session = Depends(get_db)):
    """Criar nova ordem de serviço. Se horímetro for informado, registrar HorimeterLog e atualizar equipamento."""
    # Gerar número sequencial
    last_os = db.query(WorkOrder).order_by(WorkOrder.id.desc()).first()
    if last_os:
        last_number = int(last_os.number)
        new_number = str(last_number + 1)
    else:
        new_number = "100000"

    # Preparar dados e extrair horímetro do payload (WorkOrder não possui este campo)
    payload = work_order.dict(exclude_unset=True)
    horimeter_value = payload.pop("horimeter", None)
    equipment_id = payload.get("equipment_id")

    # Validar horímetro (se fornecido) antes de criar OS
    equipment = None
    if horimeter_value is not None and equipment_id:
        equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
        if not equipment:
            raise HTTPException(status_code=404, detail="Equipamento não encontrado para registrar horímetro")
        try:
            new_value = float(horimeter_value)
        except ValueError:
            raise HTTPException(status_code=400, detail="Valor de horímetro inválido")
        current_value = float(equipment.current_horimeter or 0)
        if new_value <= current_value:
            raise HTTPException(
                status_code=400,
                detail=f"O valor de horímetro informado ({new_value}) deve ser maior que o valor atual ({current_value})"
            )

    # Criar OS (sem o campo horímetro)
    db_work_order = WorkOrder(
        number=new_number,
        **payload
    )
    db.add(db_work_order)
    db.commit()
    db.refresh(db_work_order)

    # Se horímetro foi informado, registrar log e atualizar equipamento
    if horimeter_value is not None and equipment is not None:
        recorded_by = payload.get("requested_by") or "Sistema - Abertura de OS"
        recorded_at = db_work_order.created_at or datetime.now()
        previous_value = float(equipment.current_horimeter or 0)
        new_value = float(horimeter_value)
        difference = new_value - previous_value

        # Criar registro de log
        horimeter_log = HorimeterLog(
            equipment_id=equipment.id,
            previous_value=previous_value,
            new_value=new_value,
            difference=difference,
            recorded_by=recorded_by,
            recorded_at=recorded_at,
            notes=f"Horímetro registrado ao abrir OS #{db_work_order.number}"
        )

        # Atualizar equipamento
        equipment.current_horimeter = new_value
        equipment.last_horimeter_update = recorded_at
        equipment.updated_at = datetime.now()

        # Persistir alterações
        db.add(horimeter_log)
        db.commit()
        db.refresh(horimeter_log)

        # Verificar preventivas automáticas
        try:
            await check_and_create_preventive_maintenance(equipment, db)
        except Exception:
            # Não bloquear criação da OS por erro na verificação de preventiva
            pass

    return db_work_order

@router.get("/api/work-orders/{work_order_id}")
async def get_work_order(work_order_id: int, db: Session = Depends(get_db)):
    """Obter ordem de serviço específica"""
    work_order = db.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="Ordem de serviço não encontrada")
    return work_order

@router.put("/api/work-orders/{work_order_id}")
async def update_work_order(
    work_order_id: int,
    work_order_update: WorkOrderUpdate,
    db: Session = Depends(get_db)
):
    """Atualizar ordem de serviço"""
    work_order = db.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="Ordem de serviço não encontrada")
    
    update_data = work_order_update.dict(exclude_unset=True)
    
    # Atualizar timestamps baseado no status
    if "status" in update_data:
        if update_data["status"] == "Em andamento" and not work_order.started_at:
            update_data["started_at"] = datetime.now()
        elif update_data["status"] == "Fechada" and not work_order.completed_at:
            update_data["completed_at"] = datetime.now()
    
    for field, value in update_data.items():
        setattr(work_order, field, value)
    
    db.commit()
    db.refresh(work_order)

    # Encerrar notificações de estoque vinculadas quando a OS for fechada
    if update_data.get("status") == "Fechada":
        try:
            from app.models.warehouse import StockNotification, StockNotificationItem
            notifications = db.query(StockNotification).filter(StockNotification.work_order_id == work_order.id).all()
            for n in notifications:
                # Verificar se todos os itens foram entregues
                items = db.query(StockNotificationItem).filter(StockNotificationItem.notification_id == n.id).all()
                all_delivered = all(it.status == "Entregue" for it in items) if items else True
                n.status = "Atendida" if all_delivered else "Cancelada"
                n.attended_at = datetime.now()
                n.attended_by = (work_order.assigned_to or "Sistema")
                note = "Encerrada automaticamente ao fechar OS"
                n.notes = f"{n.notes}\n{note}" if n.notes else note
                db.add(n)
            db.commit()
        except Exception:
            # Não bloquear fechamento da OS por falha ao encerrar notificações
            pass

    return work_order

@router.delete("/api/work-orders/{work_order_id}")
async def delete_work_order(work_order_id: int, db: Session = Depends(get_db)):
    """Excluir ordem de serviço"""
    work_order = db.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="Ordem de serviço não encontrada")
    
    # Verificar se a ordem de serviço pode ser excluída (não está em andamento)
    if work_order.status == "Em andamento":
        raise HTTPException(
            status_code=400, 
            detail="Não é possível excluir uma ordem de serviço em andamento"
        )
    
    # Excluir registros relacionados primeiro (time logs, checklists)
    db.query(TimeLog).filter(TimeLog.work_order_id == work_order_id).delete()
    
    # Excluir a ordem de serviço
    db.delete(work_order)
    db.commit()
    
    return {"message": "Ordem de serviço excluída com sucesso"}

@router.get("/api/work-orders/{work_order_id}/print")
async def print_work_order(work_order_id: int, db: Session = Depends(get_db)):
    """Gerar PDF da ordem de serviço para impressão"""
    # Buscar a ordem de serviço com equipamento e técnico relacionados
    work_order = db.query(WorkOrder).options(
        joinedload(WorkOrder.equipment),
        joinedload(WorkOrder.technician)
    ).filter(WorkOrder.id == work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="Ordem de serviço não encontrada")
    
    # Buscar equipamento relacionado
    equipment = work_order.equipment
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipamento não encontrado")
    
    # Gerar PDF usando ReportLab
    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, 
                              topMargin=2*cm, bottomMargin=2*cm)
        
        # Estilos
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.black
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=12,
            spaceAfter=12,
            textColor=colors.black
        )
        
        normal_style = styles['Normal']
        
        # Conteúdo do PDF
        story = []
        
        # Título
        story.append(Paragraph("ORDEM DE INTERVENÇÃO", title_style))
        story.append(Spacer(1, 12))
        
        # Informações básicas
        info_data = [
            ['Nº:', str(work_order.id), 'Data:', work_order.created_at.strftime('%d/%m/%Y')],
            ['Para:', work_order.assigned_to or 'Manutenção', 'Técnico:', work_order.technician.name if work_order.technician else 'Não atribuído']
        ]
        
        info_table = Table(info_data, colWidths=[3*cm, 6*cm, 3*cm, 4*cm])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(info_table)
        story.append(Spacer(1, 20))
        
        # Identificação do Equipamento
        story.append(Paragraph("Identificação da Unidade de Equipamento", heading_style))
        
        equipment_data = [
            ['PREFIXO', 'DESCRIÇÃO', 'Nº Chassi'],
            [equipment.prefix, equipment.name, getattr(equipment, 'chassis_number', '')]
        ]
        
        equipment_table = Table(equipment_data, colWidths=[5.3*cm, 5.3*cm, 5.3*cm])
        equipment_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(equipment_table)
        story.append(Spacer(1, 20))
        
        # Tipo de Intervenção
        story.append(Paragraph("Tipo de Intervenção", heading_style))
        story.append(Paragraph(f"<b>Tipo:</b> {work_order.type}", normal_style))
        story.append(Paragraph(f"<b>Centro Planejamento:</b> MTDL", normal_style))
        story.append(Spacer(1, 20))
        
        # Dados sobre o Equipamento
        story.append(Paragraph("Dados sobre o Equipamento", heading_style))
        story.append(Paragraph(f"<b>Horímetro atual:</b> {equipment.current_horimeter or '0'}", normal_style))
        story.append(Paragraph(f"<b>Localização:</b> {equipment.location or 'MTDL - Pátio Principal'}", normal_style))
        story.append(Spacer(1, 20))
        
        # Serviço Solicitado
        story.append(Paragraph("Intervenção/Serviço Solicitado", heading_style))
        story.append(Paragraph(f"<b>Descrição:</b> {work_order.description}", normal_style))
        story.append(Spacer(1, 20))
        
        # Lista de Tarefas do Plano (agrupadas por subcategoria)
        story.append(Paragraph("Lista de Tarefas", heading_style))

        # Tentar localizar o plano vinculado à OS via Notificação de Estoque
        plan = None
        plan_actions = []
        plan_materials = []
        try:
            stock_notif = db.query(StockNotification).filter(StockNotification.work_order_id == work_order.id).first()
            if stock_notif:
                plan = db.query(MaintenancePlan).filter(MaintenancePlan.id == stock_notif.maintenance_plan_id).first()
        except Exception:
            plan = None

        if plan:
            plan_actions = db.query(MaintenancePlanAction)\
                .filter(MaintenancePlanAction.plan_id == plan.id)\
                .order_by(MaintenancePlanAction.sequence_order.asc()).all()
            plan_materials = db.query(MaintenancePlanMaterial).filter(MaintenancePlanMaterial.plan_id == plan.id).all()

        tasks_data = [['Subcategoria', 'Tarefa', '✓']]
        if plan_actions:
            # Usar action_type como "Subcategoria" e agrupar
            actions_by_type = {}
            for a in plan_actions:
                typ = a.action_type or "Geral"
                actions_by_type.setdefault(typ, []).append(a.description or "")
            for typ, descs in actions_by_type.items():
                for desc in descs:
                    tasks_data.append([typ, desc, '☐'])
        else:
            # Fallback para tarefas padrão quando não houver plano/ações
            tasks_data.extend([
                ['Geral', 'Trocar filtro de óleo do motor', '☐'],
                ['Geral', 'Coletar amostra motor', '☐'],
                ['Geral', 'Drenar reservatório de ar', '☐'],
                ['Geral', 'Executar lubrificação geral', '☐'],
                ['Geral', 'Verificar carga do extintor de incêndio', '☐'],
                ['Geral', 'Apertar porcas das rodas', '☐'],
                ['Geral', 'Calibrar pneus', '☐'],
                ['Geral', 'Verificar desgaste dos pneus', '☐'],
                ['Geral', 'Verificar correia e tensor do motor', '☐'],
                ['Geral', 'Drenar filtro separador água-combustível', '☐'],
                ['Geral', 'Trocar o filtro de combustível', '☐'],
                ['Geral', 'Verificar o nível de óleo do motor', '☐']
            ])

        tasks_table = Table(tasks_data, colWidths=[3*cm, 11*cm, 2*cm])
        tasks_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(tasks_table)

        # Materiais do Plano
        story.append(Spacer(1, 16))
        if plan_materials:
            story.append(Paragraph("Materiais Necessários", heading_style))
            materials_data = [['Código', 'Material', 'Quantidade', 'Unidade']]
            for pm in plan_materials:
                mat = db.query(Material).filter(Material.id == pm.material_id).first()
                code = mat.code if mat else '-'
                name = mat.name if mat else 'Material'
                qty = f"{pm.quantity:.2f}"
                unit = pm.unit or 'un'
                materials_data.append([code, name, qty, unit])

            materials_table = Table(materials_data, colWidths=[3.5*cm, 8.5*cm, 2.5*cm, 2.5*cm])
            materials_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (2, 1), (2, -1), 'CENTER'),
                ('ALIGN', (3, 1), (3, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(materials_table)
            story.append(Spacer(1, 30))
        else:
            story.append(Spacer(1, 30))
        
        # Assinaturas
        signature_data = [
            ['EXECUTANTE', 'ENCARREGADO / DIR. OBRA', 'RESPONSÁVEL OFICINA'],
            ['', '', ''],
            ['(Assinatura)', '(Assinatura)', '(Assinatura)'],
            ['___/___/______', '___/___/______', '___/___/______']
        ]
        
        signature_table = Table(signature_data, colWidths=[5.3*cm, 5.3*cm, 5.3*cm])
        signature_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(signature_table)
        
        # Construir PDF
        doc.build(story)
        
        # Obter bytes do PDF
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        # Retornar PDF como resposta
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=ordem_servico_{work_order_id}.pdf"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar PDF: {str(e)}")

# API Endpoints - Equipment

@router.get("/api/equipment")
async def equipment_api(db: Session = Depends(get_db)):
    """API para listar equipamentos (alias para compatibilidade de testes)"""
    return await equipment_list(db)

@router.post("/equipment")
async def create_equipment(equipment_data: dict, db: Session = Depends(get_db)):
    """Criar novo equipamento"""
    # Ignorar qualquer parâmetro de geração automática de planos (modo legado)
    equipment_data.pop("plan_generation_mode", None)

    # Validar prefixo obrigatório e checar duplicidade
    prefix = equipment_data.get("prefix")
    if not prefix:
        raise HTTPException(status_code=400, detail="Prefixo é obrigatório")
    existing = db.query(Equipment).filter(Equipment.prefix == prefix).first()
    if existing:
        raise HTTPException(status_code=400, detail="Prefixo já existe")
    
    # Processar data de mobilização se fornecida
    if "mobilization_date" in equipment_data and equipment_data["mobilization_date"]:
        try:
            equipment_data["mobilization_date"] = datetime.fromisoformat(equipment_data["mobilization_date"])
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de data inválido")
    
    # Definir horímetro atual igual ao inicial se não fornecido
    if "initial_horimeter" in equipment_data and equipment_data["initial_horimeter"] is not None:
        if "current_horimeter" not in equipment_data or equipment_data["current_horimeter"] is None:
            equipment_data["current_horimeter"] = equipment_data["initial_horimeter"]
    
    # Definir status padrão se não fornecido
    if "status" not in equipment_data:
        equipment_data["status"] = "Ativo"
    
    db_equipment = Equipment(**equipment_data)
    db.add(db_equipment)
    db.commit()
    db.refresh(db_equipment)

    # Não criar planos automaticamente: o cadastro de planos será exclusivamente manual

    # Gerar perfil técnico automático e salvar
    try:
        profile_dict = build_technical_profile_for_equipment(db_equipment)
        existing_profile = db.query(EquipmentTechnicalProfile).filter(EquipmentTechnicalProfile.equipment_id == db_equipment.id).first()
        if not existing_profile:
            profile = EquipmentTechnicalProfile(
                equipment_id=db_equipment.id,
                profile_data=profile_dict,
            )
            db.add(profile)
            db.commit()
        else:
            existing_profile.profile_data = profile_dict
            db.commit()
    except Exception:
        # Perfil técnico é auxiliar; não bloquear criação
        pass

    # Retornar payload JSON simples com ID e campos essenciais
    return {
        "id": db_equipment.id,
        "prefix": db_equipment.prefix,
        "name": db_equipment.name,
        "status": db_equipment.status,
        "manufacturer": db_equipment.manufacturer,
        "model": db_equipment.model,
    }

"""Rotas e utilidades de manutenção."""

# Upload de manual do fabricante para um equipamento (suporta múltiplos arquivos)
@router.post("/equipment/{equipment_id}/manual/upload")
async def upload_equipment_manual(
    equipment_id: int,
    files: List[UploadFile] = File(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    # Validar equipamento
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipamento não encontrado")

    # Unificar parâmetro para compatibilidade retroativa (aceita 'file' único ou 'files')
    upload_list: List[UploadFile] = []
    if files:
        upload_list.extend([f for f in files if f is not None])
    if file is not None:
        upload_list.append(file)
    if not upload_list:
        raise HTTPException(status_code=400, detail="Nenhum arquivo enviado")

    # Criar diretório de armazenamento
    base_dir = os.path.join("data", "manuals", str(equipment_id))
    try:
        os.makedirs(base_dir, exist_ok=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falha ao preparar diretório de armazenamento: {str(e)}")

    saved_files: List[dict] = []
    for uf in upload_list:
        safe_filename = (uf.filename or "").replace("\r", "").replace("\n", "").strip()
        if not safe_filename:
            continue
        saved_path = os.path.join(base_dir, safe_filename)
        try:
            content = await uf.read()
            with open(saved_path, "wb") as f:
                f.write(content)
            saved_files.append({"filename": safe_filename, "path": saved_path})
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Falha ao salvar arquivo '{safe_filename}': {str(e)}")

    if not saved_files:
        raise HTTPException(status_code=400, detail="Falha ao salvar arquivos enviados")

    return {"message": "Arquivo(s) anexado(s) com sucesso", "files": saved_files}

# Geração de planos de manutenção para um equipamento com base em modo escolhido
@router.post("/equipment/{equipment_id}/plans/generate")
async def generate_equipment_plans(
    equipment_id: int,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
):
    # Validar equipamento
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipamento não encontrado")

    mode = str(payload.get("mode", "")).lower()
    if mode not in ["manual", "internet"]:
        raise HTTPException(status_code=400, detail="Modo inválido. Use 'manual' ou 'internet'.")

    from app.services.plan_generator import generate_plans_from_manual, generate_plans_via_internet
    plan_specs = []

    if mode == "manual":
        # Encontrar arquivo de manual mais recente
        base_dir = os.path.join("data", "manuals", str(equipment_id))
        if not os.path.isdir(base_dir):
            raise HTTPException(status_code=400, detail="Nenhum manual anexado para este equipamento")

        files = [os.path.join(base_dir, f) for f in os.listdir(base_dir) if os.path.isfile(os.path.join(base_dir, f))]
        if not files:
            raise HTTPException(status_code=400, detail="Nenhum manual disponível no diretório")
        latest_file = max(files, key=lambda p: os.path.getmtime(p))

        try:
            plan_specs = generate_plans_from_manual(equipment, latest_file)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro ao gerar planos a partir do manual: {str(e)}")

    elif mode == "internet":
        try:
            plan_specs = generate_plans_via_internet(equipment)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro ao gerar planos via internet/IA: {str(e)}")

    if not plan_specs:
        return {"message": "Nenhum plano gerado", "plans_created": 0}

    created_count = 0
    created_plan_ids = []
    # Persistir planos e ações
    from app.models.maintenance import MaintenancePlanAction
    for spec in plan_specs:
        try:
            plan = MaintenancePlan(
                name=spec.get("name") or f"Plano {equipment.prefix}",
                equipment_id=equipment.id,
                type=spec.get("type") or "Preventiva",
                interval_type=spec.get("interval_type") or "Horímetro",
                interval_value=int(spec.get("interval_value") or 250),
                description=spec.get("description"),
                checklist_template=spec.get("checklist_template") or {"items": []},
                is_active=True,
                estimated_hours=float(spec.get("estimated_hours") or 4.0),
                priority=spec.get("priority") or "Normal",
            )
            db.add(plan)
            db.flush()

            for action in spec.get("actions", []):
                db_action = MaintenancePlanAction(
                    plan_id=plan.id,
                    description=action.get("description") or "Ação",
                    action_type=action.get("action_type") or "Inspeção",
                    sequence_order=action.get("sequence_order") or 1,
                    estimated_time_minutes=action.get("estimated_time_minutes"),
                    requires_specialist=bool(action.get("requires_specialist")) if action.get("requires_specialist") is not None else False,
                    safety_notes=action.get("safety_notes"),
                )
                db.add(db_action)

            # Persistir materiais do plano (se presentes). Em modo 'manual', não criar Material ausente;
            # notificar apenas os itens não cadastrados.
            from app.models.maintenance import MaintenancePlanMaterial
            from app.models.warehouse import Material, StockNotification, StockNotificationItem

            materials_specs = spec.get("materials", []) or []
            if materials_specs:
                missing_details = []
                next_code = None
                if mode != "manual":
                    # Determinar próximo código sequencial para novos materiais (apenas fora do modo manual)
                    last_material = db.query(Material).order_by(Material.id.desc()).first()
                    if last_material and last_material.code and last_material.code.isdigit():
                        next_code = str(int(last_material.code) + 1)
                    else:
                        max_code_material = db.query(Material).filter(
                            Material.code.regexp_match(r'^\d+$')
                        ).order_by(Material.code.desc()).first()
                        if max_code_material and int(max_code_material.code) >= 100000:
                            next_code = str(int(max_code_material.code) + 1)
                        else:
                            next_code = "100000"

                for m in materials_specs:
                    ref = (m.get("reference") or "").strip()
                    name = (m.get("name") or "").strip()
                    mat = None
                    if ref:
                        mat = db.query(Material).filter(Material.reference == ref).first()
                    if not mat and name:
                        mat = db.query(Material).filter(Material.name == name).first()
                    if not mat:
                        if mode == "manual":
                            # Em modo manual, não criar material automaticamente; coletar para notificação
                            missing_details.append({
                                "name": name or "Material",
                                "reference": ref or "",
                                "quantity": float(m.get("quantity") or 1.0),
                                "unit": m.get("unit") or "un",
                                "description": (m.get("description") or "").strip(),
                            })
                            continue
                        else:
                            # Fora do modo manual, criar material para viabilizar o plano
                            mat = Material(
                                code=next_code,
                                name=name or ref or "Material",
                                description=m.get("description") or name or "Material para manutenção preventiva",
                                reference=ref or None,
                                category=m.get("category") or None,
                                unit=m.get("unit") or "un",
                            )
                            db.add(mat)
                            db.flush()
                            next_code = str(int(next_code) + 1)

                    if mat:
                        db.add(MaintenancePlanMaterial(
                            plan_id=plan.id,
                            material_id=mat.id,
                            quantity=float(m.get("quantity") or 1.0),
                            unit=m.get("unit") or "un",
                            is_critical=bool(m.get("is_critical") or False),
                        ))

                db.commit()
                db.refresh(plan)

                # Modo manual: não criar OS nem Notificação automaticamente para itens ausentes
                # Apenas registrar internamente os detalhes faltantes para eventual consulta/relatório futuro
                if mode == "manual" and missing_details:
                    pass

                # Fora do modo manual: não criar OS/notificação de provisionamento automaticamente.
                # A notificação de materiais será criada apenas quando o plano for disparado
                # pelo horímetro em check_and_create_preventive_maintenance.

            db.commit()
            db.refresh(plan)
            created_count += 1
            created_plan_ids.append(plan.id)
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Erro ao salvar plano gerado: {str(e)}")

    return {"message": "Planos gerados com sucesso", "plans_created": created_count, "plan_ids": created_plan_ids}

@router.get("/equipment/validate-cnpj")
async def validate_cnpj(cnpj: str):
    """Validar CNPJ via serviço externo e retornar nome da empresa.
    Usa BrasilAPI: https://brasilapi.com.br/api/cnpj/v1/{cnpj}
    """
    # Sanitizar CNPJ para conter apenas dígitos
    digits = "".join(ch for ch in cnpj if ch.isdigit())
    if len(digits) != 14:
        raise HTTPException(status_code=400, detail="CNPJ inválido. Informe 14 dígitos.")

    url = f"https://brasilapi.com.br/api/cnpj/v1/{digits}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
        if resp.status_code == 200:
            data = resp.json()
            company_name = (
                data.get("razao_social")
                or data.get("nome_fantasia")
                or data.get("nome")
            )
            return {
                "valid": True,
                "cnpj": digits,
                "company_name": company_name,
                "raw": data,
            }
        elif resp.status_code == 404:
            return {"valid": False, "cnpj": digits, "error": "CNPJ não encontrado"}
        else:
            # Resposta inesperada do provedor
            return {
                "valid": False,
                "cnpj": digits,
                "error": f"Erro do provedor (status {resp.status_code})"
            }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erro ao consultar serviço externo: {e}")

@router.put("/equipment/{equipment_id}")
async def update_equipment(equipment_id: int, equipment_data: dict, db: Session = Depends(get_db)):
    """Atualizar equipamento existente"""
    # Buscar equipamento
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipamento não encontrado")
    
    # Verificar se o prefixo já existe (se foi alterado)
    if "prefix" in equipment_data and equipment_data["prefix"] != equipment.prefix:
        existing = db.query(Equipment).filter(
            Equipment.prefix == equipment_data["prefix"],
            Equipment.id != equipment_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Prefixo já existe")
    
    # Processar data de mobilização se fornecida
    if "mobilization_date" in equipment_data and equipment_data["mobilization_date"]:
        try:
            equipment_data["mobilization_date"] = datetime.fromisoformat(equipment_data["mobilization_date"])
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de data inválido")
    
    # Atualizar campos
    for field, value in equipment_data.items():
        if hasattr(equipment, field):
            setattr(equipment, field, value)
    
    db.commit()
    db.refresh(equipment)
    return equipment

@router.get("/equipment/{equipment_id}")
async def get_equipment_detail(equipment_id: int, db: Session = Depends(get_db)):
    """Obter detalhes do equipamento"""
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipamento não encontrado")
    return equipment

@router.put("/equipment/{equipment_id}/horimeter")
async def update_horimeter(
    equipment_id: int,
    horimeter_data: dict,
    db: Session = Depends(get_db)
):
    """Atualizar horímetro do equipamento"""
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipamento não encontrado")
    
    new_value = horimeter_data["new_value"]
    
    # Validar se o novo valor é maior que o atual
    if new_value <= equipment.current_horimeter:
        raise HTTPException(
            status_code=400, 
            detail="Novo valor deve ser maior que o atual"
        )
    
    # Criar log de horímetro
    from app.models.equipment import HorimeterLog
    log = HorimeterLog(
        equipment_id=equipment_id,
        previous_value=equipment.current_horimeter,
        new_value=new_value,
        difference=new_value - equipment.current_horimeter,
        recorded_by=horimeter_data.get("recorded_by"),
        notes=horimeter_data.get("notes")
    )
    
    # Atualizar equipamento
    equipment.current_horimeter = new_value
    equipment.last_horimeter_update = datetime.now()
    
    db.add(log)
    db.commit()
    db.refresh(equipment)
    
    # Verificar se deve gerar manutenção preventiva
    maintenance_orders_created = await check_and_create_preventive_maintenance(equipment, db)
    
    response = {"message": "Horímetro atualizado com sucesso", "equipment": equipment}
    if maintenance_orders_created:
        response["maintenance_orders_created"] = maintenance_orders_created
        response["message"] += f". {len(maintenance_orders_created)} ordem(ns) de manutenção preventiva criada(s)."
    
    return response

async def check_and_create_preventive_maintenance(equipment: Equipment, db: Session):
    """Verificar e criar ordens de manutenção preventiva baseadas no horímetro"""
    from app.models.warehouse import StockNotification, StockNotificationItem, Material
    from app.models.maintenance import MaintenanceAlert
    
    # Calcular horas trabalhadas desde a mobilização
    if equipment.initial_horimeter is None or equipment.current_horimeter is None:
        return []
    
    hours_worked = equipment.current_horimeter - equipment.initial_horimeter
    # Guardar contra valores incorretos de horímetro (ex.: inicial > atual)
    if hours_worked < 0:
        return []
    
    # Buscar planos de manutenção ativos para este equipamento
    maintenance_plans = db.query(MaintenancePlan).filter(
        and_(
            MaintenancePlan.equipment_id == equipment.id,
            MaintenancePlan.is_active == True,
            func.lower(MaintenancePlan.interval_type).in_(["horímetro", "horimetro", "horas"]) 
        )
    ).all()
    
    orders_created = []
    alerts_created = []
    
    for plan in maintenance_plans:
        if not plan.interval_value or plan.interval_value <= 0:
            continue
        # Calcular quantos ciclos de manutenção já foram completados
        cycles_completed = int(hours_worked // plan.interval_value)
        next_maintenance_hours = (cycles_completed + 1) * plan.interval_value
        hours_until_maintenance = next_maintenance_hours - hours_worked
        
        # Verificar se atingiu 90% do intervalo (notificação de alerta)
        ninety_percent_threshold = next_maintenance_hours - (plan.interval_value * 0.1)
        
        if hours_worked >= ninety_percent_threshold and hours_worked < next_maintenance_hours:
            # Verificar se já existe alerta para este ciclo
            existing_alert = db.query(MaintenanceAlert).filter(
                and_(
                    MaintenanceAlert.equipment_id == equipment.id,
                    MaintenanceAlert.maintenance_plan_id == plan.id,
                    MaintenanceAlert.target_horimeter == next_maintenance_hours,
                    MaintenanceAlert.is_acknowledged == False
                )
            ).first()
            
            if not existing_alert:
                # Criar alerta de 90%
                alert = MaintenanceAlert(
                    equipment_id=equipment.id,
                    maintenance_plan_id=plan.id,
                    alert_type="Previsto",
                    current_horimeter=equipment.current_horimeter,
                    target_horimeter=next_maintenance_hours,
                    hours_remaining=hours_until_maintenance,
                    message=f"Manutenção preventiva próxima para {equipment.name} ({equipment.prefix}). Restam {hours_until_maintenance:.1f} horas para atingir {next_maintenance_hours}h.",
                    created_at=datetime.now()
                )
                
                db.add(alert)
                alerts_created.append(alert)
        
        # Verificar se ultrapassou algum marco de manutenção (corrigido)
        # Verificar todos os marcos que foram ultrapassados, não apenas o próximo
        for cycle in range(1, cycles_completed + 1):
            maintenance_milestone = cycle * plan.interval_value
            
            # Verificar se já existe uma OS para este marco específico (qualquer status)
            # Isso evita recriar OS para ciclos já atendidos/fechados em reconciliações futuras.
            existing_order = db.query(WorkOrder).filter(
                and_(
                    WorkOrder.equipment_id == equipment.id,
                    WorkOrder.type == "Preventiva",
                    WorkOrder.title.contains(f"{plan.name}"),
                    WorkOrder.description.contains(f"{maintenance_milestone}h")
                )
            ).first()
            
            if not existing_order and hours_worked >= maintenance_milestone:
                # Gerar número da OS
                last_order = db.query(WorkOrder).order_by(WorkOrder.id.desc()).first()
                next_number = 100000 if not last_order else int(last_order.number) + 1
                
                # Criar ordem de serviço
                work_order = WorkOrder(
                    number=str(next_number),
                    title=f"Manutenção Preventiva - {plan.name}",
                    description=f"Manutenção preventiva automática gerada ao atingir {maintenance_milestone} horas trabalhadas. Horímetro atual: {equipment.current_horimeter}h. Plano: {plan.name}",
                    priority=plan.priority,
                    type="Preventiva",
                    equipment_id=equipment.id,
                    estimated_hours=plan.estimated_hours,
                    created_at=datetime.now()
                )
                
                db.add(work_order)
                db.commit()
                db.refresh(work_order)
                
                # Criar notificação de estoque para materiais
                if plan.plan_materials:
                    stock_notification = StockNotification(
                        work_order_id=work_order.id,
                        equipment_id=equipment.id,
                        maintenance_plan_id=plan.id,
                        priority=plan.priority,
                        message=f"Solicitação automática de materiais para manutenção preventiva - {equipment.name} ({equipment.prefix}). OS: {work_order.number}",
                        status="Pendente",
                        created_at=datetime.now()
                    )
                    
                    db.add(stock_notification)
                    db.commit()
                    db.refresh(stock_notification)
                    
                    # Adicionar itens de material à notificação
                    for plan_material in plan.plan_materials:
                        material = db.query(Material).filter(Material.id == plan_material.material_id).first()
                        
                        if material:
                            notification_item = StockNotificationItem(
                                notification_id=stock_notification.id,
                                material_id=material.id,
                                quantity_needed=plan_material.quantity,
                                quantity_available=material.current_stock
                            )
                            
                            db.add(notification_item)
                
                # Marcar alertas relacionados como reconhecidos
                related_alerts = db.query(MaintenanceAlert).filter(
                    and_(
                        MaintenanceAlert.equipment_id == equipment.id,
                        MaintenanceAlert.maintenance_plan_id == plan.id,
                        MaintenanceAlert.target_horimeter == maintenance_milestone,
                        MaintenanceAlert.is_acknowledged == False
                    )
                ).all()
                
                for alert in related_alerts:
                    alert.is_acknowledged = True
                    alert.acknowledged_by = "Sistema"
                    alert.acknowledged_at = datetime.now()
                
                orders_created.append(work_order)
    
    # Commit final para salvar alertas e atualizações
    db.commit()
    
    return {
        "orders_created": len(orders_created),
        "alerts_created": len(alerts_created),
        "orders": [{"id": order.id, "number": order.number, "title": order.title} for order in orders_created],
        "alerts": [{"id": alert.id, "message": alert.message, "hours_remaining": alert.hours_remaining} for alert in alerts_created]
    }

# API Endpoints - Time Logs
@router.post("/api/work-orders/{work_order_id}/time-logs")
async def create_time_log(
    work_order_id: int,
    time_log: TimeLogCreate,
    db: Session = Depends(get_db)
):
    """Registrar horas trabalhadas"""
    work_order = db.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="Ordem de serviço não encontrada")
    
    # Calcular horas trabalhadas
    start_time = datetime.fromisoformat(time_log.start_time)
    end_time = datetime.fromisoformat(time_log.end_time)
    hours_worked = (end_time - start_time).total_seconds() / 3600
    
    db_time_log = TimeLog(
        work_order_id=work_order_id,
        technician=time_log.technician,
        start_time=start_time,
        end_time=end_time,
        hours_worked=hours_worked,
        activity_description=time_log.activity_description
    )
    
    db.add(db_time_log)
    
    # Atualizar horas totais da OS
    total_hours = db.query(func.sum(TimeLog.hours_worked)).filter(
        TimeLog.work_order_id == work_order_id
    ).scalar() or 0
    work_order.actual_hours = total_hours + hours_worked
    
    db.commit()
    db.refresh(db_time_log)
    
    return db_time_log

@router.get("/api/work-orders/{work_order_id}/time-logs")
async def get_time_logs(work_order_id: int, db: Session = Depends(get_db)):
    """Obter logs de tempo de uma OS"""
    time_logs = db.query(TimeLog).filter(TimeLog.work_order_id == work_order_id).all()
    return time_logs

# ------------------------
# Perfil Técnico do Equipamento
# ------------------------

def build_technical_profile_for_equipment(equipment: Equipment) -> dict:
    """Construir perfil técnico do equipamento com base em dados do cadastro e boas práticas.
    Estrutura contempla elétrica, hidráulica, powertrain e estrutura, com planos preventivos/preditivos.
    """
    name = equipment.name or equipment.prefix
    model = equipment.model or "N/D"
    manufacturer = equipment.manufacturer or "N/D"
    year = equipment.year or "N/D"
    category = getattr(equipment, "category", None) or "N/D"

    profile = {
        "summary": {
            "name": name,
            "prefix": equipment.prefix,
            "model": model,
            "manufacturer": manufacturer,
            "year": year,
            "category": category,
        },
        "components": {
            "electrical": [
                " chicote principal e derivações",
                " sensores e atuadores",
                " alternador e motor de partida",
                " painel de controle e fusíveis",
            ],
            "hydraulic": [
                " bomba hidráulica",
                " válvulas direcional e de alívio",
                " mangueiras e conexões",
                " cilindros (braço/lança/caçamba onde aplicável)",
            ],
            "powertrain": [
                " motor (combustão ou elétrico)",
                " transmissão e diferenciais",
                " sistema de arrefecimento",
                " filtro de combustível e linha de alimentação",
            ],
            "structural": [
                " chassi e subconjuntos",
                " esteiras/rodas e rolamentos",
                " pinos e buchas",
                " caçamba/implementos e fixações",
            ],
        },
        "maintenance": {
            "preventive": {
                "objective": "evitar falhas antes que ocorram",
                "common_actions": [
                    "troca programada de filtros e óleos",
                    "lubrificação de componentes",
                    "verificação de mangueiras, conexões e cilindros hidráulicos",
                    "inspeção de esteiras/rodas, caçamba e estrutura",
                ],
                "frequency": {
                    "by_hours": ["250h", "500h"],
                    "by_calendar": ["mensal", "trimestral"],
                },
            },
            "predictive": {
                "objective": "monitorar desgaste e antecipar falhas com base em dados",
                "common_actions": [
                    "análise de vibração",
                    "termografia em componentes",
                    "monitoramento de pressão e vazão hidráulica",
                    "telemetria para detectar anomalias",
                ],
                "benefit": "reduz paradas inesperadas e otimiza manutenção",
            },
            "corrective": {
                "objective": "reparar falhas que já ocorreram",
                "common_actions": [
                    "substituição de peças danificadas",
                    "reparos em sistemas hidráulicos ou elétricos",
                    "soldagem de componentes estruturais",
                ],
                "drawback": "mais cara e com maior tempo de inatividade",
            },
        },
        "critical_points": [
            "sistema hidráulico: bombas, válvulas, mangueiras e cilindros",
            "motor e transmissão: inspeção para evitar superaquecimento e perda de potência",
            "sistema elétrico: sensores, chicotes e painel de controle",
            "componentes estruturais: braço, lança e caçamba sob desgaste mecânico",
        ],
    }
    return profile

def create_default_preventive_plans(equipment: Equipment, db: Session) -> None:
    """Criar planos preventivos de 250h e 500h para o equipamento, se não existirem."""
    existing = db.query(MaintenancePlan).filter(MaintenancePlan.equipment_id == equipment.id).count()
    if existing:
        return

    plans_specs = [
        {
            "name": f"Troca de óleo {equipment.prefix}",
            "interval_value": 250,
            "description": "Troca de óleo do motor e inspeções básicas",
            "estimated_hours": 4.0,
        },
        {
            "name": f"Inspeção geral {equipment.prefix}",
            "interval_value": 500,
            "description": "Inspeção geral do equipamento, filtros e limpeza",
            "estimated_hours": 6.0,
        },
    ]

    for spec in plans_specs:
        plan = MaintenancePlan(
            name=spec["name"],
            equipment_id=equipment.id,
            type="Preventiva",
            interval_type="Horímetro",
            interval_value=spec["interval_value"],
            description=spec["description"],
            checklist_template={"items": ["Checar níveis", "Inspecionar vazamentos"]},
            is_active=True,
            estimated_hours=spec["estimated_hours"],
            priority="Normal",
        )
        db.add(plan)
        db.flush()

        # Ações padrão
        from app.models.maintenance import MaintenancePlanAction
        actions = [
            MaintenancePlanAction(
                plan_id=plan.id,
                description="Inspeção visual",
                action_type="Inspeção",
                sequence_order=1,
                estimated_time_minutes=30,
            ),
            MaintenancePlanAction(
                plan_id=plan.id,
                description="Troca de óleo e filtro",
                action_type="Troca",
                sequence_order=2,
                estimated_time_minutes=120,
            ),
            MaintenancePlanAction(
                plan_id=plan.id,
                description="Lubrificação de pontos críticos",
                action_type="Ajuste",
                sequence_order=3,
                estimated_time_minutes=60,
            ),
        ]
        for a in actions:
            db.add(a)

        # Materiais padrão baseados no intervalo do plano
        from app.models.maintenance import MaintenancePlanMaterial
        from app.models.warehouse import Material, StockNotification, StockNotificationItem

        materials_specs = []
        if spec["interval_value"] == 250:
            materials_specs = [
                {"name": "Óleo do motor", "description": "Óleo do motor", "unit": "L", "quantity": 20, "category": "Lubrificante"},
                {"name": "Filtro de óleo do motor", "description": "Filtro de óleo", "unit": "un", "quantity": 1, "category": "Filtro"},
                {"name": "Filtro de combustível", "description": "Filtro de combustível", "unit": "un", "quantity": 1, "category": "Filtro"},
                {"name": "Filtro de ar", "description": "Filtro de ar", "unit": "un", "quantity": 1, "category": "Filtro"},
                {"name": "Graxa multiuso", "description": "Graxa para lubrificação", "unit": "kg", "quantity": 1, "category": "Lubrificante"},
            ]
        elif spec["interval_value"] == 500:
            materials_specs = [
                {"name": "Óleo do motor", "description": "Óleo do motor", "unit": "L", "quantity": 20, "category": "Lubrificante"},
                {"name": "Filtro de óleo do motor", "description": "Filtro de óleo", "unit": "un", "quantity": 1, "category": "Filtro"},
                {"name": "Filtro de combustível", "description": "Filtro de combustível", "unit": "un", "quantity": 1, "category": "Filtro"},
                {"name": "Filtro de ar", "description": "Filtro de ar", "unit": "un", "quantity": 1, "category": "Filtro"},
                {"name": "Filtro hidráulico", "description": "Filtro do sistema hidráulico", "unit": "un", "quantity": 1, "category": "Filtro"},
                {"name": "Óleo hidráulico", "description": "Óleo do sistema hidráulico", "unit": "L", "quantity": 30, "category": "Lubrificante"},
            ]

        if materials_specs:
            # Determinar próximo código para novos materiais
            last_material = db.query(Material).order_by(Material.id.desc()).first()
            if last_material and last_material.code and last_material.code.isdigit():
                next_code = str(int(last_material.code) + 1)
            else:
                max_code_material = db.query(Material).filter(
                    Material.code.regexp_match(r'^\d+$')
                ).order_by(Material.code.desc()).first()
                if max_code_material and int(max_code_material.code) >= 100000:
                    next_code = str(int(max_code_material.code) + 1)
                else:
                    next_code = "100000"

            for m in materials_specs:
                ref = (m.get("reference") or "").strip()
                name = (m.get("name") or "").strip()
                mat = None
                if ref:
                    mat = db.query(Material).filter(Material.reference == ref).first()
                if not mat and name:
                    mat = db.query(Material).filter(Material.name == name).first()
                if not mat:
                    mat = Material(
                        code=next_code,
                        name=name or ref or "Material",
                        description=m.get("description") or name or "Material para manutenção preventiva",
                        reference=ref or None,
                        category=m.get("category") or None,
                        unit=m.get("unit") or "un",
                    )
                    db.add(mat)
                    db.flush()
                    next_code = str(int(next_code) + 1)

                db.add(MaintenancePlanMaterial(
                    plan_id=plan.id,
                    material_id=mat.id,
                    quantity=float(m.get("quantity") or 1.0),
                    unit=m.get("unit") or "un",
                    is_critical=bool(m.get("is_critical") or False),
                ))

            db.commit()
            db.refresh(plan)

            # Não criar OS/Notificação de provisionamento automaticamente.
            # As notificações serão criadas quando o plano for de fato disparado
            # em check_and_create_preventive_maintenance.

    db.commit()

@router.get("/equipment/{equipment_id}/technical-profile")
async def get_technical_profile(equipment_id: int, db: Session = Depends(get_db)):
    """Retornar perfil técnico do equipamento. Gera e salva se não existir."""
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipamento não encontrado")

    profile = db.query(EquipmentTechnicalProfile).filter(EquipmentTechnicalProfile.equipment_id == equipment_id).first()
    if not profile:
        # Gerar e salvar
        profile_dict = build_technical_profile_for_equipment(equipment)
        profile = EquipmentTechnicalProfile(
            equipment_id=equipment.id,
            profile_data=profile_dict,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

    return {
        "equipment": {
            "id": equipment.id,
            "prefix": equipment.prefix,
            "name": equipment.name,
            "model": equipment.model,
            "manufacturer": equipment.manufacturer,
            "year": equipment.year,
        },
        "profile": profile.profile_data,
    }

@router.post("/equipment/{equipment_id}/technical-profile/generate")
async def regenerate_technical_profile(equipment_id: int, db: Session = Depends(get_db)):
    """Regenerar perfil técnico do equipamento e salvar."""
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipamento não encontrado")

    profile_dict = build_technical_profile_for_equipment(equipment)
    profile = db.query(EquipmentTechnicalProfile).filter(EquipmentTechnicalProfile.equipment_id == equipment_id).first()
    if not profile:
        profile = EquipmentTechnicalProfile(
            equipment_id=equipment.id,
            profile_data=profile_dict,
        )
        db.add(profile)
    else:
        profile.profile_data = profile_dict

    db.commit()
    return {"message": "Perfil técnico atualizado", "profile": profile_dict}

# API Endpoints - Maintenance Plans

@router.post("/plans")
async def create_maintenance_plan(
    request: Request,
    data: str = Form(None),
    documents: List[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    """Criar novo plano de manutenção.
    Aceita JSON puro ou multipart/form-data com campo 'data' (JSON) e 'documents' (arquivos).
    """
    # Detectar tipo de conteúdo e extrair payload
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("multipart/"):
        try:
            plan_data = json.loads(data or "{}")
        except Exception:
            raise HTTPException(status_code=400, detail="Campo 'data' inválido no multipart")
    else:
        try:
            plan_data = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="JSON inválido no corpo da requisição")

    # Extrair ações e materiais
    actions_data = plan_data.pop('actions', []) or []
    materials_data = plan_data.pop('materials', []) or []

    # Validações mínimas
    if not plan_data.get("name") or not plan_data.get("equipment_id"):
        raise HTTPException(status_code=400, detail="'name' e 'equipment_id' são obrigatórios")

    # Criar plano
    db_plan = MaintenancePlan(**plan_data)
    db.add(db_plan)
    db.flush()  # obter id

    # Ações
    from app.models.maintenance import MaintenancePlanAction
    for action_data in actions_data:
        desc = (action_data.get('description') or '').strip()
        if not desc:
            continue
        db_action = MaintenancePlanAction(
            plan_id=db_plan.id,
            description=desc,
            action_type=action_data.get('action_type') or 'Inspeção'
        )
        db.add(db_action)

    # Materiais com validação
    from app.models.maintenance import MaintenancePlanMaterial
    from app.models.warehouse import Material
    for m in materials_data:
        mat_id = m.get('material_id')
        qty = m.get('quantity')
        unit = m.get('unit') or 'un'
        if not mat_id:
            raise HTTPException(status_code=400, detail="Material sem 'material_id'")
        try:
            qty = float(qty)
        except Exception:
            raise HTTPException(status_code=400, detail=f"Quantidade inválida para material {mat_id}")
        if qty <= 0:
            raise HTTPException(status_code=400, detail=f"Quantidade inválida para material {mat_id}")
        mat = db.query(Material).filter(Material.id == mat_id).first()
        if not mat:
            raise HTTPException(status_code=400, detail=f"Material id {mat_id} não encontrado")
        db.add(MaintenancePlanMaterial(
            plan_id=db_plan.id,
            material_id=mat_id,
            quantity=qty,
            unit=unit
        ))

    # Persistir alterações do plano, ações e materiais
    db.commit()
    db.refresh(db_plan)

    # Salvar documentos, se enviados
    saved_files = []
    if content_type.startswith("multipart/") and documents:
        base_dir = os.path.join("data", "plan_documents", str(db_plan.id))
        os.makedirs(base_dir, exist_ok=True)
        for uf in documents:
            if not uf or not uf.filename:
                continue
            safe_name = os.path.basename(uf.filename.replace("\r", "").replace("\n", "").strip())
            if not safe_name:
                continue
            dest = os.path.join(base_dir, safe_name)
            try:
                content = await uf.read()
                with open(dest, "wb") as f:
                    f.write(content)
                saved_files.append(safe_name)
            except Exception as e:
                print(f"Falha ao salvar documento do plano {db_plan.id}: {e}")

    return {"id": db_plan.id, "name": db_plan.name, "documents_saved": saved_files}

@router.get("/plans/{plan_id}/documents")
async def list_plan_documents(plan_id: int):
    base_dir = os.path.join("data", "plan_documents", str(plan_id))
    if not os.path.isdir(base_dir):
        return []
    files = []
    for fname in os.listdir(base_dir):
        fpath = os.path.join(base_dir, fname)
        if os.path.isfile(fpath):
            files.append({
                "filename": fname,
                "url": f"/maintenance/plans/{plan_id}/documents/{fname}"
            })
    return files

@router.get("/plans/{plan_id}/documents/{filename}")
async def get_plan_document(plan_id: int, filename: str):
    safe_name = os.path.basename(filename)
    base_dir = os.path.join("data", "plan_documents", str(plan_id))
    file_path = os.path.join(base_dir, safe_name)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    return FileResponse(file_path, filename=safe_name)

@router.get("/api/plans/{plan_id}")
async def get_maintenance_plan(plan_id: int, db: Session = Depends(get_db)):
    """Obter plano de manutenção específico"""
    plan = db.query(MaintenancePlan).filter(MaintenancePlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plano de manutenção não encontrado")
    
    # Obter equipamento relacionado
    equipment = db.query(Equipment).filter(Equipment.id == plan.equipment_id).first()
    equipment_name = equipment.name if equipment else "N/A"
    equipment_prefix = equipment.prefix if equipment else "N/A"
    
    # Carregar ações e materiais relacionados
    # Importações locais para evitar ciclos em importação
    from app.models.maintenance import MaintenancePlanAction, MaintenancePlanMaterial
    from app.models.warehouse import Material
    
    actions = (
        db.query(MaintenancePlanAction)
        .filter(MaintenancePlanAction.plan_id == plan.id)
        .order_by(MaintenancePlanAction.sequence_order.asc(), MaintenancePlanAction.id.asc())
        .all()
    )
    actions_payload = [
        {
            "id": a.id,
            "description": a.description,
            "action_type": a.action_type,
            "sequence_order": a.sequence_order,
            "estimated_time_minutes": a.estimated_time_minutes,
            "requires_specialist": a.requires_specialist,
            "safety_notes": a.safety_notes,
        }
        for a in actions
    ]
    
    plan_materials = (
        db.query(MaintenancePlanMaterial)
        .filter(MaintenancePlanMaterial.plan_id == plan.id)
        .all()
    )
    materials_payload = []
    for pm in plan_materials:
        mat = db.query(Material).filter(Material.id == pm.material_id).first()
        materials_payload.append(
            {
                "id": pm.id,
                "material_id": pm.material_id,
                "material_name": mat.name if mat else None,
                "quantity": pm.quantity,
                "unit": pm.unit,
                "is_critical": pm.is_critical,
            }
        )
    
    # Retornar dados completos do plano com informações do equipamento
    plan_data = {
        "id": plan.id,
        "name": plan.name,
        "type": plan.type,
        "interval_type": plan.interval_type,
        "interval_value": plan.interval_value,
        "equipment_id": plan.equipment_id,
        "equipment_name": equipment_name,
        "equipment_prefix": equipment_prefix,
        "priority": plan.priority,
        "estimated_hours": plan.estimated_hours,
        "is_active": plan.is_active,
        "description": plan.description,
        "created_at": plan.created_at.isoformat() if plan.created_at else None,
        "updated_at": plan.updated_at.isoformat() if plan.updated_at else None,
        # Incluir ações e materiais
        "actions": actions_payload,
        "materials": materials_payload,
    }
    
    return plan_data

@router.put("/api/plans/{plan_id}")
async def update_maintenance_plan(
    plan_id: int,
    plan_data: dict,
    db: Session = Depends(get_db)
):
    """Atualizar plano de manutenção"""
    plan = db.query(MaintenancePlan).filter(MaintenancePlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plano de manutenção não encontrado")
    
    for field, value in plan_data.items():
        if hasattr(plan, field):
            setattr(plan, field, value)
    
    plan.updated_at = datetime.now()
    db.commit()
    db.refresh(plan)
    return plan

@router.delete("/plans/{plan_id}")
async def delete_maintenance_plan(plan_id: int, db: Session = Depends(get_db)):
    """Deletar plano de manutenção"""
    plan = db.query(MaintenancePlan).filter(MaintenancePlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plano de manutenção não encontrado")
    
    # Deletar ações e materiais relacionados
    from app.models.maintenance import MaintenancePlanAction, MaintenancePlanMaterial
    db.query(MaintenancePlanAction).filter(MaintenancePlanAction.plan_id == plan_id).delete()
    db.query(MaintenancePlanMaterial).filter(MaintenancePlanMaterial.plan_id == plan_id).delete()
    
    # Deletar o plano
    db.delete(plan)
    db.commit()
    
    return {"message": "Plano de manutenção deletado com sucesso"}

# API Endpoints - Preventive Maintenance Detection

@router.get("/alerts")
async def get_maintenance_alerts(db: Session = Depends(get_db)):
    """Detectar equipamentos que precisam de manutenção preventiva"""
    alerts = []
    
    # Buscar todos os planos ativos
    active_plans = db.query(MaintenancePlan).filter(MaintenancePlan.is_active == True).all()
    
    for plan in active_plans:
        equipment = db.query(Equipment).filter(Equipment.id == plan.equipment_id).first()
        if not equipment:
            continue
            
        # TEMPORARIAMENTE SIMPLIFICADO - SEM HORÍMETRO
        # Criar um alerta de exemplo para demonstração
        if plan.interval_type in ["Horímetro", "Horas"]:
            alert = {
                "id": f"{plan.id}_{equipment.id}",
                "equipment_id": equipment.id,
                "equipment_name": equipment.name,
                "equipment_prefix": equipment.prefix,
                "plan_id": plan.id,
                "plan_name": plan.name,
                "alert_type": "Previsto",  # Alerta de exemplo
                "message": "Manutenção preventiva programada (sistema simplificado)",
                "priority": plan.priority,
                "estimated_hours": plan.estimated_hours
            }
            alerts.append(alert)
    
    # Ordenar por criticidade
    priority_order = {"Vencido": 0, "Crítico": 1, "Previsto": 2}
    alerts.sort(key=lambda x: priority_order.get(x["alert_type"], 3))
    
    return alerts

@router.post("/generate-work-order")
async def generate_work_order_from_plan(request_data: dict, db: Session = Depends(get_db)):
    """Gerar ordem de serviço a partir de um plano de manutenção"""
    plan_id = request_data.get("plan_id")
    equipment_id = request_data.get("equipment_id")
    
    plan = db.query(MaintenancePlan).filter(MaintenancePlan.id == plan_id).first()
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    
    if not plan or not equipment:
        raise HTTPException(status_code=404, detail="Plano ou equipamento não encontrado")
    
    # Gerar número sequencial para a OS
    last_os = db.query(WorkOrder).order_by(WorkOrder.id.desc()).first()
    if last_os:
        last_number = int(last_os.number)
        new_number = str(last_number + 1)
    else:
        new_number = "100000"
    
    # Criar ordem de serviço
    work_order = WorkOrder(
        number=new_number,
        title=f"Manutenção Preventiva - {plan.name}",
        description=f"Manutenção preventiva baseada no plano: {plan.name}\n\nDescrição do plano: {plan.description or 'N/A'}",
        priority=plan.priority,
        type="Preventiva",
        status="Aberta",
        equipment_id=equipment_id,
        estimated_hours=plan.estimated_hours,
        due_date=datetime.now() + timedelta(days=7)  # Prazo de 7 dias
    )
    
    db.add(work_order)
    db.flush()  # Para obter o ID da OS

    # Criar notificação de estoque para materiais do plano
    try:
        from app.models.warehouse import StockNotification, StockNotificationItem, Material
        stock_notification = StockNotification(
            work_order_id=work_order.id,
            equipment_id=equipment.id,
            maintenance_plan_id=plan.id,
            priority=plan.priority,
            message=f"Solicitação automática de materiais para manutenção preventiva - {equipment.name} ({equipment.prefix}). OS: {work_order.number}",
            status="Pendente",
            created_at=datetime.now()
        )
        db.add(stock_notification)
        db.commit()
        db.refresh(stock_notification)

        # Adicionar itens necessários conforme o plano
        if getattr(plan, "plan_materials", None):
            for plan_material in plan.plan_materials:
                material = db.query(Material).filter(Material.id == plan_material.material_id).first()
                if material:
                    notification_item = StockNotificationItem(
                        notification_id=stock_notification.id,
                        material_id=material.id,
                        quantity_needed=plan_material.quantity,
                        quantity_available=material.current_stock,
                    )
                    db.add(notification_item)
    except Exception:
        # Não bloquear criação da OS por falha na notificação de estoque
        pass
    
    # Atualizar o plano com a data da última execução
    # TEMPORARIAMENTE DESABILITADO - SEM HORÍMETRO
    # plan.last_execution_horimeter = equipment.current_horimeter
    plan.last_execution_date = datetime.now()
    
    # Calcular próxima execução
    # TEMPORARIAMENTE DESABILITADO - SEM HORÍMETRO
    # if plan.interval_type == "Horas":
    #     plan.next_execution_horimeter = equipment.current_horimeter + plan.interval_value
    
    db.commit()
    db.refresh(work_order)
    
    return {
        "message": "Ordem de serviço gerada com sucesso",
        "work_order": {
            "id": work_order.id,
            "number": work_order.number,
            "title": work_order.title,
            "status": work_order.status
        }
     }

# API Endpoints - Filter Options

@router.get("/filter-options")
async def get_filter_options(db: Session = Depends(get_db)):
    """Obter opções para filtros"""
    try:
        # Buscar equipamentos
        equipments = db.query(Equipment).all()
        equipment_options = [{"id": eq.id, "name": eq.name} for eq in equipments]
        
        # Buscar técnicos (usuários que já executaram manutenções)
        technicians = db.query(WorkOrder.assigned_to).filter(
            WorkOrder.assigned_to.isnot(None)
        ).distinct().all()
        technician_options = [{"name": tech[0]} for tech in technicians if tech[0]]
        
        return {
            "equipments": equipment_options,
            "technicians": technician_options,
            "types": [
                {"value": "preventive", "label": "Preventiva"},
                {"value": "corrective", "label": "Corretiva"},
                {"value": "emergency", "label": "Emergencial"}
            ],
            "priorities": [
                {"value": "low", "label": "Baixa"},
                {"value": "medium", "label": "Média"},
                {"value": "high", "label": "Alta"},
                {"value": "critical", "label": "Crítica"}
            ]
        }
    except Exception as e:
        print(f"Erro ao buscar opções de filtro: {e}")
        return {
            "equipments": [],
            "technicians": [],
            "types": [],
            "priorities": []
        }

# API Endpoints - Schedules Management

@router.get("/api/schedules")
async def get_maintenance_schedules(db: Session = Depends(get_db)):
    """Obter cronogramas de manutenção"""
    try:
        schedules = db.query(MaintenancePlan).filter(
            MaintenancePlan.is_active == True
        ).all()
        
        schedules_data = []
        for schedule in schedules:
            equipment = db.query(Equipment).filter(Equipment.id == schedule.equipment_id).first()
            
            schedules_data.append({
                "id": schedule.id,
                "equipment_id": schedule.equipment_id,
                "equipment_name": equipment.name if equipment else "N/A",
                "maintenance_type": schedule.maintenance_type,
                "description": schedule.description,
                "frequency": f"{schedule.horimeter_interval}h" if schedule.horimeter_interval else f"{schedule.time_interval_days}d",
                "status": "Ativo" if schedule.is_active else "Inativo",
                "next_execution": "A calcular",  # Será calculado baseado no último histórico
                "created_at": schedule.created_at.strftime("%d/%m/%Y") if schedule.created_at else ""
            })
        
        return {
            "schedules": schedules_data,
            "total": len(schedules_data)
        }
    except Exception as e:
        print(f"Erro ao buscar cronogramas: {e}")
        return {
            "schedules": [],
            "total": 0
        }

# API Endpoints - Weekly Hours Management

@router.get("/api/equipment/{equipment_id}/weekly-hours")
async def get_weekly_hours(equipment_id: int, week: str, db: Session = Depends(get_db)):
    """Obter horas semanais de um equipamento"""
    weekly_hours = db.query(WeeklyHours).filter(
        WeeklyHours.equipment_id == equipment_id,
        WeeklyHours.week == week
    ).first()
    
    if not weekly_hours:
        # Retornar estrutura vazia se não houver dados
        return {
            "equipment_id": equipment_id,
            "week": week,
            "monday": 0,
            "tuesday": 0,
            "wednesday": 0,
            "thursday": 0,
            "friday": 0,
            "saturday": 0,
            "sunday": 0,
            "total_hours": 0
        }
    
    return {
        "equipment_id": weekly_hours.equipment_id,
        "week": weekly_hours.week,
        "monday": weekly_hours.monday,
        "tuesday": weekly_hours.tuesday,
        "wednesday": weekly_hours.wednesday,
        "thursday": weekly_hours.thursday,
        "friday": weekly_hours.friday,
        "saturday": weekly_hours.saturday,
        "sunday": weekly_hours.sunday,
        "total_hours": weekly_hours.total_hours
    }

@router.post("/api/equipment/weekly-hours")
async def save_weekly_hours(request_data: dict, db: Session = Depends(get_db)):
    """Salvar horas semanais de um equipamento"""
    equipment_id = request_data.get("equipment_id")
    week = request_data.get("week")
    
    if not equipment_id or not week:
        raise HTTPException(status_code=400, detail="equipment_id e week são obrigatórios")
    
    # Verificar se o equipamento existe
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipamento não encontrado")
    
    # Calcular total de horas
    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    total_hours = sum(float(request_data.get(day, 0)) for day in days)
    
    # Verificar se já existe registro para esta semana
    existing = db.query(WeeklyHours).filter(
        WeeklyHours.equipment_id == equipment_id,
        WeeklyHours.week == week
    ).first()
    
    if existing:
        # Atualizar registro existente
        for day in days:
            setattr(existing, day, float(request_data.get(day, 0)))
        existing.total_hours = total_hours
        existing.updated_at = datetime.now()
        
        db.commit()
        db.refresh(existing)
        
        return {
            "message": "Horas semanais atualizadas com sucesso",
            "weekly_hours": existing
        }
    else:
        # Criar novo registro
        weekly_hours_data = {
            "equipment_id": equipment_id,
            "week": week,
            "total_hours": total_hours
        }
        
        for day in days:
            weekly_hours_data[day] = float(request_data.get(day, 0))
        
        weekly_hours = WeeklyHours(**weekly_hours_data)
        db.add(weekly_hours)
        db.commit()
        db.refresh(weekly_hours)
        
        return {
            "message": "Horas semanais salvas com sucesso",
            "weekly_hours": weekly_hours
        }

@router.post("/api/equipment/{equipment_id}/update-horimeter")
async def update_equipment_horimeter_from_hours(
    equipment_id: int,
    request_data: dict,
    db: Session = Depends(get_db)
):
    """Atualizar horímetro do equipamento baseado nas horas trabalhadas"""
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipamento não encontrado")
    
    # TEMPORARIAMENTE DESABILITADO - SEM HORÍMETRO
    return {"message": "Funcionalidade de horímetro temporariamente desabilitada"}
    
    # additional_hours = request_data.get("additional_hours", 0)
    # description = request_data.get("description", "Atualização automática")
    # 
    # if additional_hours <= 0:
    #     return {"message": "Nenhuma hora adicional para atualizar"}
    # 
    # # Calcular novo horímetro
    # new_horimeter = equipment.current_horimeter + additional_hours
    # 
    # # Criar log do horímetro
    # from app.models.equipment import HorimeterLog
    # log = HorimeterLog(
    #     equipment_id=equipment_id,
    #     previous_value=equipment.current_horimeter,
    #     new_value=new_horimeter,
    #     difference=additional_hours,
    #     recorded_by="Sistema",
    #     notes=description
    # )
    # db.add(log)
    # 
    # # Atualizar equipamento
    # equipment.current_horimeter = new_horimeter
    # equipment.last_horimeter_update = datetime.now()
    # 
    # db.commit()
    # db.refresh(equipment)
    # 
    # return {
    #     "message": "Horímetro atualizado com sucesso",
    #     "previous_horimeter": equipment.current_horimeter - additional_hours,
    #     "new_horimeter": equipment.current_horimeter,
    #     "additional_hours": additional_hours
    #  }

# API Endpoints - Preventive Maintenance Detection

@router.get("/preventive-alerts")
async def get_preventive_maintenance_alerts(db: Session = Depends(get_db)):
    """Detectar manutenções preventivas vencidas ou próximas do vencimento"""
    try:
        alerts = []
        
        # Buscar todos os planos de manutenção ativos
        maintenance_plans = db.query(MaintenancePlan).all()
        
        current_date = datetime.now()
        
        for plan in maintenance_plans:
            equipment = db.query(Equipment).filter(Equipment.id == plan.equipment_id).first()
            if not equipment:
                continue
            
            # Verificar se já existe uma OS aberta para este equipamento e tipo de manutenção
            existing_wo = db.query(WorkOrder).filter(
                and_(
                    WorkOrder.equipment_id == plan.equipment_id,
                    WorkOrder.type == "Preventiva",
                    WorkOrder.status.in_(["Aberta", "Em andamento"])
                )
            ).first()
            
            alert_data = {
                "plan_id": plan.id,
                "equipment_id": plan.equipment_id,
                "equipment_name": equipment.name,
                "maintenance_type": plan.type,
                "description": plan.description,
                "priority": "high",
                "alert_type": "",
                "message": "",
                "overdue_amount": 0,
                "next_due": None,
                "existing_work_order": existing_wo.number if existing_wo else None,
                "existing_work_order_id": existing_wo.id if existing_wo else None
            }
            
            # Verificar manutenção baseada em horímetro
            if (plan.interval_type or "").lower() in ["horímetro", "horimetro", "horas"] and plan.interval_value and plan.interval_value > 0:
                # Calcular horas trabalhadas desde a mobilização
                if equipment.initial_horimeter is not None and equipment.current_horimeter is not None:
                    hours_worked = equipment.current_horimeter - equipment.initial_horimeter
                    
                    # Calcular quantos ciclos de manutenção já foram completados
                    cycles_completed = int(hours_worked // plan.interval_value)
                    next_maintenance_hours = (cycles_completed + 1) * plan.interval_value
                    hours_until_maintenance = next_maintenance_hours - hours_worked
                    
                    # Verificar se atingiu 90% do intervalo (notificação de alerta)
                    ninety_percent_threshold = next_maintenance_hours - (plan.interval_value * 0.1)
                    
                    if hours_worked >= next_maintenance_hours:
                        # Manutenção vencida
                        hours_overdue = hours_worked - next_maintenance_hours
                        alert_data["alert_type"] = "overdue"
                        alert_data["priority"] = "high"
                        
                        # Criar mensagem com informações da OS existente se houver
                        if existing_wo:
                            alert_data["message"] = f"Manutenção vencida há {hours_overdue:.1f} horas - OS nº {existing_wo.number} - Plano de {plan.interval_value} horas"
                        else:
                            alert_data["message"] = f"Manutenção vencida há {hours_overdue:.1f} horas"
                        
                        alert_data["overdue_amount"] = hours_overdue
                        alerts.append(alert_data.copy())
                    elif hours_worked >= ninety_percent_threshold:
                        # Manutenção próxima (90% atingido)
                        alert_data["alert_type"] = "upcoming"
                        alert_data["priority"] = "medium"
                        
                        # Criar mensagem com informações da OS existente se houver
                        if existing_wo:
                            alert_data["message"] = f"Manutenção em {hours_until_maintenance:.1f} horas (90% atingido) - OS nº {existing_wo.number} - Plano de {plan.interval_value} horas"
                        else:
                            alert_data["message"] = f"Manutenção em {hours_until_maintenance:.1f} horas (90% atingido)"
                        
                        alert_data["next_due"] = f"{next_maintenance_hours:.1f}h"
                        alerts.append(alert_data.copy())
        
        # Verificar manutenção baseada em tempo
        if plan.interval_type == "Tempo" and plan.interval_value and plan.interval_value > 0:
            # Calcular próxima manutenção baseada no tempo
            last_maintenance = db.query(WorkOrder).filter(
                and_(
                    WorkOrder.equipment_id == plan.equipment_id,
                    WorkOrder.type == "Preventiva",
                    WorkOrder.status == "Fechada"
                )
            ).order_by(WorkOrder.completed_at.desc()).first()
            
            if last_maintenance and last_maintenance.completed_at:
                from datetime import timedelta
                next_date = last_maintenance.completed_at + timedelta(days=plan.interval_value)
            else:
                # Se não há manutenção anterior, usar data de criação do plano ou data atual
                from datetime import timedelta
                base_date = plan.created_at if plan.created_at else current_date
                next_date = base_date + timedelta(days=plan.interval_value)
            
            days_diff = (current_date - next_date).days
            
            if days_diff >= 0:
                # Manutenção vencida
                alert_data["alert_type"] = "overdue"
                alert_data["priority"] = "high"
                
                # Criar mensagem com informações da OS existente se houver
                if existing_wo:
                    alert_data["message"] = f"Manutenção vencida há {days_diff} dias - OS nº {existing_wo.number} - Plano de {plan.interval_value} dias"
                else:
                    alert_data["message"] = f"Manutenção vencida há {days_diff} dias"
                
                alert_data["overdue_amount"] = days_diff
                alerts.append(alert_data.copy())
            elif days_diff >= -7:  # Próxima em até 7 dias
                # Manutenção próxima
                alert_data["alert_type"] = "upcoming"
                alert_data["priority"] = "medium"
                
                # Criar mensagem com informações da OS existente se houver
                if existing_wo:
                    alert_data["message"] = f"Manutenção em {abs(days_diff)} dias - OS nº {existing_wo.number} - Plano de {plan.interval_value} dias"
                else:
                    alert_data["message"] = f"Manutenção em {abs(days_diff)} dias"
                
                alert_data["next_due"] = next_date.strftime("%d/%m/%Y")
                alerts.append(alert_data.copy())
    
        # Ordenar alertas por prioridade (vencidas primeiro)
        alerts.sort(key=lambda x: (x["alert_type"] != "overdue", x.get("overdue_amount", 0)), reverse=True)
        
        return {
            "alerts": alerts,
            "total_alerts": len(alerts),
            "overdue_count": len([a for a in alerts if a["alert_type"] == "overdue"]),
            "upcoming_count": len([a for a in alerts if a["alert_type"] == "upcoming"])
        }
    except Exception as e:
        return {
            "alerts": [],
            "total_alerts": 0,
            "overdue_count": 0,
            "upcoming_count": 0,
            "error": str(e)
        }

@router.post("/generate-work-order-from-alert")
async def generate_work_order_from_alert(request_data: dict, db: Session = Depends(get_db)):
    """Gerar ordem de serviço a partir de um alerta de manutenção preventiva"""
    plan_id = request_data.get("plan_id")
    
    if not plan_id:
        raise HTTPException(status_code=400, detail="plan_id é obrigatório")
    
    # Buscar plano de manutenção
    plan = db.query(MaintenancePlan).filter(MaintenancePlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plano de manutenção não encontrado")
    
    # Buscar equipamento
    equipment = db.query(Equipment).filter(Equipment.id == plan.equipment_id).first()
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipamento não encontrado")
    
    # Verificar se já existe uma OS aberta para este equipamento
    existing_wo = db.query(WorkOrder).filter(
        and_(
            WorkOrder.equipment_id == plan.equipment_id,
            WorkOrder.type == "Preventiva",
            WorkOrder.status.in_(["Aberta", "Em andamento"])
        )
    ).first()
    
    if existing_wo:
        return {
            "message": "Já existe uma ordem de serviço aberta para este plano",
            "work_order_id": existing_wo.id
        }
    
    # Gerar número da ordem de serviço
    last_work_order = db.query(WorkOrder).order_by(WorkOrder.id.desc()).first()
    if last_work_order and last_work_order.number:
        try:
            last_number = int(last_work_order.number)
            new_number = str(last_number + 1)
        except ValueError:
            new_number = "100000"
    else:
        new_number = "100000"
    
    # Criar nova ordem de serviço
    work_order_data = {
        "number": new_number,
        "title": f"Manutenção Preventiva - {equipment.name}",
        "description": plan.description or f"Manutenção preventiva conforme plano: {plan.type}",
        "equipment_id": plan.equipment_id,
        "priority": "Média",
        "type": "Preventiva",
        "status": "Aberta",
        "estimated_hours": plan.estimated_hours or 2,
        # "horimeter_at_creation": equipment.current_horimeter  # TEMPORARIAMENTE DESABILITADO
    }
    
    work_order = WorkOrder(**work_order_data)
    db.add(work_order)
    db.commit()
    db.refresh(work_order)

    # Criar notificação de estoque com materiais do plano vinculado
    try:
        from app.models.warehouse import StockNotification, StockNotificationItem, Material
        stock_notification = StockNotification(
            work_order_id=work_order.id,
            equipment_id=equipment.id,
            maintenance_plan_id=plan.id,
            priority=plan.priority,
            message=f"Materiais necessários para preventiva gerada via alerta - {equipment.name} ({equipment.prefix}). OS: {work_order.number}",
            status="Pendente",
            created_at=datetime.now()
        )
        db.add(stock_notification)
        db.commit()
        db.refresh(stock_notification)

        # Adicionar itens da notificação baseados nos materiais do plano
        if getattr(plan, "plan_materials", None):
            for pm in plan.plan_materials:
                material = db.query(Material).filter(Material.id == pm.material_id).first()
                if material:
                    item = StockNotificationItem(
                        notification_id=stock_notification.id,
                        material_id=material.id,
                        quantity_needed=pm.quantity,
                        quantity_available=material.current_stock,
                    )
                    db.add(item)
        db.commit()
    except Exception:
        # Não bloquear criação da OS por falha na notificação de estoque
        pass

    return {
        "message": "Ordem de serviço gerada com sucesso",
        "work_order_id": work_order.id,
        "work_order": {
            "id": work_order.id,
            "title": work_order.title,
            "description": work_order.description,
            "priority": work_order.priority,
            "status": work_order.status,
            "equipment_name": equipment.name
        }
    }

@router.delete("/equipment/{equipment_id}")
async def delete_equipment(equipment_id: int, db: Session = Depends(get_db)):
    """Excluir um equipamento"""
    # Verificar se o equipamento existe
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipamento não encontrado")
    
    # Verificar se há ordens de serviço associadas
    work_orders = db.query(WorkOrder).filter(WorkOrder.equipment_id == equipment_id).first()
    if work_orders:
        raise HTTPException(
            status_code=400, 
            detail="Não é possível excluir equipamento com ordens de serviço associadas"
        )
    
    # Verificar se há planos de manutenção associados
    maintenance_plans = db.query(MaintenancePlan).filter(MaintenancePlan.equipment_id == equipment_id).first()
    if maintenance_plans:
        raise HTTPException(
            status_code=400, 
            detail="Não é possível excluir equipamento com planos de manutenção associados"
        )

    # Verificar se há registros de abastecimento associados
    fueling = db.query(Fueling).filter(Fueling.equipment_id == equipment_id).first()
    if fueling:
        raise HTTPException(
            status_code=400,
            detail="Não é possível excluir equipamento com registros de abastecimento associados"
        )

    # Verificar se há logs de horímetro associados
    horimeter_log = db.query(HorimeterLog).filter(HorimeterLog.equipment_id == equipment_id).first()
    if horimeter_log:
        raise HTTPException(
            status_code=400,
            detail="Não é possível excluir equipamento com registros de horímetro associados"
        )
    
    # Excluir registros de horas semanais associados e perfil técnico
    try:
        # Remover perfil técnico vinculado (evita tentativa de setar FK para NULL)
        profile = db.query(EquipmentTechnicalProfile).filter(EquipmentTechnicalProfile.equipment_id == equipment_id).first()
        if profile:
            db.delete(profile)
            db.flush()

        # Remover horas semanais
        db.query(WeeklyHours).filter(WeeklyHours.equipment_id == equipment_id).delete()

        # Excluir o equipamento
        db.delete(equipment)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao excluir equipamento: {str(e)}")
    
    return {"message": "Equipamento excluído com sucesso"}

# ==================== ROTAS PARA MÃO DE OBRA ====================

@router.get("/labor")
async def labor_page(request: Request, db: Session = Depends(get_db)):
    """Página de mão de obra"""
    user, redirect = ensure_maintenance_access(request, db)
    if redirect:
        return redirect
    return templates.TemplateResponse("maintenance/labor.html", {"request": request})

@router.get("/api/technicians")
async def get_technicians(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """Listar técnicos"""
    try:
        query = db.query(Technician)
        
        if active_only:
            query = query.filter(Technician.is_active == True)
        
        technicians = query.offset(skip).limit(limit).all()
        
        return [{
            "id": tech.id,
            "name": tech.name,
            "function": tech.function,
            "hourly_rate": float(tech.hourly_rate),
            "hr_matricula": tech.hr_matricula,
            "phone": tech.phone,
            "email": tech.email,
            "specialties": tech.specialties,
            "is_active": tech.is_active,
            "created_at": tech.created_at.isoformat() if tech.created_at else None,
            "updated_at": tech.updated_at.isoformat() if tech.updated_at else None
        } for tech in technicians]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar técnicos: {str(e)}")

@router.post("/api/technicians")
async def create_technician(technician: TechnicianCreate, db: Session = Depends(get_db)):
    """Criar novo técnico"""
    try:
        db_technician = Technician(
            name=technician.name,
            function=technician.function,
            hourly_rate=technician.hourly_rate,
            hr_matricula=technician.hr_matricula,
            phone=technician.phone,
            email=technician.email,
            specialties=technician.specialties
        )
        
        db.add(db_technician)
        db.commit()
        db.refresh(db_technician)
        
        return {
            "id": db_technician.id,
            "name": db_technician.name,
            "function": db_technician.function,
            "hourly_rate": float(db_technician.hourly_rate),
            "hr_matricula": db_technician.hr_matricula,
            "phone": db_technician.phone,
            "email": db_technician.email,
            "specialties": db_technician.specialties,
            "is_active": db_technician.is_active,
            "created_at": db_technician.created_at.isoformat(),
            "updated_at": db_technician.updated_at.isoformat()
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao criar técnico: {str(e)}")

@router.get("/api/technicians/active")
async def get_active_technicians(db: Session = Depends(get_db)):
    """Listar técnicos ativos"""
    try:
        technicians = db.query(Technician).filter(Technician.is_active == True).all()
        return [{
            "id": tech.id,
            "name": tech.name,
            "function": tech.function,
            "hourly_rate": float(tech.hourly_rate)
        } for tech in technicians]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar técnicos ativos: {str(e)}")

@router.get("/api/technicians/{technician_id}")
async def get_technician(technician_id: int, db: Session = Depends(get_db)):
    """Obter técnico por ID"""
    technician = db.query(Technician).filter(Technician.id == technician_id).first()
    if not technician:
        raise HTTPException(status_code=404, detail="Técnico não encontrado")
    
    return {
        "id": technician.id,
        "name": technician.name,
        "function": technician.function,
        "hourly_rate": float(technician.hourly_rate),
        "hr_matricula": technician.hr_matricula,
        "phone": technician.phone,
        "email": technician.email,
        "specialties": technician.specialties,
        "is_active": technician.is_active,
        "created_at": technician.created_at.isoformat(),
        "updated_at": technician.updated_at.isoformat()
    }

@router.put("/api/technicians/{technician_id}")
async def update_technician(
    technician_id: int,
    technician_update: TechnicianUpdate,
    db: Session = Depends(get_db)
):
    """Atualizar técnico"""
    technician = db.query(Technician).filter(Technician.id == technician_id).first()
    if not technician:
        raise HTTPException(status_code=404, detail="Técnico não encontrado")
    
    try:
        # Atualizar apenas os campos fornecidos
        update_data = technician_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(technician, field, value)
        
        technician.updated_at = datetime.now()
        db.commit()
        db.refresh(technician)
        
        return {
            "id": technician.id,
            "name": technician.name,
            "function": technician.function,
            "hourly_rate": float(technician.hourly_rate),
            "hr_matricula": technician.hr_matricula,
            "phone": technician.phone,
            "email": technician.email,
            "specialties": technician.specialties,
            "is_active": technician.is_active,
            "created_at": technician.created_at.isoformat(),
            "updated_at": technician.updated_at.isoformat()
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar técnico: {str(e)}")

@router.delete("/api/technicians/{technician_id}")
async def delete_technician(technician_id: int, db: Session = Depends(get_db)):
    """Excluir técnico"""
    technician = db.query(Technician).filter(Technician.id == technician_id).first()
    if not technician:
        raise HTTPException(status_code=404, detail="Técnico não encontrado")
    
    try:
        # Verificar se há ordens de serviço associadas
        work_orders = db.query(WorkOrder).filter(WorkOrder.technician_id == technician_id).first()
        if work_orders:
            # Em vez de excluir, desativar o técnico
            technician.is_active = False
            technician.updated_at = datetime.now()
            db.commit()
            return {"message": "Técnico desativado com sucesso (possui ordens de serviço associadas)"}
        else:
            # Excluir completamente se não há associações
            db.delete(technician)
            db.commit()
            return {"message": "Técnico excluído com sucesso"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao excluir técnico: {str(e)}")

@router.get("/api/technicians/list/active")
async def get_active_technicians_list(db: Session = Depends(get_db)):
    """Listar técnicos ativos (para uso em selects)"""
    try:
        technicians = db.query(Technician).filter(Technician.is_active == True).all()
        return [{
            "id": tech.id,
            "name": tech.name,
            "function": tech.function,
            "hourly_rate": float(tech.hourly_rate)
        } for tech in technicians]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar técnicos ativos: {str(e)}")


# API Endpoints - Horímetro

@router.get("/equipment/{equipment_id}/horimeter")
async def get_equipment_horimeter_info(equipment_id: int, db: Session = Depends(get_db)):
    """Obter informações do horímetro de um equipamento"""
    from app.models.equipment import Equipment, HorimeterLog
    
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipamento não encontrado")
    
    # Buscar último lançamento de horímetro
    last_log = db.query(HorimeterLog).filter(
        HorimeterLog.equipment_id == equipment_id
    ).order_by(HorimeterLog.recorded_at.desc()).first()
    
    return {
        "equipment_id": equipment.id,
        "equipment_prefix": equipment.prefix,
        "equipment_name": equipment.name,
        "current_horimeter": float(equipment.current_horimeter or 0),
        "initial_horimeter": float(equipment.initial_horimeter or 0),
        "last_horimeter_update": equipment.last_horimeter_update,
        "has_previous_logs": last_log is not None,
        "last_log": {
            "id": last_log.id,
            "previous_value": float(last_log.previous_value),
            "new_value": float(last_log.new_value),
            "difference": float(last_log.difference),
            "recorded_at": last_log.recorded_at,
            "recorded_by": last_log.recorded_by,
            "notes": last_log.notes
        } if last_log else None
    }

@router.post("/equipment/{equipment_id}/horimeter")
async def add_horimeter_entry(equipment_id: int, horimeter_data: dict, db: Session = Depends(get_db)):
    """Adicionar novo lançamento de horímetro"""
    from app.models.equipment import Equipment, HorimeterLog
    
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipamento não encontrado")
    
    try:
        # Validar dados recebidos
        new_value = float(horimeter_data.get("new_value", 0))
        recorded_by = horimeter_data.get("recorded_by", "Sistema")
        notes = horimeter_data.get("notes", "")
        recorded_date = horimeter_data.get("recorded_date")
        
        if recorded_date:
            recorded_at = datetime.fromisoformat(recorded_date.replace('Z', '+00:00'))
        else:
            recorded_at = datetime.now()
        
        # Validar se o novo valor é maior que o atual
        current_value = float(equipment.current_horimeter or 0)
        if new_value <= current_value:
            raise HTTPException(
                status_code=400, 
                detail=f"O novo valor ({new_value}) deve ser maior que o valor atual ({current_value})"
            )
        
        # Calcular diferença
        difference = new_value - current_value
        
        # Criar registro de log
        horimeter_log = HorimeterLog(
            equipment_id=equipment_id,
            previous_value=current_value,
            new_value=new_value,
            difference=difference,
            recorded_by=recorded_by,
            recorded_at=recorded_at,
            notes=notes
        )
        
        # Atualizar equipamento
        equipment.current_horimeter = new_value
        equipment.last_horimeter_update = recorded_at
        equipment.updated_at = datetime.now()
        
        # Salvar no banco
        db.add(horimeter_log)
        db.commit()
        db.refresh(horimeter_log)

        # Verificar e criar manutenção preventiva automática, se aplicável
        maintenance_result = await check_and_create_preventive_maintenance(equipment, db)

        response = {
            "message": "Horímetro lançado com sucesso",
            "log": {
                "id": horimeter_log.id,
                "equipment_id": horimeter_log.equipment_id,
                "previous_value": float(horimeter_log.previous_value),
                "new_value": float(horimeter_log.new_value),
                "difference": float(horimeter_log.difference),
                "recorded_by": horimeter_log.recorded_by,
                "recorded_at": horimeter_log.recorded_at,
                "notes": horimeter_log.notes
            }
        }
        if maintenance_result:
            response["maintenance"] = maintenance_result
            if maintenance_result.get("orders_created", 0) > 0:
                response["message"] += f" {maintenance_result.get('orders_created')} ordem(ns) de manutenção preventiva criada(s)."

        return response
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Valor inválido: {str(e)}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao lançar horímetro: {str(e)}")

@router.get("/equipment/{equipment_id}/horimeter/history")
async def get_horimeter_history(
    equipment_id: int, 
    skip: int = 0, 
    limit: int = 50, 
    db: Session = Depends(get_db)
):
    """Obter histórico de lançamentos de horímetro agregando HorimeterLog, Abastecimentos (Fueling) e Ordens de Serviço (WorkOrder)."""
    from app.models.equipment import Equipment, HorimeterLog
    from app.models.warehouse import Fueling, Material
    from app.models.maintenance import WorkOrder

    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipamento não encontrado")

    # Buscar logs de horímetro (sem paginação, para cálculo correto das diferenças)
    log_entries = db.query(HorimeterLog).filter(
        HorimeterLog.equipment_id == equipment_id
    ).all()

    # Buscar abastecimentos (Fueling) deste equipamento
    fueling_entries = db.query(Fueling).filter(Fueling.equipment_id == equipment_id).all()

    # Buscar ordens de serviço do equipamento
    work_orders = db.query(WorkOrder).filter(WorkOrder.equipment_id == equipment_id).all()

    # Mapa de materiais para enriquecer notas dos abastecimentos
    material_ids = {f.material_id for f in fueling_entries if getattr(f, "material_id", None)}
    materials_map = {}
    if material_ids:
        materials = db.query(Material).filter(Material.id.in_(list(material_ids))).all()
        materials_map = {m.id: m.name for m in materials}

    # Unificar e normalizar os registros em uma linha do tempo
    timeline = []
    for log in log_entries:
        timeline.append({
            "id": log.id,
            "source": "horimeter_log",
            "recorded_at": log.recorded_at,
            "new_value": float(log.new_value or 0),
            "recorded_by": log.recorded_by or "",
            "notes": log.notes or ""
        })
    for f in fueling_entries:
        mat_name = materials_map.get(getattr(f, "material_id", None))
        base_note = "Abastecimento"
        if mat_name:
            base_note += f" de {mat_name}"
        qty = getattr(f, "quantity", None)
        if qty is not None:
            base_note += f" - {qty}"
        combined_notes = base_note
        if getattr(f, "notes", None):
            combined_notes = (combined_notes + " | " + f.notes).strip()
        timeline.append({
            "id": getattr(f, "id", None),
            "source": "fueling",
            "recorded_at": getattr(f, "date", None) or getattr(f, "created_at", None),
            "new_value": float(getattr(f, "horimeter", 0) or 0),
            "recorded_by": getattr(f, "operator", None) or "",
            "notes": combined_notes
        })
    # Incluir ordens de serviço na linha do tempo (não alteram horímetro)
    for wo in work_orders:
        wo_time = getattr(wo, "completed_at", None) or getattr(wo, "started_at", None) or getattr(wo, "created_at", None)
        # Preferência de responsável: assigned_to > technician.name > requested_by
        tech_name = getattr(getattr(wo, "technician", None), "name", None)
        recorded_by = getattr(wo, "assigned_to", None) or tech_name or getattr(wo, "requested_by", None) or ""
        status_info = f"{getattr(wo, 'type', '')} / {getattr(wo, 'priority', '')} / {getattr(wo, 'status', '')}".strip(" / ")
        notes = f"OS {getattr(wo, 'number', '')} - {getattr(wo, 'title', '')}"
        if status_info:
            notes = f"{notes} ({status_info})"
        timeline.append({
            "id": getattr(wo, "id", None),
            "source": "work_order",
            "recorded_at": wo_time,
            # Não há campo de horímetro nas OS; mantemos o valor anterior (ajustado no cálculo abaixo)
            "new_value": None,
            "recorded_by": recorded_by,
            "notes": notes
        })

    # Ordenar cronologicamente (asc) para cálculo da diferença baseada no registro anterior
    timeline.sort(key=lambda x: (x["recorded_at"] or datetime.min))

    # Calcular previous_value e difference baseados no histórico
    previous_value = float(equipment.initial_horimeter or 0)
    for entry in timeline:
        entry["previous_value"] = float(previous_value)
        # Se não houver novo valor (ex.: OS), mantemos o valor anterior
        new_val = entry["new_value"]
        if new_val is None:
            new_val = previous_value
        else:
            try:
                new_val = float(new_val)
            except Exception:
                new_val = previous_value
        entry["new_value"] = float(new_val)
        entry["difference"] = float(new_val - previous_value)
        previous_value = new_val

    # Ordenar para retorno (desc) e aplicar paginação
    timeline.sort(key=lambda x: (x["recorded_at"] or datetime.min), reverse=True)
    total = len(timeline)
    paginated = timeline[skip: skip + limit]

    return {
        "equipment_id": equipment_id,
        "equipment_prefix": equipment.prefix,
        "equipment_name": equipment.name,
        "initial_horimeter": float(equipment.initial_horimeter or 0),
        "current_horimeter": float(equipment.current_horimeter or 0),
        "mobilization_date": equipment.mobilization_date,
        "total_logs": total,
        "logs": [{
            "id": item.get("id"),
            "previous_value": float(item.get("previous_value", 0)),
            "new_value": float(item.get("new_value", 0)),
            "difference": float(item.get("difference", 0)),
            "source": item.get("source"),
            "recorded_by": item.get("recorded_by"),
            "recorded_at": item.get("recorded_at"),
            "notes": item.get("notes", "")
        } for item in paginated]
    }