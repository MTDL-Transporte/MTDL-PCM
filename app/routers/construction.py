"""
Router para módulo de Apropriação de Obra (Construção)
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from app.database import get_db
from app.templates_config import templates
from app.models.construction import MacroStage, SubStage, Task, TaskMeasurement
from sqlalchemy import func

router = APIRouter()

DEFAULT_MACROS = [
    ("Planejamento e Mobilização", 1),
    ("Infraestrutura Básica", 2),
    ("Estrutura Principal", 3),
    ("Instalações Técnicas", 4),
    ("Equipamentos e Sistemas Industriais", 5),
    ("Edificações Complementares", 6),
    ("Acabamentos e Revestimentos", 7),
    ("Testes, Comissionamento e Entrega", 8),
]

DEFAULT_SUBS = {
    "Planejamento e Mobilização": [
        ("Estudo de viabilidade e definição do escopo", 1),
        ("Elaboração de cronograma e orçamento", 2),
        ("Contratação de equipe e fornecedores", 3),
        ("Instalação do canteiro de obras", 4),
        ("Licenciamento e documentação técnica", 5),
    ],
    "Infraestrutura Básica": [
        ("Terraplenagem e sondagens", 1),
        ("Fundação (sapatas, estacas, blocos)", 2),
        ("Redes subterrâneas (água, esgoto, drenagem)", 3),
        ("Aterramento e compactação", 4),
    ],
    "Estrutura Principal": [
        ("Execução de pilares, vigas e lajes", 1),
        ("Estrutura metálica ou de concreto armado", 2),
        ("Contenção e elementos estruturais verticais", 3),
        ("Cobertura estrutural", 4),
    ],
    "Instalações Técnicas": [
        ("Instalações elétricas e hidráulicas", 1),
        ("Sistemas de gás, telefonia e dados", 2),
        ("Infraestrutura para climatização e ventilação", 3),
        ("Tubulações e dutos técnicos", 4),
    ],
    "Equipamentos e Sistemas Industriais": [
        ("Montagem de máquinas e equipamentos", 1),
        ("Sistemas automatizados e industriais", 2),
        ("Painéis de controle e instrumentação", 3),
        ("Testes de funcionamento", 4),
    ],
    "Edificações Complementares": [
        ("Construção de áreas de apoio (almoxarifado, vestiários, escritórios)", 1),
        ("Muros, cercas e portarias", 2),
        ("Urbanização externa (calçadas, paisagismo)", 3),
    ],
    "Acabamentos e Revestimentos": [
        ("Revestimentos internos e externos (pisos, paredes, tetos)", 1),
        ("Pintura, forros, esquadrias", 2),
        ("Instalação de portas, janelas e louças", 3),
        ("Detalhes decorativos e funcionais", 4),
    ],
    "Testes, Comissionamento e Entrega": [
        ("Testes de sistemas (elétrico, hidráulico, industrial)", 1),
        ("Comissionamento técnico e ajustes finais", 2),
        ("Limpeza pós-obra", 3),
        ("Vistoria e entrega oficial ao cliente", 4),
    ],
}

def ensure_default_construction_hierarchy(db: Session):
    # Seed de macroetapas
    existing_names = {m.name for m in db.query(MacroStage).all()}
    for name, order in DEFAULT_MACROS:
        if name not in existing_names:
            db.add(MacroStage(name=name, order=order))
    db.commit()

    # Seed de subetapas para as macroetapas com defaults
    for macro_name, subs in DEFAULT_SUBS.items():
        macro = db.query(MacroStage).filter(MacroStage.name == macro_name).first()
        if not macro:
            continue
        existing_sub_names = {s.name for s in db.query(SubStage).filter(SubStage.macro_stage_id == macro.id).all()}
        for sub_name, order in subs:
            if sub_name not in existing_sub_names:
                db.add(SubStage(macro_stage_id=macro.id, name=sub_name, order=order))
    db.commit()

@router.get("/construction/appropriation")
async def appropriation_page(request: Request, db: Session = Depends(get_db)):
    """Página principal do módulo Apropriação de Obra"""
    # Garantir hierarquia básica
    ensure_default_construction_hierarchy(db)

    # Carregar macroetapas -> subetapas -> tarefas
    macros = (
        db.query(MacroStage)
        .filter(MacroStage.is_active == True)
        .order_by(MacroStage.order, MacroStage.name)
        .all()
    )

    macro_data: List[Dict[str, Any]] = []
    for m in macros:
        subs = (
            db.query(SubStage)
            .filter(SubStage.macro_stage_id == m.id, SubStage.is_active == True)
            .order_by(SubStage.order, SubStage.name)
            .all()
        )
        sub_data = []
        for s in subs:
            tasks_raw = (
                db.query(Task)
                .filter(Task.sub_stage_id == s.id)
                .order_by(Task.created_at.desc())
                .all()
            )
            task_infos: List[Dict[str, Any]] = []
            for t in tasks_raw:
                try:
                    executed_qty = float(db.query(func.sum(TaskMeasurement.quantity_executed))
                                          .filter(TaskMeasurement.task_id == t.id)
                                          .scalar() or 0.0)
                except Exception:
                    executed_qty = 0.0
                planned = float(t.quantity_planned or 0.0)
                status_percent = (executed_qty / planned * 100.0) if planned > 0 else 0.0
                task_infos.append({
                    "id": t.id,
                    "name": t.name,
                    "task_type": t.task_type,
                    "start_date": t.start_date,
                    "end_date": t.end_date,
                    "unit": t.unit,
                    "quantity_planned": planned,
                    "executed_quantity": round(executed_qty, 2),
                    "status_percent": round(status_percent, 2),
                    "total_cost_planned": float(t.total_cost_planned or 0.0),
                })
            # calcular média da subetapa e cor
            avg = round(sum([ti["status_percent"] for ti in task_infos]) / len(task_infos), 2) if task_infos else 0.0
            color_class = "bg-success" if avg >= 100 else ("bg-primary" if avg > 50 else "bg-danger")
            sub_data.append({
                "id": s.id,
                "name": s.name,
                "contractual_value": getattr(s, "contractual_value", 0.0),
                "progress_avg": avg,
                "progress_color_class": color_class,
                "tasks": task_infos,
            })
        macro_data.append({
            "id": m.id,
            "name": m.name,
            "sub_stages": sub_data,
        })
    return templates.TemplateResponse(
        "construction/appropriation.html",
        {"request": request, "hierarchy": macro_data}
    )

@router.post("/api/construction/tasks")
async def create_task(payload: Dict[str, Any], db: Session = Depends(get_db)):
    """Criar uma tarefa dentro de uma subetapa"""
    try:
        sub_stage_id = int(payload.get("sub_stage_id"))
        name = (payload.get("name") or "").strip()
        task_type = (payload.get("task_type") or "").strip()
        unit = (payload.get("unit") or "unidade").strip()
        quantity_planned = float(payload.get("quantity_planned") or 0.0)
        notes = payload.get("notes")

        if not sub_stage_id or not name or not task_type:
            raise HTTPException(status_code=400, detail="Campos obrigatórios ausentes: sub_stage_id, name, task_type")

        # Datas (formatos: YYYY-MM-DD)
        start_date_str = payload.get("start_date")
        end_date_str = payload.get("end_date")
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date() if start_date_str else None
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date() if end_date_str else None

        labor_plan = payload.get("labor_plan") or []
        equipment_plan = payload.get("equipment_plan") or []

        # Calcular totais previstos
        total_labor = 0.0
        for lp in labor_plan:
            qty = float(lp.get("quantity") or 0.0)
            unit_value = float(lp.get("unit_value") or 0.0)
            total_labor += qty * unit_value

        total_equip = 0.0
        for ep in equipment_plan:
            qty = float(ep.get("quantity") or 0.0)
            tariff = float(ep.get("tariff") or 0.0)
            hours = float(ep.get("hours") or 0.0)
            total_equip += qty * tariff * hours

        task = Task(
            sub_stage_id=sub_stage_id,
            name=name,
            task_type=task_type,
            start_date=start_date,
            end_date=end_date,
            unit=unit,
            quantity_planned=quantity_planned,
            notes=notes,
            labor_plan=labor_plan,
            equipment_plan=equipment_plan,
            total_labor_planned=total_labor,
            total_equipment_planned=total_equip,
            total_cost_planned=(total_labor + total_equip),
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        return JSONResponse({
            "id": task.id,
            "message": "Tarefa criada com sucesso",
            "total_cost_planned": task.total_cost_planned,
        })
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao criar tarefa: {str(e)}")

@router.post("/api/construction/tasks/{task_id}/measurements")
async def add_task_measurement(task_id: int, payload: Dict[str, Any], db: Session = Depends(get_db)):
    """Registrar medição e recursos realizados para uma tarefa"""
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Tarefa não encontrada")

        date_str = payload.get("date")
        if not date_str:
            raise HTTPException(status_code=400, detail="Data da medição é obrigatória")
        measure_date = datetime.strptime(date_str, "%Y-%m-%d").date()

        quantity_executed = float(payload.get("quantity_executed") or 0.0)
        notes = payload.get("notes")
        photo_path = payload.get("photo_path")

        labor_realized = payload.get("labor_realized") or []
        equipment_used = payload.get("equipment_used") or []

        total_labor = 0.0
        for lr in labor_realized:
            qty = float(lr.get("quantity") or 0.0)
            unit_value = float(lr.get("unit_value") or 0.0)
            time_qty = float(lr.get("time_qty") or 0.0)
            total_labor += qty * unit_value * (time_qty if time_qty > 0 else 1)

        total_equip = 0.0
        for eu in equipment_used:
            hours = float(eu.get("hours") or 0.0)
            tariff = float(eu.get("tariff") or 0.0)
            total_equip += hours * tariff

        measurement = TaskMeasurement(
            task_id=task_id,
            date=measure_date,
            quantity_executed=quantity_executed,
            notes=notes,
            photo_path=photo_path,
            labor_realized=labor_realized,
            equipment_used=equipment_used,
            total_labor_realized=total_labor,
            total_equipment_realized=total_equip,
            total_cost_realized=(total_labor + total_equip),
        )
        db.add(measurement)
        db.commit()
        db.refresh(measurement)

        return JSONResponse({
            "id": measurement.id,
            "message": "Medição registrada com sucesso",
            "total_cost_realized": measurement.total_cost_realized,
        })
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao registrar medição: {str(e)}")

@router.post("/api/construction/substages")
async def create_substage(payload: Dict[str, Any], db: Session = Depends(get_db)):
    """Criar uma subetapa dentro de uma macroetapa"""
    try:
        macro_stage_id = int(payload.get("macro_stage_id"))
        name = (payload.get("name") or "").strip()
        order = int(payload.get("order") or 0)
        contractual_value = float(payload.get("contractual_value") or 0.0)
        
        if not macro_stage_id or not name:
            raise HTTPException(status_code=400, detail="Campos obrigatórios ausentes: macro_stage_id, name")
        
        macro = db.query(MacroStage).filter(MacroStage.id == macro_stage_id, MacroStage.is_active == True).first()
        if not macro:
            raise HTTPException(status_code=404, detail="Macroetapa não encontrada")
        
        sub = SubStage(
            macro_stage_id=macro_stage_id,
            name=name,
            order=order,
            contractual_value=contractual_value,
            is_active=True,
        )
        db.add(sub)
        db.commit()
        db.refresh(sub)
        return JSONResponse({"id": sub.id, "message": "Subetapa criada com sucesso"})
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao criar subetapa: {str(e)}")

@router.put("/api/construction/substages/{sub_stage_id}/contractual-value")
async def update_substage_contract(sub_stage_id: int, payload: Dict[str, Any], db: Session = Depends(get_db)):
    """Atualizar valor contratual da subetapa"""
    try:
        sub = db.query(SubStage).filter(SubStage.id == sub_stage_id).first()
        if not sub:
            raise HTTPException(status_code=404, detail="Subetapa não encontrada")
        
        contractual_value = payload.get("contractual_value")
        if contractual_value is None:
            raise HTTPException(status_code=400, detail="Valor contratual é obrigatório")
        
        sub.contractual_value = float(contractual_value)
        db.commit()
        db.refresh(sub)
        return {"success": True, "contractual_value": sub.contractual_value}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar valor contratual: {str(e)}")

@router.delete("/api/construction/substages/{sub_stage_id}")
async def delete_substage(sub_stage_id: int, db: Session = Depends(get_db)):
    """Excluir (inativar) uma subetapa"""
    try:
        sub = db.query(SubStage).filter(SubStage.id == sub_stage_id).first()
        if not sub:
            raise HTTPException(status_code=404, detail="Subetapa não encontrada")
        
        sub.is_active = False
        db.commit()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao excluir subetapa: {str(e)}")