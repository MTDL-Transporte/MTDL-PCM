"""
Router para relatórios e KPIs
"""

from fastapi import APIRouter, Depends, Request
import httpx
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, extract
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from app.database import get_db
from app.models.maintenance import WorkOrder, TimeLog, WorkOrderMaterial, Technician
from app.models.equipment import Equipment
from app.models.warehouse import (
    Material,
    StockMovement,
    Fueling,
    PurchaseRequest,
    PurchaseRequestItem,
    PurchaseOrder,
    InventoryHistory,
    InventoryHistoryItem
)
from app.templates_config import templates
from app.models.construction import MacroStage, SubStage, Task, TaskMeasurement
from pydantic import BaseModel
import os
from app.services.llm_provider import llm_generate

router = APIRouter()

# Helper para abreviar nomes de categorias nos gráficos
def abbreviate_category(name: Optional[str]) -> str:
    """Converte nomes de categoria longos em abreviações amigáveis para eixo de gráfico.
    Aplica um mapeamento conhecido e faz fallback heurístico quando necessário."""
    if not name:
        return "Sem categoria"
    n = name.strip()
    mapping = {
        "escavadeira hidráulica": "Esc. Hid.",
        "escavadeira hidraulica": "Esc. Hid.",
        "retroescavadeira": "Retro",
        "pá carregadeira": "Pá carr.",
        "pa carregadeira": "Pá carr.",
        "rolo compactador": "Rolo comp.",
        "motoniveladora": "Motoniv.",
        "perfuratriz": "Perfur.",
        "betoneira": "Beton.",
        "usina de asfalto": "Usina asf.",
        "caminhões": "Cam.",
        "caminhoes": "Cam.",
        "tratores": "Trat.",
        "outros": "Outros",
    }
    key = n.lower()
    if key in mapping:
        return mapping[key]
    # Fallback heurístico: remove preposições e abrevia cada palavra
    stop = {"de", "da", "do", "das", "dos", "e"}
    tokens = [t for t in n.split() if t.lower() not in stop]
    if not tokens:
        return n
    if len(tokens) == 1:
        t = tokens[0]
        return (t[:5] + ".") if len(t) > 6 else t
    abbr = []
    for t in tokens:
        ln = 3
        tl = t.lower()
        if tl.startswith("carreg"):
            ln = 4
        elif tl.startswith("compact"):
            ln = 5
        elif tl.startswith("asfalt"):
            ln = 3
        abbr.append(t[:ln] + ".")
    return " ".join(abbr)

@router.get("/")
async def reports_page(request: Request):
    """Página de relatórios"""
    return templates.TemplateResponse("reports/index.html", {"request": request})

@router.get("/maintenance")
async def maintenance_reports(
    request: Request,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Relatórios de manutenção"""
    # Verificar se é uma requisição para HTML ou JSON
    accept_header = request.headers.get("accept", "")
    
    if "text/html" in accept_header:
        # Retornar página HTML (se existir template)
        try:
            return templates.TemplateResponse("reports/maintenance.html", {"request": request})
        except:
            # Se não existir template, retornar dados JSON
            pass
    
    # Retornar dados JSON (API)
    # Métricas básicas de manutenção
    today = datetime.now().date()
    
    # Total de OS
    total_os = db.query(WorkOrder).count()
    
    # OS abertas
    open_os = db.query(WorkOrder).filter(
        WorkOrder.status.in_(["Aberta", "Em andamento"])
    ).count()
    
    # OS fechadas
    closed_os = db.query(WorkOrder).filter(
        WorkOrder.status == "Fechada"
    ).count()
    
    # Custo total
    total_cost = db.query(func.sum(WorkOrder.cost)).scalar() or 0
    
    return {
        "total_work_orders": total_os,
        "open_work_orders": open_os,
        "closed_work_orders": closed_os,
        "total_cost": float(total_cost),
        "period": f"{start_date or 'início'} até {end_date or 'hoje'}"
    }

@router.get("/warehouse")
async def warehouse_reports(
    request: Request,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Relatórios de almoxarifado"""
    # Verificar se é uma requisição para HTML ou JSON
    accept_header = request.headers.get("accept", "")
    
    if "text/html" in accept_header:
        # Retornar página HTML (se existir template)
        try:
            return templates.TemplateResponse("reports/warehouse.html", {"request": request})
        except:
            # Se não existir template, retornar dados JSON
            pass
    
    # Retornar dados JSON (API)
    # Métricas básicas de almoxarifado
    
    # Total de materiais
    total_materials = db.query(Material).count()
    
    # Materiais com estoque baixo (menos de 10 unidades)
    low_stock_materials = db.query(Material).filter(
        Material.current_stock < 10
    ).count()
    
    # Valor total do estoque
    total_stock_value = db.query(
        func.sum(Material.current_stock * Material.average_cost)
    ).scalar() or 0
    
    # Movimentações do mês atual
    today = datetime.now().date()
    first_day_month = today.replace(day=1)
    monthly_movements = db.query(StockMovement).filter(
        StockMovement.date >= first_day_month
    ).count()
    
    return {
        "total_materials": total_materials,
        "low_stock_materials": low_stock_materials,
        "total_stock_value": float(total_stock_value),
        "monthly_movements": monthly_movements,
        "period": f"{start_date or 'início'} até {end_date or 'hoje'}"
    }

# Alias: página de relatórios de almoxarifado em /reports/inventory
@router.get("/inventory")
async def inventory_reports_alias(
    request: Request,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Aponta para o mesmo conteúdo da página de almoxarifado."""
    return await warehouse_reports(request, start_date, end_date, db)

# KPIs de Manutenção
@router.get("/kpis/mttr")
async def get_mttr(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Mean Time To Repair - Tempo médio de reparo"""
    query = db.query(WorkOrder).filter(
        and_(
            WorkOrder.status == "Fechada",
            WorkOrder.completed_at.isnot(None),
            WorkOrder.started_at.isnot(None)
        )
    )
    
    if start_date:
        query = query.filter(WorkOrder.completed_at >= datetime.fromisoformat(start_date))
    if end_date:
        query = query.filter(WorkOrder.completed_at <= datetime.fromisoformat(end_date))
    
    work_orders = query.all()
    
    if not work_orders:
        return {"mttr_hours": 0, "count": 0}
    
    total_time = sum([
        (wo.completed_at - wo.started_at).total_seconds() / 3600
        for wo in work_orders
    ])
    
    mttr = total_time / len(work_orders)
    
    return {
        "mttr_hours": round(mttr, 2),
        "count": len(work_orders),
        "period": f"{start_date or 'início'} até {end_date or 'hoje'}"
    }

@router.get("/kpis/mtbf")
async def get_mtbf(
    equipment_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Mean Time Between Failures - Tempo médio entre falhas"""
    query = db.query(WorkOrder).filter(
        and_(
            WorkOrder.type == "Corretiva",
            WorkOrder.status == "Fechada"
        )
    )
    
    if equipment_id:
        query = query.filter(WorkOrder.equipment_id == equipment_id)
    if start_date:
        query = query.filter(WorkOrder.completed_at >= datetime.fromisoformat(start_date))
    if end_date:
        query = query.filter(WorkOrder.completed_at <= datetime.fromisoformat(end_date))
    
    failures = query.order_by(WorkOrder.completed_at).all()
    
    if len(failures) < 2:
        return {"mtbf_hours": 0, "failures_count": len(failures)}
    
    # Calcular tempo entre falhas
    intervals = []
    for i in range(1, len(failures)):
        interval = (failures[i].completed_at - failures[i-1].completed_at).total_seconds() / 3600
        intervals.append(interval)
    
    mtbf = sum(intervals) / len(intervals) if intervals else 0
    
    return {
        "mtbf_hours": round(mtbf, 2),
        "failures_count": len(failures),
        "equipment_id": equipment_id
    }

@router.get("/maintenance-costs")
async def get_maintenance_costs(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    group_by: str = "month",
    db: Session = Depends(get_db)
):
    """Relatório de custos de manutenção"""
    query = db.query(WorkOrder).filter(WorkOrder.status == "Fechada")
    
    if start_date:
        query = query.filter(WorkOrder.completed_at >= datetime.fromisoformat(start_date))
    if end_date:
        query = query.filter(WorkOrder.completed_at <= datetime.fromisoformat(end_date))
    
    if group_by == "month":
        result = query.with_entities(
            extract('year', WorkOrder.completed_at).label('year'),
            extract('month', WorkOrder.completed_at).label('month'),
            func.sum(WorkOrder.cost).label('total_cost'),
            func.count(WorkOrder.id).label('count')
        ).group_by('year', 'month').all()
        
        return [
            {
                "period": f"{int(row.year)}-{int(row.month):02d}",
                "total_cost": float(row.total_cost or 0),
                "work_orders_count": row.count
            }
            for row in result
        ]
    
    elif group_by == "equipment":
        result = query.join(Equipment).with_entities(
            Equipment.prefix,
            Equipment.name,
            func.sum(WorkOrder.cost).label('total_cost'),
            func.count(WorkOrder.id).label('count')
        ).group_by(Equipment.id).all()
        
        return [
            {
                "equipment": row.prefix,
                "total_cost": float(row.total_cost or 0),
                "work_orders_count": row.count
            }
            for row in result
        ]

@router.get("/maintenance-costs/breakdown")
async def get_maintenance_costs_breakdown(
    equipment: str,
    year: Optional[int] = None,
    month: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Detalhamento de custos de manutenção por equipamento e período.
    Retorna a composição por materiais, mão de obra e outros itens/serviços,
    garantindo que a soma dos subtotais iguala ao custo total das OS fechadas no período.
    """
    import calendar
    # Resolver equipamento pelo prefixo
    eq = db.query(Equipment).filter(Equipment.prefix == equipment).first()
    if not eq:
        return {
            "equipment": equipment,
            "period": "N/A",
            "summary": {"total_cost": 0.0, "materials_total": 0.0, "labor_total": 0.0, "other_total": 0.0},
            "materials": [],
            "labor": [],
            "other_items": []
        }

    # Determinar período
    start_dt = None
    end_dt = None
    period_label = "todos"
    try:
        if year and month:
            start_dt = datetime(year, month, 1)
            last_day = calendar.monthrange(year, month)[1]
            end_dt = datetime(year, month, last_day, 23, 59, 59)
            period_label = f"{year}-{month:02d}"
        elif start_date or end_date:
            if start_date:
                start_dt = datetime.fromisoformat(start_date)
            if end_date:
                # permitir dia completo
                end_dt = datetime.fromisoformat(end_date)
            period_label = f"{start_date or 'início'} até {end_date or 'hoje'}"
    except Exception:
        # Em caso de erro na data, usar período total
        start_dt = None
        end_dt = None
        period_label = "todos"

    # Buscar OS fechadas do equipamento no período
    wo_query = db.query(WorkOrder).filter(
        and_(
            WorkOrder.status == "Fechada",
            WorkOrder.equipment_id == eq.id
        )
    )
    if start_dt:
        wo_query = wo_query.filter(WorkOrder.completed_at >= start_dt)
    if end_dt:
        wo_query = wo_query.filter(WorkOrder.completed_at <= end_dt)
    work_orders = wo_query.all()

    wo_ids = [wo.id for wo in work_orders]
    total_cost = float(sum([wo.cost or 0.0 for wo in work_orders]))

    # Materiais utilizados (via WorkOrderMaterial -> Material)
    materials_rows = []
    materials_total = 0.0
    if wo_ids:
        mat_query = db.query(WorkOrderMaterial, Material, WorkOrder).\
            join(Material, Material.id == WorkOrderMaterial.material_id).\
            join(WorkOrder, WorkOrder.id == WorkOrderMaterial.work_order_id).\
            filter(WorkOrderMaterial.work_order_id.in_(wo_ids))
        # Aplicar janela por data usando completed_at da OS
        if start_dt:
            mat_query = mat_query.filter(WorkOrder.completed_at >= start_dt)
        if end_dt:
            mat_query = mat_query.filter(WorkOrder.completed_at <= end_dt)
        for wom, mat, wo in mat_query.all():
            row_total = float(wom.total_cost or ((wom.unit_cost or 0.0) * (wom.quantity_used or 0.0)))
            materials_total += row_total
            materials_rows.append({
                "work_order_id": wo.id,
                "work_order_number": wo.number,
                "date": wo.completed_at.isoformat() if wo.completed_at else None,
                "material_code": mat.code,
                "material_name": mat.name,
                "unit": mat.unit,
                "quantity": float(wom.quantity_used or 0.0),
                "unit_cost": float(wom.unit_cost or 0.0),
                "total_cost": round(row_total, 2)
            })

    # Mão de obra (TimeLog -> Technician por nome)
    labor_rows = []
    labor_total = 0.0
    if wo_ids:
        tl_query = db.query(TimeLog).filter(TimeLog.work_order_id.in_(wo_ids))
        if start_dt:
            tl_query = tl_query.filter(TimeLog.date >= start_dt)
        if end_dt:
            tl_query = tl_query.filter(TimeLog.date <= end_dt)
        # Mapa de taxa por nome
        techs = db.query(Technician).all()
        rate_by_name = {t.name: float(t.hourly_rate or 0.0) for t in techs}
        for tl in tl_query.all():
            rate = rate_by_name.get(tl.technician, 0.0)
            hours = float(tl.hours_worked or 0.0)
            cost = hours * rate
            labor_total += cost
            labor_rows.append({
                "work_order_id": tl.work_order_id,
                "technician": tl.technician,
                "hours": round(hours, 2),
                "hourly_rate": round(rate, 2),
                "total_cost": round(cost, 2),
                "date": tl.date.isoformat() if tl.date else None
            })

    # Outros itens/serviços (residual para fechar o total)
    other_total = round(total_cost - materials_total - labor_total, 2)
    other_items = []
    if other_total > 0:
        other_items.append({
            "description": "Outros itens/serviços não categorizados",
            "total_cost": other_total
        })

    # Quantidade de combustível no período (somente exibição; não entra no custo total)
    fuel_quantity_total = 0.0
    try:
        fq_query = db.query(func.sum(Fueling.quantity)).filter(Fueling.equipment_id == eq.id)
        if start_dt:
            fq_query = fq_query.filter(Fueling.date >= start_dt)
        if end_dt:
            fq_query = fq_query.filter(Fueling.date <= end_dt)
        fuel_quantity_total = float(fq_query.scalar() or 0.0)
    except Exception:
        fuel_quantity_total = 0.0

    # --- Pendências: OS não fechadas e saídas de materiais não vinculadas a OS fechada ---
    # OS pendentes (Aberta/Em andamento) do equipamento no período (por created_at)
    pending_work_orders_rows = []
    pwo_query = db.query(WorkOrder).filter(
        and_(
            WorkOrder.equipment_id == eq.id,
            WorkOrder.status != "Fechada"
        )
    )
    if start_dt:
        pwo_query = pwo_query.filter(WorkOrder.created_at >= start_dt)
    if end_dt:
        pwo_query = pwo_query.filter(WorkOrder.created_at <= end_dt)
    for pwo in pwo_query.all():
        pending_work_orders_rows.append({
            "work_order_id": pwo.id,
            "work_order_number": pwo.number,
            "title": pwo.title,
            "status": pwo.status,
            "created_at": pwo.created_at.isoformat() if pwo.created_at else None,
            "due_date": pwo.due_date.isoformat() if pwo.due_date else None,
            "cost": float(pwo.cost or 0.0)
        })

    # Movimentações de saída de materiais pendentes: associadas ao equipamento, tipo Saída,
    # e não vinculadas a uma OS fechada (quando reference_document indica uma OS)
    import re
    pending_movements_rows = []
    sm_query = db.query(StockMovement, Material).\
        join(Material, Material.id == StockMovement.material_id).\
        filter(and_(StockMovement.equipment_id == eq.id, StockMovement.type == "Saída"))
    if start_dt:
        sm_query = sm_query.filter(StockMovement.date >= start_dt)
    if end_dt:
        sm_query = sm_query.filter(StockMovement.date <= end_dt)
    for sm, mat in sm_query.all():
        ref = sm.reference_document or ""
        m = re.search(r"OS[-\s]?(\d+)", ref or "")
        linked_wo_closed = False
        if m:
            num = m.group(1)
            wo = db.query(WorkOrder).filter(WorkOrder.number == num).first()
            if wo and wo.status == "Fechada":
                linked_wo_closed = True
        # Considerar pendente se não estiver ligada a OS fechada
        if not linked_wo_closed:
            pending_movements_rows.append({
                "movement_id": sm.id,
                "date": sm.date.isoformat() if sm.date else None,
                "material_code": mat.code,
                "material_name": mat.name,
                "unit": mat.unit,
                "quantity": float(sm.quantity or 0.0),
                "unit_cost": float(sm.unit_cost or 0.0),
                "total_cost": float(sm.total_cost or ((sm.unit_cost or 0.0) * (sm.quantity or 0.0))),
                "reference_document": ref,
                "reason": sm.reason or "",
                "cost_center": sm.cost_center or "",
            })

    return {
        "equipment": eq.prefix,
        "equipment_name": eq.name,
        "period": period_label,
        "summary": {
            "total_cost": round(total_cost, 2),
            "materials_total": round(materials_total, 2),
            "labor_total": round(labor_total, 2),
            "other_total": round(other_total, 2),
            "fuel_quantity": round(fuel_quantity_total, 2)
        },
        "materials": materials_rows,
        "labor": labor_rows,
        "other_items": other_items,
        "pending": {
            "label": "Aguardando finalização",
            "work_orders": pending_work_orders_rows,
            "stock_movements": pending_movements_rows
        }
    }

@router.get("/technician-productivity")
async def get_technician_productivity(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Relatório de produtividade dos técnicos"""
    query = db.query(TimeLog)
    
    if start_date:
        query = query.filter(TimeLog.date >= datetime.fromisoformat(start_date))
    if end_date:
        query = query.filter(TimeLog.date <= datetime.fromisoformat(end_date))
    
    result = query.with_entities(
        TimeLog.technician,
        func.sum(TimeLog.hours_worked).label('total_hours'),
        func.count(func.distinct(TimeLog.work_order_id)).label('work_orders_count'),
        func.avg(TimeLog.hours_worked).label('avg_hours_per_os')
    ).group_by(TimeLog.technician).all()
    
    return [
        {
            "technician": row.technician,
            "total_hours": float(row.total_hours),
            "work_orders_count": row.work_orders_count,
            "avg_hours_per_os": round(float(row.avg_hours_per_os), 2)
        }
        for row in result
    ]

# Relatórios de Almoxarifado
@router.get("/abc-analysis")
async def get_abc_analysis(db: Session = Depends(get_db)):
    """Análise ABC do estoque"""
    # Buscar materiais com valor de estoque
    materials = db.query(Material).filter(Material.is_active == True).all()
    
    # Calcular valor de cada material
    material_values = []
    for material in materials:
        value = material.current_stock * material.average_cost
        material_values.append({
            "id": material.id,
            "code": material.code,
            "name": material.name,
            "stock_value": value,
            "current_stock": material.current_stock,
            "average_cost": material.average_cost
        })
    
    # Ordenar por valor decrescente
    material_values.sort(key=lambda x: x["stock_value"], reverse=True)
    
    # Calcular percentuais acumulados
    total_value = sum(item["stock_value"] for item in material_values)
    accumulated_percentage = 0
    
    for item in material_values:
        percentage = (item["stock_value"] / total_value * 100) if total_value > 0 else 0
        accumulated_percentage += percentage
        
        # Classificar ABC
        if accumulated_percentage <= 80:
            classification = "A"
        elif accumulated_percentage <= 95:
            classification = "B"
        else:
            classification = "C"
        
        item["percentage"] = round(percentage, 2)
        item["accumulated_percentage"] = round(accumulated_percentage, 2)
        item["classification"] = classification
    
    return {
        "total_value": total_value,
        "materials": material_values
    }

@router.get("/stock-turnover")
async def get_stock_turnover(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Relatório de giro de estoque"""
    # Período padrão: últimos 12 meses
    if not start_date:
        start_date = (datetime.now() - timedelta(days=365)).isoformat()
    if not end_date:
        end_date = datetime.now().isoformat()
    
    # Buscar saídas no período
    movements = db.query(StockMovement).filter(
        and_(
            StockMovement.type == "Saída",
            StockMovement.date >= datetime.fromisoformat(start_date),
            StockMovement.date <= datetime.fromisoformat(end_date)
        )
    ).all()
    
    # Agrupar por material
    material_consumption = {}
    for movement in movements:
        material_id = movement.material_id
        if material_id not in material_consumption:
            material_consumption[material_id] = 0
        material_consumption[material_id] += movement.quantity
    
    # Calcular giro para cada material
    turnover_data = []
    for material_id, consumption in material_consumption.items():
        material = db.query(Material).filter(Material.id == material_id).first()
        if material and material.current_stock > 0:
            # Giro = Consumo / Estoque Médio (aproximado pelo estoque atual)
            turnover = consumption / material.current_stock
            
            turnover_data.append({
                "material_code": material.code,
                "material_name": material.name,
                "consumption": consumption,
                "current_stock": material.current_stock,
                "turnover": round(turnover, 2),
                "unit": material.unit
            })
    
    # Ordenar por giro decrescente
    turnover_data.sort(key=lambda x: x["turnover"], reverse=True)
    
    return {
        "period": f"{start_date} até {end_date}",
        "materials": turnover_data
    }

@router.get("/supplier-performance")
async def get_supplier_performance(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Relatório de performance dos fornecedores"""
    from app.models.warehouse import Supplier, PurchaseRequest
    
    query = db.query(PurchaseRequest).filter(
        PurchaseRequest.status.in_(["Aprovada", "Comprada"]) 
    )
    
    if start_date:
        query = query.filter(PurchaseRequest.approved_date >= datetime.fromisoformat(start_date))
    if end_date:
        query = query.filter(PurchaseRequest.approved_date <= datetime.fromisoformat(end_date))
    
    result = query.join(Supplier).with_entities(
        Supplier.name,
        func.count(PurchaseRequest.id).label('orders_count'),
        func.sum(PurchaseRequest.total_value).label('total_value'),
        func.avg(Supplier.rating).label('avg_rating')
    ).group_by(Supplier.id).all()
    
    return [
        {
            "supplier_name": row.name,
            "orders_count": row.orders_count,
            "total_value": float(row.total_value or 0),
            "avg_rating": round(float(row.avg_rating or 0), 2)
        }
        for row in result
    ]

# ------------------------------
# Relatórios de Manutenção - KPIs Avançados e Gráficos
# ------------------------------

@router.get("/availability")
async def get_availability(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    group_by: str = "category",
    db: Session = Depends(get_db)
):
    """Disponibilidade por classe/categoria e média geral.
    Fórmula utilizada: disponibilidade = 1 - (horas de parada / horas totais possíveis no período).
    Horas de parada são aproximadas pela duração das OS corretivas fechadas no período.
    Horas totais possíveis = dias no período * 24."""
    from datetime import date
    from app.models.equipment import Equipment
    
    # Período padrão: últimos 30 dias
    end_dt = datetime.fromisoformat(end_date) if end_date else datetime.now()
    start_dt = datetime.fromisoformat(start_date) if start_date else (end_dt - timedelta(days=30))
    
    total_hours_possible = max(1, ((end_dt.date() - start_dt.date()).days + 1) * 24)
    
    # Downtime por equipamento (OS corretivas fechadas)
    wo_query = db.query(WorkOrder).filter(
        and_(
            WorkOrder.type == "Corretiva",
            WorkOrder.status == "Fechada",
            WorkOrder.started_at.isnot(None),
            WorkOrder.completed_at.isnot(None),
            WorkOrder.completed_at >= start_dt,
            WorkOrder.completed_at <= end_dt
        )
    )
    # Carregar OS e derivar flags/contagem
    work_orders = wo_query.all()
    work_orders_count = len(work_orders)
    has_data = work_orders_count > 0

    equipment_downtime = {}
    for wo in work_orders:
        duration_h = max(0.0, (wo.completed_at - wo.started_at).total_seconds() / 3600)
        equipment_downtime[wo.equipment_id] = equipment_downtime.get(wo.equipment_id, 0.0) + duration_h
    
    # Agrupar por classe/categoria
    equipments = db.query(Equipment).all()
    grouped = {}
    availabilities = []
    
    for eq in equipments:
        downtime = equipment_downtime.get(eq.id, 0.0)
        availability = max(0.0, 1.0 - (downtime / total_hours_possible)) * 100
        availabilities.append(availability)
        label = None
        if group_by == "class":
            label = eq.equipment_class or "Sem classe"
        elif group_by == "category":
            label = abbreviate_category(eq.category) if (eq and eq.category) else "Sem categoria"
        else:
            label = "Geral"
        
        if label not in grouped:
            grouped[label] = []
        grouped[label].append(availability)
    
    grouped_result = [
        {"label": k, "availability_percent": round(sum(v)/len(v), 2) if v else 0}
        for k, v in grouped.items()
    ]
    overall = round(sum(availabilities)/len(availabilities), 2) if availabilities else 0
    
    return {"grouped": grouped_result, "overall": overall, "period_hours": total_hours_possible, "has_data": has_data, "work_orders_count": work_orders_count}

@router.get("/availability/details")
async def get_availability_details(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    group_by: str = "class",
    label: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Detalhamento de disponibilidade por equipamento para uma classe/categoria específica.
    Fórmula: disponibilidade = 1 - (horas de parada / horas totais possíveis no período).
    Horas de parada aproximadas pela duração das OS corretivas fechadas no período.
    """
    from app.models.equipment import Equipment

    # Período padrão: últimos 30 dias
    end_dt = datetime.fromisoformat(end_date) if end_date else datetime.now()
    start_dt = datetime.fromisoformat(start_date) if start_date else (end_dt - timedelta(days=30))
    total_hours_possible = max(1, ((end_dt.date() - start_dt.date()).days + 1) * 24)

    # Downtime por equipamento (OS corretivas fechadas)
    wo_query = db.query(WorkOrder).filter(
        and_(
            WorkOrder.type == "Corretiva",
            WorkOrder.status == "Fechada",
            WorkOrder.started_at.isnot(None),
            WorkOrder.completed_at.isnot(None),
            WorkOrder.completed_at >= start_dt,
            WorkOrder.completed_at <= end_dt
        )
    )
    # Carregar OS e derivar flags/contagem
    work_orders = wo_query.all()
    work_orders_count = len(work_orders)
    has_data = work_orders_count > 0

    equipment_downtime: dict[int, float] = {}
    for wo in work_orders:
        duration_h = max(0.0, (wo.completed_at - wo.started_at).total_seconds() / 3600)
        equipment_downtime[wo.equipment_id] = equipment_downtime.get(wo.equipment_id, 0.0) + duration_h

    # Preparar lista por equipamento e filtrar pelo agrupamento/label solicitado
    items = []
    equipments = db.query(Equipment).all()
    for eq in equipments:
        # Determinar rótulo de agrupamento
        if group_by == "class":
            grp_label = eq.equipment_class or "Sem classe"
        elif group_by == "category":
            grp_label = eq.category or "Sem categoria"
        else:
            grp_label = "Geral"

        # Filtrar pelo label (quando fornecido)
        if label and grp_label != label:
            continue

        downtime = equipment_downtime.get(eq.id, 0.0)
        availability = max(0.0, 1.0 - (downtime / total_hours_possible)) * 100.0
        items.append({
            "equipment_id": eq.id,
            "equipment": f"{eq.name}" if getattr(eq, "name", None) else (getattr(eq, "prefix", None) or f"Eq #{eq.id}"),
            "prefix": getattr(eq, "prefix", None),
            "class": getattr(eq, "equipment_class", None),
            "category": getattr(eq, "category", None),
            "availability_percent": round(float(availability), 2)
        })

    # Ordenar por disponibilidade decrescente para facilitar leitura
    items.sort(key=lambda x: x.get("availability_percent", 0.0), reverse=True)

    return {
        "group_by": group_by,
        "label": label or "",
        "period_hours": total_hours_possible,
        "count": len(items),
        "items": items,
        "has_data": has_data,
        "work_orders_count": work_orders_count
    }

@router.get("/utilization")
async def get_utilization(
    year: Optional[int] = None,
    month: Optional[int] = None,
    week: Optional[str] = None,
    group_by: str = "category",
    db: Session = Depends(get_db)
):
    """Utilização por classe/categoria e média geral.
    Utilização = horas operacionais / capacidade (franquia mensal*meses ou 160h*meses se franquia ausente).
    Horas operacionais obtidas de WeeklyHours."""
    from datetime import date
    from app.models.equipment import Equipment, WeeklyHours
    
    # Carregar horas semanais
    hours_query = db.query(WeeklyHours)
    if week:
        hours_query = hours_query.filter(WeeklyHours.week == week)
    if year:
        hours_query = hours_query.filter(WeeklyHours.week.like(f"{year}-%"))
    hours = hours_query.all()
    has_data = len(hours) > 0
    
    # Filtrar por mês via cálculo do primeiro dia da semana ISO
    def week_month(wh):
        try:
            parts = wh.week.split("-W")
            y = int(parts[0]); w = int(parts[1])
            d = date.fromisocalendar(y, w, 1)
            return d.month
        except:
            return None
    
    if month:
        hours = [h for h in hours if week_month(h) == month]
    
    # Agregar horas por equipamento
    equipment_hours = {}
    for h in hours:
        equipment_hours[h.equipment_id] = equipment_hours.get(h.equipment_id, 0.0) + (h.total_hours or 0.0)
    
    equipments = db.query(Equipment).all()
    grouped = {}
    utilizations = []
    months_count = 1 if month else (12 if year and not week else (0.25 if week else 1))
    base_month_hours = 160.0  # fallback quando não há franquia
    
    for eq in equipments:
        oper_hours = equipment_hours.get(eq.id, 0.0)
        capacity = (eq.monthly_quota or base_month_hours) * months_count
        util = 0.0
        if capacity > 0:
            util = min(100.0, (oper_hours / capacity) * 100.0)
        utilizations.append(util)
        label = None
        if group_by == "class":
            label = eq.equipment_class or "Sem classe"
        elif group_by == "category":
            label = abbreviate_category(eq.category) if (eq and eq.category) else "Sem categoria"
        else:
            label = "Geral"
        if label not in grouped:
            grouped[label] = []
        grouped[label].append(util)
    
    grouped_result = [
        {"label": k, "utilization_percent": round(sum(v)/len(v), 2) if v else 0}
        for k, v in grouped.items()
    ]
    overall = round(sum(utilizations)/len(utilizations), 2) if utilizations else 0
    
    return {"grouped": grouped_result, "overall": overall, "has_data": has_data}

@router.get("/kpis/mttr-grouped")
async def get_mttr_grouped(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    group_by: str = "equipment",
    db: Session = Depends(get_db)
):
    """MTTR agrupado por equipamento ou categoria."""
    from app.models.equipment import Equipment
    query = db.query(WorkOrder).filter(
        and_(
            WorkOrder.status == "Fechada",
            WorkOrder.completed_at.isnot(None),
            WorkOrder.started_at.isnot(None)
        )
    )
    if start_date:
        query = query.filter(WorkOrder.completed_at >= datetime.fromisoformat(start_date))
    if end_date:
        query = query.filter(WorkOrder.completed_at <= datetime.fromisoformat(end_date))
    
    wos = query.all()
    if not wos:
        return {"grouped": [], "overall": 0}
    
    # Mapear equipamento
    equipments_map = {eq.id: eq for eq in db.query(Equipment).all()}
    grouped = {}
    mttrs = []
    for wo in wos:
        mttr_h = max(0.0, (wo.completed_at - wo.started_at).total_seconds() / 3600)
        mttrs.append(mttr_h)
        label = None
        if group_by == "equipment":
            eq = equipments_map.get(wo.equipment_id)
            label = (eq.prefix if eq else f"Eq {wo.equipment_id}")
        else:
            eq = equipments_map.get(wo.equipment_id)
            label = abbreviate_category(eq.category) if (eq and eq.category) else "Sem categoria"
        grouped.setdefault(label, []).append(mttr_h)
    
    grouped_result = [
        {"label": k, "mttr_hours": round(sum(v)/len(v), 2)} for k, v in grouped.items()
    ]
    overall = round(sum(mttrs)/len(mttrs), 2)
    return {"grouped": grouped_result, "overall": overall}

@router.get("/kpis/mtbf-grouped")
async def get_mtbf_grouped(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    group_by: str = "equipment",
    db: Session = Depends(get_db)
):
    """MTBF agrupado por equipamento ou categoria (apenas OS corretivas fechadas)."""
    from app.models.equipment import Equipment
    query = db.query(WorkOrder).filter(
        and_(WorkOrder.type == "Corretiva", WorkOrder.status == "Fechada")
    )
    if start_date:
        query = query.filter(WorkOrder.completed_at >= datetime.fromisoformat(start_date))
    if end_date:
        query = query.filter(WorkOrder.completed_at <= datetime.fromisoformat(end_date))
    
    wos = query.order_by(WorkOrder.completed_at).all()
    if not wos:
        return {"grouped": [], "overall": 0}
    
    equipments_map = {eq.id: eq for eq in db.query(Equipment).all()}
    grouped = {}
    intervals_all = []
    # Agrupar por equipamento primeiro
    from collections import defaultdict
    wos_by_eq = defaultdict(list)
    for wo in wos:
        wos_by_eq[wo.equipment_id].append(wo)
    
    for eq_id, list_wos in wos_by_eq.items():
        list_wos.sort(key=lambda x: x.completed_at)
        intervals = []
        for i in range(1, len(list_wos)):
            interval = (list_wos[i].completed_at - list_wos[i-1].completed_at).total_seconds() / 3600
            intervals.append(interval)
        if intervals:
            mtbf_eq = sum(intervals) / len(intervals)
            eq = equipments_map.get(eq_id)
            label_eq = (
                (eq.prefix if (eq and group_by == "equipment") else (abbreviate_category(eq.category) if (eq and eq.category) else "Sem categoria"))
            )
            grouped.setdefault(label_eq, []).append(mtbf_eq)
            intervals_all.extend(intervals)
    
    grouped_result = [
        {"label": k, "mtbf_hours": round(sum(v)/len(v), 2)} for k, v in grouped.items()
    ]
    overall = round(sum(intervals_all)/len(intervals_all), 2) if intervals_all else 0
    return {"grouped": grouped_result, "overall": overall}

@router.get("/backlog")
async def get_backlog(
    year: Optional[int] = None,
    group_by: str = "month",
    db: Session = Depends(get_db)
):
    """Backlog: volume de OS abertas/pendentes por período e evolução no ano."""
    status_open = ["Aberta", "Em andamento"]
    
    # Contagem atual
    current_backlog = db.query(WorkOrder).filter(WorkOrder.status.in_(status_open)).count()
    
    # Evolução por mês do ano
    if not year:
        year = datetime.now().year
    result = db.query(
        extract('month', WorkOrder.created_at).label('month'),
        func.count(WorkOrder.id).label('count')
    ).filter(
        and_(
            WorkOrder.status.in_(status_open),
            extract('year', WorkOrder.created_at) == year
        )
    ).group_by('month').order_by('month').all()
    
    evolution = [{"month": int(r.month), "count": int(r.count)} for r in result]
    return {"current_backlog": current_backlog, "evolution": evolution, "year": year}

@router.get("/fuel-consumption")
async def get_fuel_consumption(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    group_by: str = "equipment",
    db: Session = Depends(get_db)
):
    """Consumo médio de combustível por equipamento, modelo ou categoria."""
    from app.models.warehouse import Fueling
    from app.models.equipment import Equipment
    
    query = db.query(Fueling)
    if start_date:
        query = query.filter(Fueling.date >= datetime.fromisoformat(start_date))
    if end_date:
        query = query.filter(Fueling.date <= datetime.fromisoformat(end_date))
    fuelings = query.all()
    
    equipments_map = {eq.id: eq for eq in db.query(Equipment).all()}
    grouped = {}
    for f in fuelings:
        eq = equipments_map.get(f.equipment_id)
        if group_by == "model":
            label = (eq.model if eq else None) or "Sem modelo"
        elif group_by == "category":
            label = abbreviate_category(eq.category) if (eq and eq.category) else "Sem categoria"
        else:
            label = (eq.prefix if eq else f"Eq {f.equipment_id}")
        grouped.setdefault(label, {"total_quantity": 0.0, "events": 0, "total_cost": 0.0})
        grouped[label]["total_quantity"] += (f.quantity or 0.0)
        grouped[label]["events"] += 1
        grouped[label]["total_cost"] += (f.total_cost or 0.0)
    
    result = []
    for label, data in grouped.items():
        avg_consumption = (data["total_quantity"] / data["events"]) if data["events"] else 0.0
        result.append({
            "label": label,
            "avg_consumption": round(avg_consumption, 2),
            "events": data["events"],
            "total_cost": round(data["total_cost"], 2)
        })
    return {"grouped": result}

@router.get("/exceeded-quota")
async def get_exceeded_quota(
    year: int,
    month: int,
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Equipamentos que ultrapassaram a franquia mensal de horas."""
    from datetime import date
    from app.models.equipment import Equipment, WeeklyHours
    
    hours = db.query(WeeklyHours).filter(WeeklyHours.week.like(f"{year}-%")).all()
    # Filtrar por mês pela data de segunda-feira da semana ISO
    def week_month(wh):
        try:
            parts = wh.week.split("-W")
            y = int(parts[0]); w = int(parts[1])
            d = date.fromisocalendar(y, w, 1)
            return d.month
        except:
            return None
    hours = [h for h in hours if week_month(h) == month]
    
    equipments = db.query(Equipment).all()
    eq_map = {e.id: e for e in equipments}
    if category:
        equipments = [e for e in equipments if (e.category or "") == category]
    
    # Somar horas por equipamento
    total_hours = {}
    for h in hours:
        if h.equipment_id in eq_map:
            total_hours[h.equipment_id] = total_hours.get(h.equipment_id, 0.0) + (h.total_hours or 0.0)
    
    exceeded = []
    for eq in equipments:
        quota = eq.monthly_quota or 0.0
        used = total_hours.get(eq.id, 0.0)
        if quota and used > quota:
            exceeded.append({
                "equipment": f"{eq.prefix} - {eq.name}",
                "category": eq.category or "Sem categoria",
                "class": eq.equipment_class or "Sem classe",
                "monthly_quota": quota,
                "used_hours": round(used, 2),
                "exceeded_hours": round(used - quota, 2),
                "percentage": round((used / quota) * 100.0, 2)
            })
    
    # Comparativo por classe e categoria
    from collections import defaultdict
    by_class = defaultdict(int)
    by_category = defaultdict(int)
    for item in exceeded:
        by_class[item["class"]] += 1
        by_category[abbreviate_category(item["category"])] += 1
    
    return {
        "list": exceeded,
        "by_class": [{"label": k, "count": v} for k, v in by_class.items()],
        "by_category": [{"label": k, "count": v} for k, v in by_category.items()],
        "year": year,
        "month": month
    }

# ==================== CHAT DE IA (respostas baseadas nos dados dos relatórios) ====================

class AIChatMessage(BaseModel):
    role: str
    content: str

class AIChatRequest(BaseModel):
    messages: List[AIChatMessage]
    filters: Optional[Dict[str, Any]] = None


def _resolve_period_from_filters(filters: Optional[Dict[str, Any]]):
    """Recebe filtros do front e retorna (start_date_iso, end_date_iso, label)."""
    if not filters:
        return None, None, "Últimos 30 dias"
    year = filters.get("year")
    month = filters.get("month")
    try:
        if year and month:
            y = int(year); m = int(month)
            start = f"{y}-{m:02d}-01"
            # último dia do mês
            import calendar
            last_day = calendar.monthrange(y, m)[1]
            end = f"{y}-{m:02d}-{last_day:02d}T23:59:59"
            label = f"{y}-{m:02d}"
            return start, end, label
        elif year:
            y = int(year)
            start = f"{y}-01-01"
            end = f"{y}-12-31T23:59:59"
            label = f"{y}"
            return start, end, label
    except Exception:
        pass
    return None, None, "Últimos 30 dias"


def _detect_intent_pt(text: str) -> str:
    t = (text or "").lower()
    # mapeamento simples de intenções
    if any(k in t for k in ["disponib", "parada", "uptime", "downtime"]):
        return "availability"
    if any(k in t for k in ["utiliza", "ocup", "uso"]):
        return "utilization"
    if "mttr" in t:
        return "mttr"
    if "mtbf" in t:
        return "mtbf"
    if any(k in t for k in ["custo", "gasto", "despesa"]):
        return "costs"
    if any(k in t for k in ["backlog", "penden", "abertas"]):
        return "backlog"
    if any(k in t for k in ["combust", "diesel", "abastec"]):
        return "fuel"
    if any(k in t for k in ["franquia", "quota", "exced"]):
        return "quota"
    # Contagem de equipamentos cadastrados
    if any(k in t for k in [
        "quantos equip", "qtd equip", "equipamentos cadastrados", "total de equip", "número de equip", "numero de equip"
    ]):
        return "equipment_count"
    # Diagnóstico de falhas / causas prováveis
    if any(k in t for k in [
        "perda de potência", "perca de potência", "perda de potencia", "perca de potencia",
        "sem potência", "sem potencia", "fraca", "não sobe", "nao sobe",
        "falha", "problema", "defeito", "sintoma", "causas", "diagnóst", "diagnost",
        "não liga", "nao liga", "apaga", "engasga", "trava", "rateando",
        "superaquec", "esquentando",
        "guindaste", "grua", "escavadeira", "pá carregadeira", "retroescavadeira",
        "hidráulic", "hidraulic",
    ]):
        return "troubleshoot"
    # Busca de peças (part number / referência)
    if any(k in t for k in ["retrovisor", "espelho", "referência", "referencia", "peça", "peca", "part number", "código", "codigo", "320d", "escavadeira", "caterpillar", "cat 320"]):
        return "parts_lookup"
    # Especificações de óleo / viscosidade
    if any(k in t for k in ["óleo", "oleo", "viscos", "15w30", "15w-30", "sae 15w", "sae j300"]):
        return "fluid_spec"
    return "overview"


def _format_top(items, key, n=3, suffix=""):
    try:
        sorted_items = sorted(items, key=lambda x: x.get(key, 0))
        return ", ".join([f"{i.get('label')} ({i.get(key):.2f}{suffix})" for i in sorted_items[:n]])
    except Exception:
        return ""


@router.post("/maintenance/ai-chat")
async def maintenance_ai_chat(payload: AIChatRequest, db: Session = Depends(get_db)):
    """Gera respostas textuais baseadas nos endpoints existentes, considerando os filtros atuais.
    Opcionalmente usa provedor externo (Copilot) para melhorar a redação com os mesmos dados.
    """
    # Extrair última pergunta do usuário
    user_msg = ""
    for m in (payload.messages or [])[::-1]:
        if (m.role or "").lower() == "user":
            user_msg = m.content or ""
            break
    intent = _detect_intent_pt(user_msg)

    start_date, end_date, period_label = _resolve_period_from_filters(payload.filters or {})
    replies = []
    sources = []

    # Disponibilidade
    if intent in ("availability", "overview"):
        data_cat = await get_availability(start_date=start_date, end_date=end_date, group_by="category", db=db)
        overall = data_cat.get("overall", 0)
        top_low = _format_top(data_cat.get("grouped", []), "availability_percent", 3, "%")
        replies.append(f"Disponibilidade média: {overall:.2f}%. Categorias com menor disponibilidade: {top_low or '—'}.")
        sources.append("/api/reports/availability?group_by=category")

    # Utilização
    if intent in ("utilization", "overview"):
        # Utilização usa ano/semana. Quando período não especificado, tenta derivar de start/end -> ano
        year = None
        if payload.filters and payload.filters.get("year"):
            try: year = int(payload.filters.get("year"))
            except: year = None
        util = await get_utilization(year=year, week=payload.filters.get("week") if (payload.filters) else None, group_by="category", db=db)
        util_overall = util.get("overall", 0)
        top_util = _format_top(util.get("grouped", []), "utilization_percent", 3, "%")
        replies.append(f"Utilização média: {util_overall:.2f}%. Maiores utilizações por categoria: {top_util or '—'}.")
        sources.append("/api/reports/utilization?group_by=category")

    # MTTR
    if intent in ("mttr", "overview"):
        mttr_g = await get_mttr_grouped(start_date=start_date, end_date=end_date, group_by="category", db=db)
        mttr_overall = mttr_g.get("overall", 0)
        worst_mttr = _format_top(mttr_g.get("grouped", []), "mttr_hours", 3, "h")
        replies.append(f"MTTR médio: {mttr_overall:.2f} h. Maiores MTTR por categoria: {worst_mttr or '—'}.")
        sources.append("/api/reports/kpis/mttr-grouped?group_by=category")

    # MTBF
    if intent in ("mtbf", "overview"):
        mtbf_g = await get_mtbf_grouped(start_date=start_date, end_date=end_date, group_by="category", db=db)
        mtbf_overall = mtbf_g.get("overall", 0)
        best_mtbf = _format_top(mtbf_g.get("grouped", []), "mtbf_hours", 3, "h")
        replies.append(f"MTBF médio: {mtbf_overall:.2f} h. Maiores MTBF por categoria: {best_mtbf or '—'}.")
        sources.append("/api/reports/kpis/mtbf-grouped?group_by=category")

    # Custos
    if intent in ("costs", "overview"):
        costs_eq = await get_maintenance_costs(start_date=start_date, end_date=end_date, group_by="equipment", db=db)
        # Top 3 por custo
        try:
            top_costs = sorted(costs_eq, key=lambda x: x.get("total_cost", 0), reverse=True)[:3]
            top_costs_str = ", ".join([f"{c['equipment']} (R$ {float(c['total_cost']):,.2f})" for c in top_costs])
        except Exception:
            top_costs_str = ""
        replies.append(f"Custos por equipamento (top 3): {top_costs_str or '—'}.")
        sources.append("/api/reports/maintenance-costs?group_by=equipment")

    # Backlog
    if intent in ("backlog", "overview"):
        from datetime import datetime as _dt
        year = None
        try:
            if payload.filters and payload.filters.get("year"):
                year = int(payload.filters.get("year"))
        except:
            year = _dt.now().year
        backlog = await get_backlog(year=year, group_by="month", db=db)
        replies.append(f"Backlog atual (OS abertas): {backlog.get('current_backlog', 0)}.")
        sources.append("/api/reports/backlog")

    # Combustível
    if intent in ("fuel", "overview"):
        fuel = await get_fuel_consumption(start_date=start_date, end_date=end_date, group_by="category", db=db)
        try:
            top_fuel = sorted(fuel.get("grouped", []), key=lambda x: x.get("avg_consumption", 0), reverse=True)[:3]
            top_fuel_str = ", ".join([f"{c['label']} ({c['avg_consumption']} L/evento)" for c in top_fuel])
        except Exception:
            top_fuel_str = ""
        replies.append(f"Consumo médio de combustível (top categorias): {top_fuel_str or '—'}.")
        sources.append("/api/reports/fuel-consumption?group_by=category")

    # Excedentes de franquia
    if intent in ("quota",):
        # Requer ano/mês
        try:
            y = int(payload.filters.get("year")) if payload.filters and payload.filters.get("year") else datetime.now().year
            m = int(payload.filters.get("month")) if payload.filters and payload.filters.get("month") else datetime.now().month
        except Exception:
            y = datetime.now().year; m = datetime.now().month
        quota = await get_exceeded_quota(year=y, month=m, category=payload.filters.get("category") if payload.filters else None, db=db)
        qtd = len(quota.get("list", []))
        replies.append(f"Equipamentos que excederam a franquia em {y}-{m:02d}: {qtd}.")
        sources.append("/api/reports/exceeded-quota")

    # Contagem de equipamentos cadastrados
    if intent in ("equipment_count",):
        try:
            total = db.query(Equipment).count()
        except Exception:
            total = 0
        replies.append(f"Há {total} equipamentos cadastrados no sistema.")
        sources.append("/api/maintenance/equipment/list")

    # ===== Integração simples com web para perguntas fora do escopo dos relatórios =====
    async def _search_web_duckduckgo(query: str, max_results: int = 3):
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                r = await client.get(
                    "https://api.duckduckgo.com/",
                    params={
                        "q": query,
                        "format": "json",
                        "no_html": 1,
                        "skip_disambig": 1,
                        "no_redirect": 1,
                    },
                    headers={"Accept": "application/json"},
                )
                data = r.json()
                results = []
                if data.get("AbstractText"):
                    results.append({
                        "title": data.get("Heading") or "Resultado",
                        "url": data.get("AbstractURL"),
                        "snippet": data.get("AbstractText"),
                    })
                # Flatten RelatedTopics
                def _flat(lst):
                    for it in lst or []:
                        if isinstance(it, dict) and "Topics" in it:
                            for sub in it.get("Topics", []):
                                yield sub
                        else:
                            yield it
                for it in _flat(data.get("RelatedTopics")):
                    if len(results) >= max_results:
                        break
                    results.append({
                        "title": it.get("Text"),
                        "url": it.get("FirstURL"),
                        "snippet": it.get("Text"),
                    })
                return [x for x in results[:max_results] if x.get("url")]
        except Exception:
            return []

    # Ranquear causas por dados internos (OS fechadas no período)
    def _rank_causes_by_internal_data(category: Optional[str], lookback_days: int = 365) -> List[Dict[str, Any]]:
        keywords = {
            "admissao": ["filtro de ar", "admiss", "entrada de ar", "restrição ar"],
            "combustivel": ["filtro de combustível", "baixa pressão", "ar no sistema", "diesel contamin"],
            "turbo_pressurizacao": ["mangueira", "intercooler", "vazamento", "wastegate", "turbo"],
            "injecao_combustao": ["bico", "bomba", "injeç", "compressão", "combustão"],
            "pos_tratamento": ["dpf", "egr", "regener", "derate"],
            "hidraulico": ["válvula", "bomba", "cavitação", "vazamento interno", "pressão hidráulica"],
            "transmissao_pto": ["embreagem", "pto", "conversor", "patinação", "atrito"],
            "eletrica_sensores": ["sensor", "map", "maf", "temperatura", "pressão", "chicote"],
            "superaquecimento": ["superaquec", "alta temperatura", "arrefecimento", "radiador", "ventoinha"],
        }
        cutoff = datetime.now() - timedelta(days=lookback_days)
        counts = {k: 0 for k in keywords.keys()}
        try:
            q = db.query(WorkOrder).join(Equipment, Equipment.id == WorkOrder.equipment_id).filter(
                WorkOrder.status == "Fechada",
                WorkOrder.completed_at.isnot(None),
                WorkOrder.completed_at >= cutoff
            )
            if category:
                q = q.filter(Equipment.category == category)
            rows = q.limit(500).all()
            for wo in rows:
                text = f"{wo.title or ''} {wo.description or ''}".lower()
                for k, kws in keywords.items():
                    if any(kw in text for kw in kws):
                        counts[k] += 1
        except Exception:
            pass
        ranked = sorted([{"key": k, "score": v} for k, v in counts.items()], key=lambda x: x["score"], reverse=True)
        return ranked

    async def _extract_specifics_from_urls(urls: List[str], max_items: int = 3) -> List[str]:
        if not urls:
            return []
        snippets: List[str] = []
        terms = ["causa", "sintoma", "diagn", "verificar", "checagem", "falha", "perda de potência", "hidrául", "diesel", "elétric"]
        try:
            async with httpx.AsyncClient(timeout=6.0, headers={"User-Agent": "MTDL-PCM/1.0"}) as client:
                for url in urls[:2]:
                    try:
                        r = await client.get(url)
                        if r.status_code != 200:
                            continue
                        txt = r.text
                        import re
                        clean = re.sub(r"<[^>]+>", " ", txt)
                        clean = re.sub(r"\s+", " ", clean)
                        sentences = re.split(r"[\.!?]", clean)
                        for s in sentences:
                            s2 = s.strip().lower()
                            if any(t in s2 for t in terms):
                                snippets.append(s.strip())
                                if len(snippets) >= max_items:
                                    break
                        if len(snippets) >= max_items:
                            break
                    except Exception:
                        continue
        except Exception:
            return []
        return snippets

    if intent == "parts_lookup":
        q = user_msg.strip() or "retrovisor esquerdo escavadeira 320D part number"
        web = await _search_web_duckduckgo(q, max_results=3)
        if web:
            replies = [
                "Não tenho acesso ao catálogo oficial. Consultei fontes públicas na web; valide no fornecedor/SIS:",
            ]
            for idx, w in enumerate(web, 1):
                replies.append(f"{idx}. {w.get('title') or 'Fonte'} — {w.get('url')}")
            for w in web:
                if w.get("url"):
                    sources.append(w.get("url"))
        else:
            replies = [
                "Não encontrei um part number confiável em fontes públicas.",
                "Sugestão: busque no parts.cat.com ou informe o serial/prefixo exato.",
            ]

    if intent == "fluid_spec":
        # Explicação com base na norma SAE J300 (faixas típicas)
        replies = [
            "Óleo 15W-30 (SAE J300):",
            "• '15W' — baixa temperatura: CCS ≤ 7000 mPa·s a −20°C; MRV ≤ 60.000 mPa·s a −25°C.",
            "• '30' — alta temperatura: viscosidade cinemática a 100°C entre 9,3 e <12,5 cSt; HTHS ≥ 2,9 mPa·s.",
            "Observação: consulte a ficha técnica (TDS) do fabricante para valores exatos.",
        ]
        refs = await _search_web_duckduckgo("SAE J300 15W-30 viscosidade tabela", max_results=2)
        if refs:
            replies.append("Fontes:")
            for i, r in enumerate(refs, 1):
                replies.append(f"{i}. {r.get('title') or 'Referência'} — {r.get('url')}")
                if r.get("url"):
                    sources.append(r.get("url"))

    if intent == "troubleshoot":
        # Diagnóstico refinado por tipo de equipamento + dados internos
        q = (user_msg or "").strip() or "perda de potência causas"
        web_refs = await _search_web_duckduckgo(q, max_results=3)
        for w in web_refs:
            if w.get("url"):
                sources.append(w.get("url"))

        # Tipagem por texto e filtros
        eq_type = "geral"
        t = (user_msg or "").lower()
        if any(k in t for k in ["hidrául", "hidraulic"]):
            eq_type = "hidraulico"
        elif any(k in t for k in ["elétric", "eletric"]):
            eq_type = "eletrico"
        elif any(k in t for k in ["diesel", "motor"]):
            eq_type = "diesel"
        cat = (payload.filters.get("category") if payload.filters else None) or None
        ranked = _rank_causes_by_internal_data(cat)

        def base_order(eq: str) -> List[str]:
            if eq == "hidraulico":
                return ["hidraulico","combustivel","injecao_combustao","turbo_pressurizacao","eletrica_sensores","transmissao_pto","pos_tratamento","admissao","superaquecimento"]
            if eq == "eletrico":
                return ["eletrica_sensores","combustivel","injecao_combustao","admissao","turbo_pressurizacao","pos_tratamento","superaquecimento","hidraulico","transmissao_pto"]
            # diesel
            return ["combustivel","injecao_combustao","turbo_pressurizacao","admissao","pos_tratamento","eletrica_sensores","superaquecimento","hidraulico","transmissao_pto"]

        order = base_order(eq_type)
        score_map = {x["key"]: x["score"] for x in ranked}
        order_sorted = sorted(order, key=lambda k: (-score_map.get(k, 0), order.index(k)))

        replies = [
            f"Diagnóstico por tipo ({eq_type}) e dados internos ({cat or 'geral'}):",
        ]
        causes_text = {
            "admissao": "Admissão: filtro de ar saturado, obstruções, entrada falsa de ar.",
            "combustivel": "Combustível: filtro entupido, baixa pressão, ar no sistema, diesel contaminado.",
            "turbo_pressurizacao": "Turbo/pressurização: vazamentos em mangueiras, intercooler furado, wastegate travada, turbo desgastado.",
            "injecao_combustao": "Injeção/combustão: bicos irregulares, bomba desgastada, baixa compressão.",
            "pos_tratamento": "Pós-tratamento/derate: DPF/EGR obstruídos, falhas de regeneração, limites de ECU.",
            "hidraulico": "Hidráulico sobrecarregando motor: válvula de alívio fora de ajuste, bomba desgastada, cavitação, vazamento interno.",
            "transmissao_pto": "Transmissão/PTO: patinação de embreagem, conversor de torque, atrito anormal.",
            "eletrica_sensores": "Elétrica/sensores: MAP/MAF, pressão combustível/óleo, temperatura, chicotes/intermitências.",
            "superaquecimento": "Superaquecimento: arrefecimento, radiador, ventoinha, termostato, bomba d’água.",
        }
        for k in order_sorted[:6]:
            replies.append(f"• {causes_text.get(k)}")

        replies.append("Checklist (seguir manual OEM e segurança):")
        replies.extend([
            "1) Ler códigos no painel/ECU; 2) Conferir filtros (ar/comb.) e restrições;",
            "3) Medir pressão/vazão de combustível; 4) Inspecionar mangueiras de turbo/intercooler;",
            "5) Verificar DPF/EGR e temperatura; 6) Medir pressões/vazões hidráulicas;",
            "7) Checar viscosidade/contaminação do óleo hidráulico; 8) Avaliar patinação PTO/embreagem;",
            "9) Testar sensores críticos e chicotes.",
        ])

        specifics = await _extract_specifics_from_urls(sources, max_items=3)
        if specifics:
            replies.append("Pontos específicos encontrados:")
            for s in specifics:
                replies.append(f"- {s[:240]}")

    # Montagem da resposta
    if not replies:
        replies.append("Posso explicar disponibilidade, utilização, MTTR/MTBF, custos, backlog e franquia a partir dos dados do sistema. Tente algo como: 'Quais categorias tiveram menor disponibilidade este mês?'")

    summary = " ".join([r for r in replies if r])
    period_txt = f"Período: {period_label}"

    # Copilot opcional para refino textual (não altera os números)
    final_text = f"{summary} {period_txt}."
    if os.getenv("AI_PROVIDER"):
        system_prompt = (
            "Você é um copiloto de manutenção industrial. Responda em português do Brasil. "
            "Use somente os dados fornecidos no contexto do sistema e não invente valores. "
            "Se não houver dados, diga objetivamente que não há dados no período. "
            "Seja direto e claro."
        )
        context = (
            f"Pergunta: {(user_msg or '').strip()}\n"
            f"{period_txt}\n"
            f"Dados:\n- " + ("\n- ".join([r for r in replies if r])) + "\n"
            f"Fontes: " + (", ".join(sources) if sources else "—")
        )
        try:
            llm_out = await llm_generate([{"role": "user", "content": context}], system_prompt=system_prompt)
            if llm_out:
                final_text = llm_out.strip()
                if period_label and (period_label not in final_text):
                    final_text = f"{final_text} {period_txt}."
        except Exception:
            pass

    return {
        "reply": final_text,
        "intent": intent,
        "period": period_label,
        "sources": sources
    }

# ==================== RELATÓRIOS DE ALMOXARIFADO (AGRUPADOS POR CATEGORIA) ====================

@router.get("/warehouse/stock-turnover-grouped")
async def get_stock_turnover_grouped(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    group_by: str = "category",
    db: Session = Depends(get_db)
):
    """Giro de estoque agrupado (padrão por categoria).
    Fórmula: Giro = Consumo no período / Estoque médio (aprox. estoque atual).
    """
    if not start_date:
        start_date = (datetime.now() - timedelta(days=365)).isoformat()
    if not end_date:
        end_date = datetime.now().isoformat()

    movements = db.query(StockMovement).filter(
        and_(
            StockMovement.type == "Saída",
            StockMovement.date >= datetime.fromisoformat(start_date),
            StockMovement.date <= datetime.fromisoformat(end_date)
        )
    ).all()

    # Consumo por material
    material_consumption = {}
    for mv in movements:
        material_consumption[mv.material_id] = material_consumption.get(mv.material_id, 0.0) + (mv.quantity or 0.0)

    # Calcular giro por material
    per_material = []
    for mid, cons in material_consumption.items():
        m = db.query(Material).filter(Material.id == mid).first()
        if not m:
            continue
        stock = m.current_stock or 0.0
        if stock <= 0:
            continue
        turnover = cons / stock
        per_material.append({
            "category": (m.category or "Sem categoria"),
            "label": f"{m.code} - {m.name}",
            "turnover": round(turnover, 2)
        })

    # Agrupado por categoria
    grouped = {}
    for row in per_material:
        key = row["category"] if group_by == "category" else row["category"]
        grouped.setdefault(key, []).append(row["turnover"])

    grouped_result = [{"label": k, "turnover": round(sum(v) / len(v), 2)} for k, v in grouped.items()]
    overall = round(sum([r["turnover"] for r in per_material]) / len(per_material), 2) if per_material else 0.0

    return {
        "period": f"{start_date} até {end_date}",
        "grouped": grouped_result,
        "materials": per_material,
        "overall": overall
    }

@router.get("/warehouse/stock-coverage")
async def get_stock_coverage(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    group_by: str = "category",
    db: Session = Depends(get_db)
):
    """Cobertura de estoque (dias) = Estoque Atual / Consumo Diário Médio."""
    if not start_date:
        start_date = (datetime.now() - timedelta(days=90)).isoformat()
    if not end_date:
        end_date = datetime.now().isoformat()

    start_dt = datetime.fromisoformat(start_date)
    end_dt = datetime.fromisoformat(end_date)
    days = max(1, (end_dt - start_dt).days)

    movements = db.query(StockMovement).filter(
        and_(
            StockMovement.type == "Saída",
            StockMovement.date >= start_dt,
            StockMovement.date <= end_dt
        )
    ).all()

    # Consumo por material
    material_consumption = {}
    for mv in movements:
        material_consumption[mv.material_id] = material_consumption.get(mv.material_id, 0.0) + (mv.quantity or 0.0)

    per_material = []
    for mid, cons in material_consumption.items():
        m = db.query(Material).filter(Material.id == mid).first()
        if not m:
            continue
        daily = cons / days if days else 0.0
        coverage = (m.current_stock or 0.0) / daily if daily > 0 else None
        if coverage is None:
            continue
        # Limitar cobertura excessiva para visualização
        coverage = min(coverage, 365.0)
        per_material.append({
            "category": (m.category or "Sem categoria"),
            "label": f"{m.code} - {m.name}",
            "coverage_days": round(coverage, 2)
        })

    grouped = {}
    for row in per_material:
        key = row["category"] if group_by == "category" else row["category"]
        grouped.setdefault(key, []).append(row["coverage_days"])

    grouped_result = [{"label": k, "coverage_days": round(sum(v) / len(v), 2)} for k, v in grouped.items()]
    overall = round(sum([r["coverage_days"] for r in per_material]) / len(per_material), 2) if per_material else 0.0

    return {
        "period": f"{start_date} até {end_date}",
        "grouped": grouped_result,
        "materials": per_material,
        "overall": overall
    }

@router.get("/warehouse/stockout-rate")
async def get_stockout_rate(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    group_by: str = "category",
    db: Session = Depends(get_db)
):
    """Taxa de Ruptura: Pedidos não atendidos / Total de pedidos × 100.
    Aproximação baseada em requisições de compra não atendidas (sem pedidos entregues).
    """
    # Buscar requisições no período
    pr_query = db.query(PurchaseRequest)
    if start_date:
        pr_query = pr_query.filter(PurchaseRequest.requested_date >= datetime.fromisoformat(start_date))
    if end_date:
        pr_query = pr_query.filter(PurchaseRequest.requested_date <= datetime.fromisoformat(end_date))
    prs = pr_query.all()

    # Mapear categorias por requisição (via itens)
    from collections import defaultdict
    pr_categories = defaultdict(set)
    for pr in prs:
        items = db.query(PurchaseRequestItem).filter(PurchaseRequestItem.purchase_request_id == pr.id).all()
        for it in items:
            mat = db.query(Material).filter(Material.id == it.material_id).first()
            pr_categories[pr.id].add((mat.category if mat and mat.category else "Sem categoria"))

    # Determinar se requisição foi atendida (algum pedido com status Entregue)
    pr_attended = {}
    for pr in prs:
        delivered = False
        orders = db.query(PurchaseOrder).filter(PurchaseOrder.purchase_request_id == pr.id).all()
        for po in orders:
            if (po.status or "").lower() == "entregue":
                delivered = True
                break
        pr_attended[pr.id] = delivered

    # Contabilizar por categoria
    totals = defaultdict(int)
    not_attended = defaultdict(int)
    for pr in prs:
        cats = pr_categories.get(pr.id, {"Sem categoria"})
        for c in cats:
            totals[c] += 1
            if not pr_attended.get(pr.id, False) or (pr.status or "").lower() in ["rejeitada"]:
                not_attended[c] += 1

    grouped_result = []
    overall_total = sum(totals.values())
    overall_not = sum(not_attended.values())
    for c, tot in totals.items():
        na = not_attended.get(c, 0)
        rate = (na / tot) * 100.0 if tot else 0.0
        grouped_result.append({"label": c, "stockout_rate": round(rate, 2), "total": tot, "not_attended": na})

    overall = (overall_not / overall_total) * 100.0 if overall_total else 0.0
    return {"grouped": grouped_result, "overall": round(overall, 2)}

@router.get("/warehouse/inventory-accuracy-grouped")
async def get_inventory_accuracy_grouped(
    inventory_id: Optional[int] = None,
    group_by: str = "category",
    db: Session = Depends(get_db)
):
    """Acuracidade do inventário agrupada por categoria.
    Fórmula: Itens corretos / Total de itens verificados × 100.
    """
    # Selecionar inventário (último por padrão)
    inv = None
    if inventory_id:
        inv = db.query(InventoryHistory).filter(InventoryHistory.id == inventory_id).first()
    else:
        inv = db.query(InventoryHistory).order_by(InventoryHistory.process_date.desc()).first()
    if not inv:
        return {"grouped": [], "overall": 0.0}

    items = db.query(InventoryHistoryItem).filter(InventoryHistoryItem.inventory_id == inv.id).all()
    from collections import defaultdict
    totals = defaultdict(int)
    corrects = defaultdict(int)
    for it in items:
        mat = db.query(Material).filter(Material.id == it.material_id).first()
        cat = mat.category if mat and mat.category else "Sem categoria"
        totals[cat] += 1
        # Considera correto quando diferença == 0
        if (it.difference or 0.0) == 0.0:
            corrects[cat] += 1

    grouped_result = []
    overall_total = sum(totals.values())
    overall_correct = sum(corrects.values())
    for c, tot in totals.items():
        corr = corrects.get(c, 0)
        acc = (corr / tot) * 100.0 if tot else 0.0
        grouped_result.append({"label": c, "accuracy_percent": round(acc, 2), "total": tot, "correct": corr})

    overall = (overall_correct / overall_total) * 100.0 if overall_total else 0.0
    return {"grouped": grouped_result, "overall": round(overall, 2), "inventory_id": inv.id}

@router.get("/warehouse/request-service-time")
async def get_request_service_time(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    group_by: str = "category",
    db: Session = Depends(get_db)
):
    """Tempo médio de atendimento de requisições.
    Fórmula: Soma dos tempos / Número de requisições (diferença entre solicitação e aprovação).
    """
    pr_query = db.query(PurchaseRequest)
    if start_date:
        pr_query = pr_query.filter(PurchaseRequest.requested_date >= datetime.fromisoformat(start_date))
    if end_date:
        pr_query = pr_query.filter(PurchaseRequest.requested_date <= datetime.fromisoformat(end_date))
    prs = pr_query.all()

    from collections import defaultdict
    times_by_cat = defaultdict(list)
    for pr in prs:
        if not pr.approved_date:
            continue
        delta_days = max(0.0, (pr.approved_date - pr.requested_date).total_seconds() / 86400.0) if pr.requested_date else 0.0
        items = db.query(PurchaseRequestItem).filter(PurchaseRequestItem.purchase_request_id == pr.id).all()
        cats = set()
        for it in items:
            mat = db.query(Material).filter(Material.id == it.material_id).first()
            cats.add(mat.category if mat and mat.category else "Sem categoria")
        for c in cats:
            times_by_cat[c].append(delta_days)

    grouped_result = [{"label": c, "avg_days": round(sum(v) / len(v), 2)} for c, v in times_by_cat.items() if v]
    overall = round(sum([sum(v) for v in times_by_cat.values()]) / (sum([len(v) for v in times_by_cat.values()]) or 1), 2) if times_by_cat else 0.0
    return {"grouped": grouped_result, "overall": overall}

@router.get("/warehouse/storage-cost")
async def get_storage_cost(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    group_by: str = "category",
    db: Session = Depends(get_db)
):
    """Custo de Armazenagem aproximado.
    Fórmula: Custos Totais do Almoxarifado / Valor Médio do Estoque.
    - Custos Totais: soma de total_cost de entradas no período.
    - Valor Médio do Estoque: aproximação pelo valor atual (current_stock * average_cost).
    """
    if not start_date:
        start_date = (datetime.now() - timedelta(days=90)).isoformat()
    if not end_date:
        end_date = datetime.now().isoformat()

    start_dt = datetime.fromisoformat(start_date)
    end_dt = datetime.fromisoformat(end_date)

    # Custos totais (entradas)
    entries = db.query(StockMovement).filter(
        and_(
            StockMovement.type == "Entrada",
            StockMovement.date >= start_dt,
            StockMovement.date <= end_dt
        )
    ).all()

    from collections import defaultdict
    cost_by_cat = defaultdict(float)
    for mv in entries:
        mat = db.query(Material).filter(Material.id == mv.material_id).first()
        cat = mat.category if mat and mat.category else "Sem categoria"
        cost_by_cat[cat] += float(mv.total_cost or 0.0)

    # Valor médio do estoque por categoria (snapshot atual)
    materials = db.query(Material).all()
    value_by_cat = defaultdict(float)
    for m in materials:
        cat = m.category if m and m.category else "Sem categoria"
        value_by_cat[cat] += float((m.current_stock or 0.0) * (m.average_cost or 0.0))

    grouped_result = []
    for c in set(list(cost_by_cat.keys()) + list(value_by_cat.keys())):
        total_cost = cost_by_cat.get(c, 0.0)
        avg_value = value_by_cat.get(c, 0.0)
        ratio = (total_cost / avg_value) if avg_value > 0 else 0.0
        grouped_result.append({
            "label": c,
            "total_cost": round(total_cost, 2),
            "avg_stock_value": round(avg_value, 2),
            "storage_cost_ratio": round(ratio, 4)
        })

    overall_cost = sum(cost_by_cat.values())
    overall_value = sum(value_by_cat.values())
    overall_ratio = (overall_cost / overall_value) if overall_value > 0 else 0.0
    return {
        "period": f"{start_date} até {end_date}",
        "grouped": grouped_result,
        "overall": round(overall_ratio, 4),
        "overall_cost": round(overall_cost, 2),
        "overall_avg_stock_value": round(overall_value, 2)
    }

# Siglas de macroetapas para abas dos relatórios de obra
MACRO_ABBR = {
    "Planejamento e Mobilização": "Plan/Mob",
    "Infraestrutura Básica": "Infra Básica",
    "Estrutura Principal": "Estrut Princ",
    "Instalações Técnicas": "Inst Téc",
    "Equipamentos e Sistemas Industriais": "Equip/Sist Ind",
    "Edificações Complementares": "Edif Compl",
    "Acabamentos e Revestimentos": "Acab/Revest",
    "Testes, Comissionamento e Entrega": "Test/Comiss/Entreg",
}

@router.get("/construction")
@router.get("/by-project")
async def construction_reports_page(request: Request, db: Session = Depends(get_db)):
    """Página de Relatórios de Obra (Construção)"""
    accept_header = request.headers.get("accept", "")
    if "text/html" in accept_header:
        macros = (
            db.query(MacroStage)
            .filter(MacroStage.is_active == True)
            .order_by(MacroStage.order, MacroStage.name)
            .all()
        )
        macro_items = [{"id": m.id, "name": m.name, "abbr": MACRO_ABBR.get(m.name, m.name)} for m in macros]
        return templates.TemplateResponse("reports/construction.html", {"request": request, "macros": macro_items})
    return {"message": "Esta rota serve a página HTML; use Accept: text/html."}

@router.get("/construction/progress-by-substage")
async def construction_progress_by_substage(macro_id: int, db: Session = Depends(get_db)):
    """Progresso médio (%) por subetapa dentro da macroetapa informada"""
    subs = (
        db.query(SubStage)
        .filter(SubStage.macro_stage_id == macro_id, SubStage.is_active == True)
        .order_by(SubStage.order, SubStage.name)
        .all()
    )
    grouped = []
    for s in subs:
        tasks = db.query(Task).filter(Task.sub_stage_id == s.id).all()
        percents = []
        for t in tasks:
            planned = float(t.quantity_planned or 0.0)
            executed_qty = float(db.query(func.sum(TaskMeasurement.quantity_executed)).filter(TaskMeasurement.task_id == t.id).scalar() or 0.0)
            perc = (executed_qty / planned * 100.0) if planned > 0 else 0.0
            percents.append(perc)
        avg = round(sum(percents) / len(percents), 2) if percents else 0.0
        grouped.append({"label": s.name, "progress_percent": avg})
    macro = db.query(MacroStage).filter(MacroStage.id == macro_id).first()
    return {"macro_id": macro_id, "macro_name": (macro.name if macro else None), "grouped": grouped}

@router.get("/construction/planned-cost-by-substage")
async def construction_planned_cost_by_substage(macro_id: int, db: Session = Depends(get_db)):
    """Custo previsto total (R$) por subetapa dentro da macroetapa informada"""
    subs = (
        db.query(SubStage)
        .filter(SubStage.macro_stage_id == macro_id, SubStage.is_active == True)
        .order_by(SubStage.order, SubStage.name)
        .all()
    )
    grouped = []
    for s in subs:
        tasks = db.query(Task).filter(Task.sub_stage_id == s.id).all()
        total_cost = sum([float(t.total_cost_planned or 0.0) for t in tasks])
        grouped.append({"label": s.name, "planned_cost": round(total_cost, 2)})
    macro = db.query(MacroStage).filter(MacroStage.id == macro_id).first()
    return {"macro_id": macro_id, "macro_name": (macro.name if macro else None), "grouped": grouped}

@router.get("/management")
async def management_reports_page(request: Request):
    """Página de Relatórios Gerenciais (placeholder)"""
    accept_header = request.headers.get("accept", "")
    if "text/html" in accept_header:
        return templates.TemplateResponse("reports/management.html", {"request": request})
    return {"message": "Funcionalidade em desenvolvimento — estará disponível para consultas em breve."}

@router.get("/production")
async def production_reports_page(request: Request):
    """Página de Relatórios de Produção (placeholder)"""
    accept_header = request.headers.get("accept", "")
    if "text/html" in accept_header:
        return templates.TemplateResponse("reports/production.html", {"request": request})
    return {"message": "Funcionalidade em desenvolvimento — estará disponível para consultas em breve."}