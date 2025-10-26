"""
Router para dashboard e métricas
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from app.database import get_db
from app.models.maintenance import WorkOrder
from app.models.equipment import Equipment
from app.models.warehouse import Material, StockMovement
from app.templates_config import templates
from starlette.responses import RedirectResponse

router = APIRouter()

@router.get("/dashboard")
async def dashboard_page(request: Request, db: Session = Depends(get_db)):
    """Página principal do dashboard"""
    # Redirecionar para login se não autenticado
    from app.models.admin import SessionToken
    auth_header = request.headers.get("Authorization") or ""
    token_value = None
    if auth_header.lower().startswith("bearer "):
        token_value = auth_header.split(" ", 1)[1].strip()
    if not token_value:
        token_value = request.cookies.get("auth_token")
    if not token_value:
        token_value = request.query_params.get("token")
    if not token_value:
        return RedirectResponse(url="/admin/login", status_code=302)
    session = db.query(SessionToken).filter(
        SessionToken.token == token_value,
        SessionToken.is_revoked == False,
    ).first()
    if not session or session.expires_at < datetime.utcnow():
        return RedirectResponse(url="/admin/login", status_code=302)

    # Obter métricas básicas
    total_equipments = db.query(Equipment).count()
    pending_maintenance = db.query(WorkOrder).filter(
        WorkOrder.status.in_(["Aberta", "Em andamento"])
    ).count()
    total_materials = db.query(Material).count()
    
    # Manutenções recentes
    recent_maintenance = db.query(WorkOrder).order_by(
        WorkOrder.created_at.desc()
    ).limit(5).all()
    
    # Dados para o template
    context = {
        "request": request,
        "metrics": {
            "total_equipments": total_equipments,
            "active_equipments": total_equipments,  # Por enquanto, assumir que todos estão ativos
            "pending_maintenance": pending_maintenance,
            "overdue_maintenance": 0,  # Implementar lógica depois
            "total_materials": total_materials,
            "low_stock_items": 0,  # Implementar lógica depois
            "efficiency_rate": 0  # Será calculado quando houver dados
        },
        "recent_maintenance": [
            {
                "equipment_name": f"Equipamento {wo.equipment_id}" if wo.equipment_id else "N/A",
                "type": "preventiva" if "preventiva" in (wo.description or "").lower() else "corretiva",
                "status": wo.status.lower() if wo.status else "pendente",
                "date": wo.created_at.strftime("%d/%m/%Y") if wo.created_at else "N/A"
            }
            for wo in recent_maintenance
        ],
        "alerts": [
            {
                "type": "info",
                "icon": "info-circle",
                "title": "Sistema OK!",
                "message": "Todos os sistemas estão funcionando normalmente."
            }
        ],
        "critical_equipment": []  # Implementar depois
    }
    
    return templates.TemplateResponse("dashboard.html", context)

@router.get("/metrics")
async def get_dashboard_metrics(db: Session = Depends(get_db)):
    """Obter métricas do dashboard"""
    # Métricas base
    today = datetime.now().date()

    # Totais gerais
    total_equipments = db.query(Equipment).count()
    total_materials = db.query(Material).count()

    # Pendências e atrasos
    pending_maintenance = db.query(WorkOrder).filter(
        WorkOrder.status.in_(["Aberta", "Em andamento"])
    ).count()
    overdue_maintenance = db.query(WorkOrder).filter(
        and_(
            WorkOrder.status != "Fechada",
            WorkOrder.due_date < datetime.now()
        )
    ).count()

    # Status de equipamentos
    os_today = db.query(WorkOrder).filter(func.date(WorkOrder.created_at) == today).count()
    os_in_progress = db.query(WorkOrder).filter(WorkOrder.status == "Em andamento").count()
    equipment_maintenance = db.query(Equipment).filter(Equipment.status == "Manutenção").count()
    active_equipment = total_equipments - equipment_maintenance

    # Tempo médio de resolução (últimos 30 dias)
    thirty_days_ago = datetime.now() - timedelta(days=30)
    completed_os = db.query(WorkOrder).filter(
        and_(
            WorkOrder.status == "Fechada",
            WorkOrder.completed_at >= thirty_days_ago
        )
    ).all()
    avg_resolution_time = 0
    if completed_os:
        total_time = sum([
            (os.completed_at - os.created_at).total_seconds() / 3600 
            for os in completed_os if os.completed_at
        ])
        avg_resolution_time = round(total_time / len(completed_os), 2)

    # Alertas de preventiva (próximos 7 dias)
    next_week = datetime.now() + timedelta(days=7)
    preventive_alerts = db.query(WorkOrder).filter(
        and_(
            WorkOrder.type == "Preventiva",
            WorkOrder.due_date <= next_week,
            WorkOrder.status != "Fechada"
        )
    ).count()

    # Materiais com estoque baixo
    low_stock_materials = db.query(Material).filter(
        Material.current_stock <= Material.minimum_stock
    ).count()

    # Retornar no formato padronizado consumido pelo frontend
    return {
        "success": True,
        "data": {
            "pending_maintenance": pending_maintenance,
            "overdue_maintenance": overdue_maintenance,
            "materials_stock": total_materials,
            "low_stock": low_stock_materials,
            "operational_efficiency": 0,
            "active_equipment": active_equipment,
            "total_equipment": total_equipments,
            # Inclui algumas métricas adicionais úteis para futura expansão
            "os_today": os_today,
            "os_in_progress": os_in_progress,
            "equipment_maintenance": equipment_maintenance,
            "avg_resolution_time": avg_resolution_time,
            "preventive_alerts": preventive_alerts
        }
    }

@router.get("/charts/os-by-status")
async def get_os_by_status(db: Session = Depends(get_db)):
    """Gráfico de OS por status"""
    try:
        result = db.query(
            WorkOrder.status,
            func.count(WorkOrder.id).label('count')
        ).group_by(WorkOrder.status).all()
        return {
            'success': True,
            'data': {
                'labels': [item.status for item in result],
                'data': [item.count for item in result]
            }
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}

@router.get("/charts/equipment-by-status")
async def get_equipment_by_status(db: Session = Depends(get_db)):
    """Gráfico de equipamentos por status"""
    try:
        result = db.query(
            Equipment.status,
            func.count(Equipment.id).label('count')
        ).group_by(Equipment.status).all()
        return {
            'success': True,
            'data': {
                'labels': [item.status for item in result],
                'data': [item.count for item in result]
            }
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}

@router.get("/recent-activities")
async def get_recent_activities(db: Session = Depends(get_db)):
    """Atividades recentes do sistema"""
    from datetime import datetime, timedelta
    from app.models.warehouse import Fueling
    from app.models.equipment import Equipment
    
    activities = []
    
    # OS recentes (últimos 7 dias)
    seven_days_ago = datetime.now() - timedelta(days=7)
    recent_os = db.query(WorkOrder).filter(
        WorkOrder.created_at >= seven_days_ago
    ).order_by(WorkOrder.created_at.desc()).limit(10).all()
    
    for os in recent_os:
        # Determinar tipo de atividade baseado no status
        if os.status == "Fechada":
            activity_type = "success"
            title = "Manutenção Concluída"
        elif os.status == "Em andamento":
            activity_type = "info"
            title = "Manutenção em Andamento"
        else:
            activity_type = "primary"
            title = "Nova Ordem de Serviço"
        
        # Calcular tempo relativo
        time_diff = datetime.now() - os.created_at
        if time_diff.days > 0:
            time_str = f"Há {time_diff.days} dia{'s' if time_diff.days > 1 else ''}"
        elif time_diff.seconds > 3600:
            hours = time_diff.seconds // 3600
            time_str = f"Há {hours} hora{'s' if hours > 1 else ''}"
        else:
            minutes = time_diff.seconds // 60
            time_str = f"Há {minutes} minuto{'s' if minutes > 1 else ''}"
        
        activities.append({
            "type": activity_type,
            "title": title,
            "description": f"OS {os.number} - {os.title}",
            "time": time_str,
            "date": os.created_at.isoformat()
        })
    
    # Movimentações de estoque recentes (últimos 3 dias)
    three_days_ago = datetime.now() - timedelta(days=3)
    recent_movements = db.query(StockMovement).filter(
        StockMovement.date >= three_days_ago
    ).order_by(StockMovement.date.desc()).limit(8).all()
    
    for movement in recent_movements:
        # Determinar tipo baseado na movimentação
        if movement.type == "Entrada":
            activity_type = "success"
            title = "Material Recebido"
        elif movement.type == "Saída":
            activity_type = "warning"
            title = "Material Utilizado"
        else:  # Ajuste
            activity_type = "info"
            title = "Ajuste de Estoque"
        
        # Calcular tempo relativo
        time_diff = datetime.now() - movement.date
        if time_diff.days > 0:
            time_str = f"Há {time_diff.days} dia{'s' if time_diff.days > 1 else ''}"
        elif time_diff.seconds > 3600:
            hours = time_diff.seconds // 3600
            time_str = f"Há {hours} hora{'s' if hours > 1 else ''}"
        else:
            minutes = time_diff.seconds // 60
            time_str = f"Há {minutes} minuto{'s' if minutes > 1 else ''}"
        
        activities.append({
            "type": activity_type,
            "title": title,
            "description": f"{movement.material.name} - {abs(movement.quantity)} {movement.material.unit}",
            "time": time_str,
            "date": movement.date.isoformat()
        })
    
    # Abastecimentos recentes (últimos 2 dias)
    two_days_ago = datetime.now() - timedelta(days=2)
    recent_fuelings = db.query(Fueling).filter(
        Fueling.date >= two_days_ago
    ).order_by(Fueling.date.desc()).limit(5).all()
    
    for fueling in recent_fuelings:
        # Calcular tempo relativo
        time_diff = datetime.now() - fueling.date
        if time_diff.days > 0:
            time_str = f"Há {time_diff.days} dia{'s' if time_diff.days > 1 else ''}"
        elif time_diff.seconds > 3600:
            hours = time_diff.seconds // 3600
            time_str = f"Há {hours} hora{'s' if hours > 1 else ''}"
        else:
            minutes = time_diff.seconds // 60
            time_str = f"Há {minutes} minuto{'s' if minutes > 1 else ''}"
        
        activities.append({
            "type": "info",
            "title": "Abastecimento Realizado",
            "description": f"{fueling.equipment.name} - {fueling.quantity}L",
            "time": time_str,
            "date": fueling.date.isoformat()
        })
    
    # Equipamentos cadastrados recentemente (últimos 7 dias)
    recent_equipment = db.query(Equipment).filter(
        Equipment.created_at >= seven_days_ago
    ).order_by(Equipment.created_at.desc()).limit(3).all()
    
    for equipment in recent_equipment:
        # Calcular tempo relativo
        time_diff = datetime.now() - equipment.created_at
        if time_diff.days > 0:
            time_str = f"Há {time_diff.days} dia{'s' if time_diff.days > 1 else ''}"
        elif time_diff.seconds > 3600:
            hours = time_diff.seconds // 3600
            time_str = f"Há {hours} hora{'s' if hours > 1 else ''}"
        else:
            minutes = time_diff.seconds // 60
            time_str = f"Há {minutes} minuto{'s' if minutes > 1 else ''}"
        
        activities.append({
            "type": "primary",
            "title": "Equipamento Cadastrado",
            "description": f"{equipment.name} - {equipment.model or 'N/A'}",
            "time": time_str,
            "date": equipment.created_at.isoformat()
        })
    
    # Alertas de estoque baixo
    low_stock_materials = db.query(Material).filter(
        Material.current_stock <= Material.minimum_stock,
        Material.is_active == True
    ).limit(3).all()
    
    for material in low_stock_materials:
        activities.append({
            "type": "warning",
            "title": "Alerta de Estoque",
            "description": f"{material.name} - Estoque baixo ({material.current_stock} {material.unit})",
            "time": "Agora",
            "date": datetime.now().isoformat()
        })
    
    # Ordenar por data (mais recentes primeiro)
    activities.sort(key=lambda x: x["date"], reverse=True)
    
    # Retornar apenas os 10 mais recentes
    return {"success": True, "data": activities[:10]}

@router.get("/equipment-status")
async def get_equipment_status(db: Session = Depends(get_db)):
    """Status dos equipamentos"""
    equipments = db.query(Equipment).all()
    
    equipment_list = []
    for equipment in equipments:
        equipment_list.append({
            'name': equipment.name,
            'status': equipment.status or 'Operacional',
            'efficiency': 0,  # Será calculado quando houver dados
            'color': 'success' if equipment.status == 'Operacional' else 'warning'
        })
    
    return {
        'success': True,
        'data': equipment_list
    }

@router.get("/alerts")
async def get_system_alerts(db: Session = Depends(get_db)):
    """Alertas do sistema"""
    alerts = []
    
    # Verificar manutenções em atraso
    overdue_maintenance = db.query(WorkOrder).filter(
        and_(
            WorkOrder.status.in_(["Aberta", "Em andamento"]),
            WorkOrder.due_date < datetime.now()
        )
    ).count()
    
    if overdue_maintenance > 0:
        alerts.append({
            'type': 'warning',
            'title': 'Manutenções em Atraso',
            'message': f'{overdue_maintenance} manutenção(ões) em atraso',
            'timestamp': datetime.now().isoformat()
        })
    
    # Verificar materiais com baixo estoque (implementar quando houver lógica de estoque mínimo)
    low_stock = db.query(Material).filter(Material.current_stock < 10).count()
    
    if low_stock > 0:
        alerts.append({
            'type': 'info',
            'title': 'Estoque Baixo',
            'message': f'{low_stock} material(is) com estoque baixo',
            'timestamp': datetime.now().isoformat()
        })
    
    return {
        'success': True,
        'data': alerts
    }

@router.get("/performance-data")
async def get_performance_data(db: Session = Depends(get_db)):
    """Dados de performance para gráficos"""
    # Por enquanto, retornar dados básicos
    # Em produção, isso seria calculado com base em dados reais
    months = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 
             'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    
    # Dados básicos por enquanto
    efficiency_data = [0] * 12  # Todos zerados para banco limpo
    availability_data = [0] * 12  # Todos zerados para banco limpo
    
    performance_data = {
        'labels': months,
        'datasets': [
            {
                'label': 'Eficiência (%)',
                'data': efficiency_data,
                'borderColor': '#3498db',
                'backgroundColor': 'rgba(52, 152, 219, 0.1)',
                'borderWidth': 3,
                'fill': True,
                'tension': 0.4
            },
            {
                'label': 'Disponibilidade (%)',
                'data': availability_data,
                'borderColor': '#27ae60',
                'backgroundColor': 'rgba(39, 174, 96, 0.1)',
                'borderWidth': 3,
                'fill': True,
                'tension': 0.4
            }
        ]
    }
    
    return {
        'success': True,
        'data': performance_data
    }