"""
Router para módulo de almoxarifado
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Query, Body
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import List, Optional
from datetime import datetime, timedelta
# from weasyprint import HTML, CSS
# from weasyprint.text.fonts import FontConfiguration
import io
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from app.database import get_db
from app.models.warehouse import Material, StockMovement, Supplier, PurchaseRequest, PurchaseRequestItem, InventoryHistory, InventoryHistoryItem, Fueling, PurchaseOrder, PurchaseOrderQuotation
from app.schemas import warehouse as schemas
from app.templates_config import templates
from starlette.responses import RedirectResponse
from app.routers.admin import get_user_from_request_token, get_user_modules

router = APIRouter()

# Acesso: autenticação e licença do módulo Almoxarifado

def ensure_warehouse_access(request: Request, db: Session):
    user = get_user_from_request_token(request, db)
    if not user:
        return None, RedirectResponse(url="/admin/login", status_code=302)
    # Admin tem acesso irrestrito
    if user.is_admin:
        return user, None
    modules = get_user_modules(user.id, db)
    if "warehouse" in modules:
        return user, None
    raise HTTPException(status_code=403, detail="Acesso restrito ao módulo Almoxarifado")

def generate_inventory_number(db: Session) -> str:
    """Gera um número único de inventário no formato INV-YYYYMMDD-XXX"""
    from datetime import datetime
    
    # Formato: INV-YYYYMMDD-XXX (onde XXX é um contador sequencial do dia)
    today = datetime.now()
    date_prefix = today.strftime("INV-%Y%m%d")
    
    # Buscar o último inventário do dia para gerar o próximo número sequencial
    last_inventory = db.query(InventoryHistory).filter(
        InventoryHistory.inventory_number.like(f"{date_prefix}-%")
    ).order_by(InventoryHistory.inventory_number.desc()).first()
    
    if last_inventory:
        # Extrair o número sequencial do último inventário
        last_number = last_inventory.inventory_number.split("-")[-1]
        next_number = int(last_number) + 1
    else:
        # Primeiro inventário do dia
        next_number = 1
    
    # Formatar com 3 dígitos (001, 002, etc.)
    return f"{date_prefix}-{next_number:03d}"

def calculate_average_consumption(material_id: int, db: Session) -> float:
    """Calcular consumo médio baseado nas movimentações dos últimos 6 meses"""
    try:
        # Data de 6 meses atrás
        six_months_ago = datetime.now() - timedelta(days=180)
        
        # Buscar todas as saídas dos últimos 6 meses
        outbound_movements = db.query(StockMovement).filter(
            and_(
                StockMovement.material_id == material_id,
                StockMovement.type == "Saída",
                StockMovement.date >= six_months_ago
            )
        ).all()
        
        if not outbound_movements:
            return 0.0
        
        # Calcular total consumido
        total_consumed = sum(abs(movement.quantity) for movement in outbound_movements)
        
        # Calcular média mensal (total / 6 meses)
        average_monthly_consumption = total_consumed / 6
        
        return round(average_monthly_consumption, 2)
    except Exception:
        return 0.0

# Páginas HTML
@router.get("/materials")
async def materials(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    low_stock: bool = False,
    db: Session = Depends(get_db)
):
    """Página de materiais ou API"""
    # Verificar se é uma requisição para HTML ou JSON
    accept_header = request.headers.get("accept", "")

    if "text/html" in accept_header:
        # Checar autenticação e licença do módulo
        user, redirect = ensure_warehouse_access(request, db)
        if redirect:
            return redirect
        # Retornar página HTML
        return templates.TemplateResponse("warehouse/materials.html", {"request": request})
    else:
        # Retornar dados JSON formatados para formulários
        materials = db.query(Material).filter(Material.is_active == True).all()
        return [{"id": m.id, "code": m.code, "name": m.name, "unit": m.unit} for m in materials]

@router.get("/stock")
async def stock(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    low_stock_only: bool = False,
    db: Session = Depends(get_db)
):
    """Página de estoque ou API"""
    # Verificar se é uma requisição para HTML ou JSON
    accept_header = request.headers.get("accept", "")
    
    if "text/html" in accept_header:
        # Checar autenticação e licença do módulo
        user, redirect = ensure_warehouse_access(request, db)
        if redirect:
            return redirect
        # Retornar página HTML
        return templates.TemplateResponse("warehouse/stock.html", {"request": request})
    else:
        # Retornar dados JSON (API)
        query = db.query(Material)
        
        if low_stock_only:
            query = query.filter(Material.current_stock <= Material.minimum_stock)
        
        materials = query.offset(skip).limit(limit).all()
        
        # Formatar dados para incluir informações de estoque
        stock_data = []
        for material in materials:
            stock_data.append({
                "id": material.id,
                "name": material.name,
                "code": material.code,
                "category": material.category,
                "current_stock": material.current_stock,
                "minimum_stock": material.minimum_stock,
                "unit": material.unit,
                "unit_price": float(material.average_cost) if material.average_cost else 0,
                "location": material.location,
                "is_low_stock": material.current_stock <= material.minimum_stock
            })
        
        return stock_data

@router.get("/suppliers")
async def suppliers(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """Página de fornecedores ou API"""
    # Verificar se é uma requisição para HTML ou JSON
    accept_header = request.headers.get("accept", "")
    
    if "text/html" in accept_header:
        # Checar autenticação e licença do módulo
        user, redirect = ensure_warehouse_access(request, db)
        if redirect:
            return redirect
        # Retornar página HTML
        return templates.TemplateResponse("warehouse/suppliers.html", {"request": request})
    else:
        # Retornar dados JSON (API)
        query = db.query(Supplier)
        
        if active_only:
            query = query.filter(Supplier.is_active == True)
        
        suppliers = query.offset(skip).limit(limit).all()
        return suppliers

@router.get("/purchase_requests")
async def purchase_requests(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Página de requisições de compra (HTML)"""
    # Checar autenticação e licença do módulo
    user, redirect = ensure_warehouse_access(request, db)
    if redirect:
        return redirect
    # Sempre retornar página HTML
    return templates.TemplateResponse("warehouse/purchase_requests.html", {"request": request})

@router.get("/purchase-requests", response_model=List[schemas.PurchaseRequestResponse])
async def list_purchase_requests_api(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """API: Listar requisições de compra com filtro opcional por status"""
    query = db.query(PurchaseRequest)
    if status:
        query = query.filter(PurchaseRequest.status == status)
    requests = query.offset(skip).limit(limit).all()
    return [schemas.PurchaseRequestResponse.model_validate(r) for r in requests]


@router.get("/purchase_orders")
async def purchase_orders_page(request: Request, db: Session = Depends(get_db)):
    """Página de pedidos de compra"""
    user, redirect = ensure_warehouse_access(request, db)
    if redirect:
        return redirect
    return templates.TemplateResponse("warehouse/purchase_orders.html", {"request": request})

@router.get("/inventory")
async def inventory_page(request: Request, db: Session = Depends(get_db)):
    """Página de inventário físico"""
    user, redirect = ensure_warehouse_access(request, db)
    if redirect:
        return redirect
    return templates.TemplateResponse("warehouse/inventory.html", {"request": request})

# Inventory API Endpoints (for compatibility)
@router.get("/inventory/materials")
async def inventory_materials(db: Session = Depends(get_db)):
    """API para materiais do inventário com dados completos"""
    materials = db.query(Material).filter(Material.is_active == True).all()
    
    result = []
    for material in materials:
        result.append({
            "id": material.id,
            "code": material.code,
            "name": material.name,
            "description": material.description,
            "unit": material.unit,
            "unit_price": float(material.unit_price) if material.unit_price else 0.0,
            "minimum_stock": float(material.minimum_stock) if material.minimum_stock else 0.0,
            "maximum_stock": float(material.maximum_stock) if material.maximum_stock else 0.0,
            "current_stock": float(material.current_stock) if material.current_stock else 0.0,
            "location": material.location,
            "is_active": material.is_active,
            "category": material.category,
            "reference": material.reference
        })
    
    return result

@router.get("/inventory/stock")
async def inventory_stock(db: Session = Depends(get_db)):
    """API para estoque do inventário"""
    materials = db.query(Material).filter(Material.current_stock > 0).all()
    return [{"id": m.id, "name": m.name, "current_stock": m.current_stock, "minimum_stock": m.minimum_stock} for m in materials]

@router.get("/inventory/suppliers")
async def inventory_suppliers(db: Session = Depends(get_db)):
    """API para fornecedores do inventário"""
    suppliers = db.query(Supplier).filter(Supplier.active == True).all()
    return [{"id": s.id, "name": s.name, "contact": s.contact, "email": s.email} for s in suppliers]

@router.get("/materials/all")
async def get_all_materials(db: Session = Depends(get_db)):
    """API para obter todos os materiais com dados completos para a tabela"""
    materials = db.query(Material).filter(Material.is_active == True).all()
    
    result = []
    for material in materials:
        result.append({
            "id": material.id,
            "code": material.code,
            "name": material.name,
            "description": material.description,
            "unit": material.unit,
            "unit_price": float(material.unit_price) if material.unit_price else 0.0,
            "minimum_stock": float(material.minimum_stock) if material.minimum_stock else 0.0,
            "maximum_stock": float(material.maximum_stock) if material.maximum_stock else 0.0,
            "current_stock": float(material.current_stock) if material.current_stock else 0.0,
            "location": material.location,
            "is_active": material.is_active,
            "category": material.category,
            "reference": material.reference
        })
    
    return result

# API Endpoints - Materials

@router.post("/materials")
async def create_material(material_data: dict, db: Session = Depends(get_db)):
    """Criar novo material"""
    try:
        # Gerar código automaticamente a partir de 100000
        last_material = db.query(Material).order_by(Material.id.desc()).first()
        if last_material and last_material.code.isdigit():
            next_code = str(int(last_material.code) + 1)
        else:
            # Verificar se já existe algum material com código >= 100000
            max_code_material = db.query(Material).filter(
                Material.code.regexp_match(r'^\d+$')
            ).order_by(Material.code.desc()).first()
            
            if max_code_material and int(max_code_material.code) >= 100000:
                next_code = str(int(max_code_material.code) + 1)
            else:
                next_code = "100000"
        
        # Normalizar categoria de combustíveis para o singular
        raw_category = material_data.get("category")
        if raw_category:
            cat_norm = str(raw_category).strip().lower()
            if cat_norm in ("combustivel", "combustível", "combustiveis", "combustíveis", "fuel", "fuels"):
                material_data["category"] = "Combustível"
        
        material = Material(
            code=next_code,
            name=material_data.get("name"),
            description=material_data.get("description"),
            reference=material_data.get("reference"),
            category=material_data.get("category"),
            unit=material_data.get("unit"),
            minimum_stock=material_data.get("minimum_stock"),
            maximum_stock=material_data.get("maximum_stock"),
            location=material_data.get("location"),
            barcode=material_data.get("barcode")
        )
        db.add(material)
        db.commit()
        db.refresh(material)
        return {"message": "Material criado com sucesso", "id": material.id, "code": material.code}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/materials/search")
async def search_material_by_code(code: str, db: Session = Depends(get_db)):
    """Buscar material por código"""
    material = db.query(Material).filter(
        and_(
            Material.code == code,
            Material.is_active == True
        )
    ).first()
    
    if not material:
        return None
    
    return {
        "id": material.id,
        "code": material.code,
        "name": material.name,
        "description": material.description,
        "unit": material.unit,
        "current_stock": material.current_stock,
        "minimum_stock": material.minimum_stock,
        "maximum_stock": material.maximum_stock
    }

@router.get("/materials/{material_id}")
async def get_material(material_id: int, db: Session = Depends(get_db)):
    """Obter material específico"""
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material não encontrado")
    return material

@router.put("/materials/{material_id}")
async def update_material(
    material_id: int,
    material_data: dict,
    db: Session = Depends(get_db)
):
    """Atualizar material"""
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material não encontrado")
    
    for field, value in material_data.items():
        # Normalizar categoria de combustíveis para o singular
        if field == "category" and value:
            v = str(value).strip().lower()
            if v in ("combustivel", "combustível", "combustiveis", "combustíveis", "fuel", "fuels"):
                value = "Combustível"
        if hasattr(material, field):
            setattr(material, field, value)
    
    material.updated_at = datetime.now()
    db.commit()
    db.refresh(material)
    return material

# API Endpoints - Stock Movements
@router.get("/stock-movements")
async def get_all_stock_movements(
    skip: int = 0,
    limit: int = 100,
    material_id: Optional[int] = None,
    movement_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Listar todas as movimentações de estoque"""
    query = db.query(StockMovement)
    
    if material_id:
        query = query.filter(StockMovement.material_id == material_id)
    
    if movement_type:
        query = query.filter(StockMovement.type == movement_type)
    
    movements = query.order_by(StockMovement.date.desc()).offset(skip).limit(limit).all()
    
    # Incluir informações do material em cada movimentação
    result = []
    for movement in movements:
        material = db.query(Material).filter(Material.id == movement.material_id).first()
        result.append({
            "id": movement.id,
            "material_id": movement.material_id,
            "material_name": material.name if material else "Material não encontrado",
            "material_code": material.code if material else "N/A",
            "movement_type": movement.type,
            "quantity": float(movement.quantity) if movement.quantity is not None else 0.0,
            "unit_cost": float(movement.unit_cost) if hasattr(movement, "unit_cost") and movement.unit_cost is not None else None,
            "total_cost": float(movement.total_cost) if hasattr(movement, "total_cost") and movement.total_cost is not None else None,
            "reason": movement.reason,
            "reference_document": movement.reference_document,
            "notes": movement.notes,
            "date": movement.date.isoformat() if movement.date else None,
        })
    
    return result

@router.post("/materials/{material_id}/movements")
async def create_stock_movement(
    material_id: int,
    movement_data: dict,
    db: Session = Depends(get_db)
):
    """Criar movimentação de estoque"""
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material não encontrado")
    
    movement_type = movement_data["type"]
    quantity = movement_data["quantity"]
    
    # Validar quantidade para saída
    if movement_type == "Saída" and quantity > material.current_stock:
        raise HTTPException(
            status_code=400, 
            detail="Quantidade insuficiente em estoque"
        )
    
    # Calcular novo estoque
    previous_stock = material.current_stock
    if movement_type == "Entrada":
        new_stock = previous_stock + quantity
    elif movement_type == "Saída":
        new_stock = previous_stock - quantity
    else:  # Ajuste
        new_stock = quantity
    
    # Criar movimentação
    movement = StockMovement(
        material_id=material_id,
        type=movement_type,
        quantity=quantity,
        unit_cost=movement_data.get("unit_cost"),
        total_cost=movement_data.get("total_cost"),
        previous_stock=previous_stock,
        new_stock=new_stock,
        reference_document=movement_data.get("reference_document"),
        reason=movement_data.get("reason"),
        performed_by=movement_data.get("performed_by"),
        notes=movement_data.get("notes"),
        cost_center=movement_data.get("cost_center"),
        equipment_id=movement_data.get("equipment_id"),
        application=movement_data.get("application")
    )
    
    # Atualizar estoque do material
    material.current_stock = new_stock
    
    # Atualizar custo médio para entradas
    if movement_type == "Entrada" and movement_data.get("unit_cost"):
        total_value = (material.current_stock * material.average_cost) + movement_data["total_cost"]
        material.average_cost = total_value / new_stock if new_stock > 0 else 0
    
    material.updated_at = datetime.now()
    
    db.add(movement)
    db.commit()
    db.refresh(movement)
    
    # Recalcular consumo médio após a movimentação
    material.average_consumption = calculate_average_consumption(material_id, db)
    db.commit()
    
    return movement

@router.post("/recalculate-consumption")
async def recalculate_consumption(material_id: int, db: Session = Depends(get_db)):
    """Recalcular consumo médio de um material"""
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material não encontrado")
    
    # Recalcular consumo médio
    material.average_consumption = calculate_average_consumption(material_id, db)
    db.commit()
    
    return {"message": "Consumo médio recalculado com sucesso", "average_consumption": material.average_consumption}

@router.get("/materials/{material_id}/movements")
async def get_stock_movements(
    material_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Obter movimentações de um material"""
    movements = db.query(StockMovement).filter(
        StockMovement.material_id == material_id
    ).order_by(StockMovement.date.desc()).offset(skip).limit(limit).all()
    
    return movements

@router.post("/stock-movements")
async def create_stock_movement_new(movement_data: dict, db: Session = Depends(get_db)):
    """Criar nova movimentação de estoque"""
    try:
        material_id = movement_data.get("material_id")
        material = db.query(Material).filter(Material.id == material_id).first()
        
        if not material:
            raise HTTPException(status_code=404, detail="Material não encontrado")
        
        movement_type = movement_data.get("movement_type")
        quantity = float(movement_data.get("quantity"))
        reason = movement_data.get("reason")
        reference_document = movement_data.get("reference_document")
        notes = movement_data.get("notes", "")
        unit_price = movement_data.get("unit_price")
        # Data da movimentação (opcional)
        incoming_date = movement_data.get("date")
        if incoming_date:
            try:
                if isinstance(incoming_date, str):
                    try:
                        movement_date = datetime.fromisoformat(incoming_date)
                    except ValueError:
                        movement_date = datetime.strptime(incoming_date, "%Y-%m-%d")
                else:
                    movement_date = datetime.now()
            except Exception:
                raise HTTPException(status_code=400, detail="Formato de data inválido. Use YYYY-MM-DD ou ISO 8601.")
        else:
            movement_date = datetime.now()
        
        # Validar quantidade para saída
        if movement_type == "Saída" and quantity > material.current_stock:
            raise HTTPException(
                status_code=400, 
                detail=f"Quantidade insuficiente em estoque. Disponível: {material.current_stock}"
            )
        
        # Calcular novo estoque
        previous_stock = material.current_stock
        if movement_type == "Entrada":
            new_stock = previous_stock + quantity
        elif movement_type == "Saída":
            new_stock = previous_stock - quantity
        else:
            raise HTTPException(status_code=400, detail="Tipo de movimentação inválido")
        
        # Calcular custos
        unit_cost = float(unit_price) if unit_price else None
        total_cost = (quantity * unit_cost) if unit_cost else None
        
        # Criar movimentação
        movement = StockMovement(
            material_id=material_id,
            type=movement_type,
            quantity=quantity if movement_type == "Entrada" else -quantity,
            previous_stock=previous_stock,
            new_stock=new_stock,
            reference_document=reference_document,
            reason=reason,
            notes=notes,
            unit_cost=unit_cost,
            total_cost=total_cost,
            cost_center=movement_data.get("cost_center"),
            equipment_id=movement_data.get("equipment_id"),
            application=movement_data.get("application"),
            date=movement_date
        )
        
        # Atualizar estoque do material
        material.current_stock = new_stock
        material.updated_at = datetime.now()
        
        # Atualizar custo médio para movimentações de entrada com valor unitário
        if movement_type == "Entrada" and unit_price and unit_price > 0:
            current_value = (previous_stock * (material.average_cost or 0))
            new_value = quantity * unit_price
            total_value = current_value + new_value
            material.average_cost = total_value / new_stock if new_stock > 0 else unit_price
        
        db.add(movement)
        db.commit()
        db.refresh(movement)
        
        # Recalcular consumo médio após a movimentação
        material.average_consumption = calculate_average_consumption(material_id, db)
        
        # Se movimentação de saída for originada de notificação, atualizar status do item e da notificação
        try:
            if movement_type == "Saída":
                notif_id = movement_data.get("notification_id")
                item_id = movement_data.get("notification_item_id")
                if notif_id and item_id:
                    from app.models.warehouse import StockNotification, StockNotificationItem
                    item = db.query(StockNotificationItem).filter(
                        StockNotificationItem.id == item_id,
                        StockNotificationItem.notification_id == notif_id
                    ).first()
                    if item:
                        # Atualizar quantidade reservada acumulada
                        item.quantity_reserved = (item.quantity_reserved or 0.0) + quantity
                        # Definir status do item
                        if item.quantity_reserved >= item.quantity_needed:
                            item.status = "Entregue"
                        else:
                            item.status = "Reservado"
                        
                        # Verificar se todos os itens da notificação foram entregues
                        items = db.query(StockNotificationItem).filter(
                            StockNotificationItem.notification_id == notif_id
                        ).all()
                        if items and all(i.status == "Entregue" for i in items):
                            notification = db.query(StockNotification).filter(StockNotification.id == notif_id).first()
                            if notification:
                                notification.status = "Atendida"
                                notification.attended_at = datetime.now()
                                notification.attended_by = movement_data.get("attended_by", "Sistema")
                                # Acrescentar observações, se houver
                                note_extra = movement_data.get("notes") or ""
                                notification.notes = (notification.notes or "") + (f"\n{note_extra}" if note_extra else "")
        except Exception:
            # Não bloquear a movimentação caso a atualização da notificação falhe
            pass
        
        db.commit()
        
        return {
            "message": "Movimentação registrada com sucesso",
            "movement_id": movement.id,
            "new_stock": new_stock
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao processar movimentação: {str(e)}")

# API Endpoints - Suppliers

@router.post("/api/suppliers")
async def create_supplier(supplier_data: dict, db: Session = Depends(get_db)):
    """Criar novo fornecedor"""
    db_supplier = Supplier(**supplier_data)
    db.add(db_supplier)
    db.commit()
    db.refresh(db_supplier)
    return db_supplier

@router.get("/api/suppliers/{supplier_id}")
async def get_supplier(supplier_id: int, db: Session = Depends(get_db)):
    """Obter fornecedor específico"""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado")
    return supplier

# API Endpoints - Purchase Requests

@router.post("/purchase-requests", status_code=201)
async def create_purchase_request(request_data: dict, db: Session = Depends(get_db)):
    """Criar nova requisição de compra"""
    
    # Validar se o material existe e verificar estoque
    material_id = request_data.get("material_id")
    material = None
    if material_id:
        material = db.query(Material).filter(Material.id == material_id).first()
        if not material:
            raise HTTPException(status_code=404, detail="Material não encontrado")
        
        # Verificar se há estoque acima do mínimo
        if material.current_stock > material.minimum_stock:
            # Se não há justificativa para estoque disponível, retornar erro
            if not request_data.get("stock_justification"):
                raise HTTPException(
                    status_code=422, 
                    detail={
                        "message": "Existe saldo em estoque acima do mínimo. Favor justificar o motivo desta nova requisição.",
                        "current_stock": material.current_stock,
                        "minimum_stock": material.minimum_stock,
                        "requires_justification": True
                    }
                )
    
    # Gerar número sequencial
    last_request = db.query(PurchaseRequest).order_by(PurchaseRequest.id.desc()).first()
    if last_request:
        last_number = int(last_request.number.replace("RC", ""))
        new_number = f"RC{last_number + 1:06d}"
    else:
        new_number = "RC000001"
    
    # Filtrar e mapear campos válidos para PurchaseRequest
    request_fields = {
        "requester": request_data.get("requester"),
        "priority": request_data.get("priority", "Normal"),
        "justification": request_data.get("justification"),
        "cost_center": request_data.get("cost_center"),
        "stock_justification": request_data.get("stock_justification"),
    }

    db_request = PurchaseRequest(
        number=new_number,
        **{k: v for k, v in request_fields.items() if v is not None}
    )
    db.add(db_request)
    db.flush()  # obter ID da requisição para vincular itens

    # Criar item da requisição, se material e quantidade fornecidos
    if material_id and request_data.get("quantity"):
        unit_price = material.unit_price if material else 0.0
        quantity_val = float(request_data.get("quantity"))
        total_price = quantity_val * (unit_price or 0.0)

        db_item = PurchaseRequestItem(
            purchase_request_id=db_request.id,
            material_id=material_id,
            quantity=quantity_val,
            unit_price=unit_price,
            total_price=total_price
        )
        db.add(db_item)

        # Atualizar valor total da requisição
        db_request.total_value = total_price

    db.commit()
    db.refresh(db_request)
    return db_request

@router.get("/purchase-requests/{request_id}")
async def get_purchase_request(request_id: int, db: Session = Depends(get_db)):
    """Obter requisição de compra específica"""
    request = db.query(PurchaseRequest).filter(PurchaseRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Requisição não encontrada")
    return request

@router.get("/materials/{material_id}/stock-check")
async def check_material_stock(material_id: int, db: Session = Depends(get_db)):
    """Verificar estoque do material para validação de requisição"""
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material não encontrado")
    
    return {
        "material_id": material.id,
        "code": material.code,
        "description": material.description,
        "unit": material.unit,
        "current_stock": material.current_stock,
        "minimum_stock": material.minimum_stock,
        "requires_justification": material.current_stock > material.minimum_stock
    }

@router.get("/materials/by-code/{material_code}")
async def get_material_by_code(material_code: str, db: Session = Depends(get_db)):
    """Buscar material por código para preenchimento automático"""
    material = db.query(Material).filter(Material.code == material_code).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material não encontrado")
    
    return {
        "material_id": material.id,
        "code": material.code,
        "description": material.description,
        "unit": material.unit,
        "current_stock": material.current_stock,
        "minimum_stock": material.minimum_stock,
        "requires_justification": material.current_stock > material.minimum_stock
    }

@router.put("/purchase-requests/{request_id}/status")
async def update_purchase_request_status(
    request_id: int,
    status_data: dict,
    db: Session = Depends(get_db)
):
    """Atualizar status da requisição de compra"""
    request = db.query(PurchaseRequest).filter(PurchaseRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Requisição não encontrada")
    
    new_status = status_data["status"]
    request.status = new_status
    
    if new_status == "Aprovada":
        request.approved_date = datetime.now()
        request.approved_by = status_data.get("approved_by")
    
    db.commit()
    db.refresh(request)
    return request

# API Endpoints - Stock Notifications

@router.get("/stock-notifications")
async def get_stock_notifications(
    status: str = "Pendente",
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Obter notificações de estoque"""
    from app.models.warehouse import StockNotification, StockNotificationItem
    from app.models.equipment import Equipment
    from app.models.maintenance import MaintenancePlan, WorkOrder
    
    query = db.query(StockNotification)
    
    if status != "Todas":
        query = query.filter(StockNotification.status == status)
    
    notifications = query.order_by(StockNotification.created_at.desc()).offset(skip).limit(limit).all()
    
    result = []
    for notification in notifications:
        # Buscar dados relacionados
        equipment = db.query(Equipment).filter(Equipment.id == notification.equipment_id).first()
        work_order = db.query(WorkOrder).filter(WorkOrder.id == notification.work_order_id).first()
        maintenance_plan = db.query(MaintenancePlan).filter(MaintenancePlan.id == notification.maintenance_plan_id).first()
        
        # Buscar itens da notificação
        items = db.query(StockNotificationItem).filter(
            StockNotificationItem.notification_id == notification.id
        ).all()
        
        notification_data = {
            "id": notification.id,
            "work_order_id": notification.work_order_id,
            "work_order_number": (work_order.number if (work_order and work_order.number) else "N/A"),
            "equipment_name": (equipment.name if (equipment and equipment.name) else "N/A"),
            "equipment_prefix": (equipment.prefix if (equipment and equipment.prefix) else "N/A"),
            "maintenance_plan_name": (maintenance_plan.name if (maintenance_plan and maintenance_plan.name) else "N/A"),
            "status": notification.status,
            "priority": notification.priority,
            "message": notification.message,
            "created_at": notification.created_at.isoformat() if notification.created_at else None,
            "attended_at": notification.attended_at.isoformat() if notification.attended_at else None,
            "attended_by": notification.attended_by,
            "items": []
        }
        
        for item in items:
            material = db.query(Material).filter(Material.id == item.material_id).first()
            if material:
                notification_data["items"].append({
                    "id": item.id,
                    "material_id": item.material_id,
                    "material_code": material.code or "",
                    "material_name": material.name or "",
                    "material_unit": material.unit or "",
                    "quantity_needed": item.quantity_needed,
                    "quantity_available": item.quantity_available,
                    "quantity_reserved": item.quantity_reserved,
                    "status": item.status
                })
        
        result.append(notification_data)
    
    return result

@router.post("/stock-notifications/{notification_id}/attend")
async def attend_stock_notification(
    notification_id: int,
    attend_data: dict,
    db: Session = Depends(get_db)
):
    """Atender notificação de estoque - processar movimentação automática"""
    from app.models.warehouse import StockNotification, StockNotificationItem
    
    notification = db.query(StockNotification).filter(StockNotification.id == notification_id).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notificação não encontrada")
    
    if notification.status != "Pendente":
        raise HTTPException(status_code=400, detail="Notificação já foi atendida ou cancelada")
    
    # Buscar itens da notificação
    items = db.query(StockNotificationItem).filter(
        StockNotificationItem.notification_id == notification_id
    ).all()
    
    movements_created = []
    insufficient_stock = []
    
    try:
        for item in items:
            material = db.query(Material).filter(Material.id == item.material_id).first()
            if not material:
                continue
            
            # Verificar se há estoque suficiente
            if material.current_stock < item.quantity_needed:
                insufficient_stock.append({
                    "material_code": material.code,
                    "material_name": material.name,
                    "needed": item.quantity_needed,
                    "available": material.current_stock,
                    "missing": item.quantity_needed - material.current_stock
                })
                continue
            
            # Criar movimentação de saída
            movement = StockMovement(
                material_id=material.id,
                type="Saída",
                quantity=-item.quantity_needed,
                previous_stock=material.current_stock,
                new_stock=material.current_stock - item.quantity_needed,
                reference_document=f"OS-{notification.work_order_id}",
                reason="Manutenção Preventiva",
                notes=f"Movimentação automática para OS {notification.work_order_id} - {notification.message}",
                date=datetime.now()
            )
            
            # Atualizar estoque
            material.current_stock -= item.quantity_needed
            material.updated_at = datetime.now()
            
            # Atualizar status do item
            item.status = "Entregue"
            item.quantity_reserved = item.quantity_needed
            
            db.add(movement)
            movements_created.append({
                "material_code": material.code,
                "material_name": material.name,
                "quantity": item.quantity_needed,
                "new_stock": material.current_stock
            })
        
        # Se há materiais com estoque insuficiente, não processar nenhum
        if insufficient_stock:
            db.rollback()
            return {
                "success": False,
                "message": "Estoque insuficiente para alguns materiais",
                "insufficient_stock": insufficient_stock
            }
        
        # Atualizar status da notificação
        notification.status = "Atendida"
        notification.attended_at = datetime.now()
        notification.attended_by = attend_data.get("attended_by", "Sistema")
        notification.notes = attend_data.get("notes", "")
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Notificação atendida com sucesso. {len(movements_created)} movimentação(ões) criada(s).",
            "movements_created": movements_created
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao processar atendimento: {str(e)}")

@router.put("/stock-notifications/{notification_id}/status")
async def update_notification_status(
    notification_id: int,
    status_data: dict,
    db: Session = Depends(get_db)
):
    """Atualizar status da notificação"""
    from app.models.warehouse import StockNotification
    
    notification = db.query(StockNotification).filter(StockNotification.id == notification_id).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notificação não encontrada")
    
    notification.status = status_data["status"]
    if status_data["status"] == "Cancelada":
        notification.notes = status_data.get("notes", "")
    
    db.commit()
    db.refresh(notification)
    
    return {"message": "Status atualizado com sucesso", "notification": notification}

# API Endpoints - Reports
@router.get("/reports/low-stock")
async def get_low_stock_report(db: Session = Depends(get_db)):
    """Relatório de materiais com estoque baixo"""
    materials = db.query(Material).filter(
        and_(
            Material.current_stock <= Material.minimum_stock,
            Material.is_active == True
        )
    ).all()
    
    return [
        {
            "id": material.id,
            "code": material.code,
            "name": material.name,
            "current_stock": material.current_stock,
            "minimum_stock": material.minimum_stock,
            "difference": material.minimum_stock - material.current_stock,
            "unit": material.unit
        }
        for material in materials
    ]

@router.get("/reports/stock-value")
async def get_stock_value_report(db: Session = Depends(get_db)):
    """Relatório de valor do estoque"""
    materials = db.query(Material).filter(Material.is_active == True).all()
    
    total_value = 0
    items = []
    
    for material in materials:
        # Determinar custo efetivo: prioriza unit_price; se ausente/zero, usa average_cost
        effective_unit_cost = None
        try:
            effective_unit_cost = (
                float(material.unit_price) if material.unit_price and float(material.unit_price) > 0 else
                (float(material.average_cost) if material.average_cost else 0.0)
            )
        except Exception:
            effective_unit_cost = (material.unit_price or 0) or (material.average_cost or 0) or 0.0

        value = float(material.current_stock or 0) * float(effective_unit_cost or 0)
        total_value += value
        
        items.append({
            "code": material.code,
            "name": material.name,
            "stock": material.current_stock,
            "unit_cost": effective_unit_cost,
            "total_value": value,
            "unit": material.unit
        })
    
    return {
        "total_value": total_value,
        "items": sorted(items, key=lambda x: x["total_value"], reverse=True)
    }

# Inventory-specific API endpoints
@router.get("/api/inventory/materials-with-stock")
async def get_materials_with_stock(db: Session = Depends(get_db)):
    """API para obter materiais com saldo em estoque para inventário"""
    materials = db.query(Material).filter(
        and_(
            Material.is_active == True,
            Material.current_stock > 0
        )
    ).all()
    
    result = []
    for material in materials:
        result.append({
            "id": material.id,
            "code": material.code,
            "description": material.description,
            "unit": material.unit,
            "location": material.location,
            "current_stock": float(material.current_stock),
            "category": material.category,
            "physical_count": None  # Será preenchido pelo usuário
        })
    
    return result

@router.post("/api/inventory/process")
async def process_inventory(inventory_data: dict, db: Session = Depends(get_db)):
    """API para processar inventário e calcular acuracidade"""
    try:
        inventory_items = inventory_data.get("inventory_data", [])
        
        if not inventory_items:
            raise HTTPException(status_code=400, detail="Nenhum item de inventário fornecido")
        
        processed_items = 0
        correct_items = 0
        difference_items = 0
        adjustments = []
        
        # Processar cada item do inventário
        for item in inventory_items:
            material_id = item.get("material_id")
            current_stock = item.get("current_stock")
            physical_count = item.get("physical_count")
            
            # Buscar material no banco
            material = db.query(Material).filter(Material.id == material_id).first()
            if not material:
                continue
            
            processed_items += 1
            difference = physical_count - current_stock
            
            if difference == 0:
                correct_items += 1
            else:
                difference_items += 1
                
                # Registrar ajuste de estoque
                adjustments.append({
                    "material_code": material.code,
                    "material_description": material.description,
                    "previous_stock": current_stock,
                    "physical_count": physical_count,
                    "adjustment": difference
                })
                
                # Atualizar estoque no banco
                material.current_stock = physical_count
                
                # Criar movimento de estoque para o ajuste
                movement_type = "Entrada" if difference > 0 else "Saída"
                
                # Calcular previous_stock e new_stock
                previous_stock = current_stock
                new_stock = physical_count
                
                movement = StockMovement(
                    material_id=material_id,
                    type=movement_type,
                    quantity=abs(difference),
                    previous_stock=previous_stock,
                    new_stock=new_stock,
                    date=datetime.now(),
                    reason="Ajuste de Inventário",
                    notes=f"Ajuste por inventário físico. Diferença: {difference}"
                )
                db.add(movement)
        
        # Calcular acuracidade
        accuracy_percentage = round((correct_items / processed_items) * 100, 2) if processed_items > 0 else 0
        
        # Gerar número único de inventário
        inventory_number = generate_inventory_number(db)
        
        # Salvar histórico de inventário
        inventory_record = InventoryHistory(
            inventory_number=inventory_number,
            total_items=len(inventory_items),
            items_counted=processed_items,
            items_correct=correct_items,
            items_with_difference=difference_items,
            accuracy_percentage=accuracy_percentage,
            total_adjustments=len(adjustments),
            processed_by="Sistema",  # Pode ser melhorado para incluir usuário logado
            notes=f"Inventário processado com {processed_items} itens contados"
        )
        db.add(inventory_record)
        db.flush()  # Para obter o ID do inventário
        
        # Salvar itens do inventário
        for item in inventory_items:
            material_id = item.get("material_id")
            current_stock = item.get("current_stock")
            physical_count = item.get("physical_count")
            difference = physical_count - current_stock
            
            inventory_item = InventoryHistoryItem(
                inventory_id=inventory_record.id,
                material_id=material_id,
                system_stock=current_stock,
                physical_count=physical_count,
                difference=difference,
                adjustment_made=difference != 0
            )
            db.add(inventory_item)
        
        db.commit()
        
        return {
            "success": True,
            "inventory_number": inventory_number,
            "accuracy_percentage": accuracy_percentage,
            "processed_items": processed_items,
            "correct_items": correct_items,
            "difference_items": difference_items,
            "adjustments": adjustments,
            "process_date": datetime.now().isoformat()
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao processar inventário: {str(e)}")

@router.get("/api/inventory/accuracy-history")
async def get_accuracy_history(db: Session = Depends(get_db)):
    """API para obter histórico de acuracidade dos últimos 6 meses"""
    from datetime import datetime, timedelta
    import calendar
    from sqlalchemy import extract, func
    
    # Calcular data de 6 meses atrás
    six_months_ago = datetime.now() - timedelta(days=180)
    
    # Buscar inventários dos últimos 6 meses agrupados por mês
    inventories = db.query(
        extract('year', InventoryHistory.process_date).label('year'),
        extract('month', InventoryHistory.process_date).label('month'),
        func.avg(InventoryHistory.accuracy_percentage).label('avg_accuracy'),
        func.sum(InventoryHistory.items_counted).label('total_items_counted'),
        func.sum(InventoryHistory.items_with_difference).label('total_items_with_difference'),
        func.count(InventoryHistory.id).label('inventory_count')
    ).filter(
        InventoryHistory.process_date >= six_months_ago
    ).group_by(
        extract('year', InventoryHistory.process_date),
        extract('month', InventoryHistory.process_date)
    ).order_by(
        extract('year', InventoryHistory.process_date),
        extract('month', InventoryHistory.process_date)
    ).all()
    
    # Criar lista dos últimos 6 meses
    current_date = datetime.now()
    history = []
    
    for i in range(6):
        month_date = current_date - timedelta(days=30 * i)
        month_name = calendar.month_name[month_date.month]
        year = month_date.year
        month_number = month_date.month
        
        # Procurar dados reais para este mês
        month_data = next((inv for inv in inventories if inv.year == year and inv.month == month_number), None)
        
        if month_data:
            history.append({
                "month": f"{month_name} {year}",
                "month_number": month_number,
                "year": year,
                "accuracy_percentage": round(float(month_data.avg_accuracy), 2),
                "items_counted": int(month_data.total_items_counted),
                "items_with_difference": int(month_data.total_items_with_difference),
                "inventory_count": int(month_data.inventory_count)
            })
        else:
            # Se não há dados para este mês, retornar valores zerados
            history.append({
                "month": f"{month_name} {year}",
                "month_number": month_number,
                "year": year,
                "accuracy_percentage": 0.0,
                "items_counted": 0,
                "items_with_difference": 0,
                "inventory_count": 0
            })
    
    return list(reversed(history))  # Retornar em ordem cronológica

@router.get("/api/stock-metrics")
async def get_stock_metrics(db: Session = Depends(get_db)):
    """Métricas do estoque"""
    # Total de materiais
    total_materials = db.query(Material).filter(Material.is_active == True).count()
    
    # Materiais com estoque baixo (saldo abaixo do mínimo, excluindo os com estoque zero)
    low_stock = db.query(Material).filter(
        and_(
            Material.is_active == True,
            Material.current_stock < Material.minimum_stock,
            Material.current_stock > 0
        )
    ).count()
    
    # Materiais com estoque zero
    zero_stock = db.query(Material).filter(
        and_(
            Material.is_active == True,
            Material.current_stock == 0
        )
    ).count()
    
    # Valor total do estoque (usa unit_price; se zero/nulo, usa average_cost)
    materials = db.query(Material).filter(Material.is_active == True).all()
    total_value = 0.0
    for m in materials:
        try:
            unit_price = float(m.unit_price) if m.unit_price is not None else 0.0
        except Exception:
            unit_price = 0.0
        try:
            avg_cost = float(m.average_cost) if m.average_cost is not None else 0.0
        except Exception:
            avg_cost = 0.0
        effective_cost = unit_price if unit_price > 0 else avg_cost
        qty = float(m.current_stock) if m.current_stock is not None else 0.0
        total_value += qty * effective_cost
    
    # Movimentações do mês
    today = datetime.now()
    first_day_month = today.replace(day=1)
    monthly_movements = db.query(StockMovement).filter(
        StockMovement.date >= first_day_month
    ).count()
    
    return {
        "total_materials": total_materials,
        "low_stock": low_stock,
        "zero_stock": zero_stock,
        "total_value": float(total_value),
        "monthly_movements": monthly_movements
    }

# Temporariamente comentado devido a problemas com WeasyPrint
# @router.post("/api/inventory/export-pdf")
# async def export_inventory_pdf(filters: dict, db: Session = Depends(get_db)):
#     """Exportar tabela de inventário para PDF"""
#     try:
#         # Buscar materiais com estoque
#         query = db.query(Material).filter(
#             and_(
#                 Material.is_active == True,
#                 Material.current_stock > 0
#             )
#         )
#         
#         # Aplicar filtros se fornecidos
#         if filters.get("category"):
#             query = query.filter(Material.category == filters["category"])
#         if filters.get("location"):
#             query = query.filter(Material.location == filters["location"])
#         
#         materials = query.order_by(Material.code).all()
#         
#         # Gerar HTML para o PDF
#         html_content = generate_inventory_pdf_html(materials)
#         
#         # Configurar fonte
#         font_config = FontConfiguration()
#         
#         # CSS para o PDF
#         css_content = """
#         @page {
#             size: A4 landscape;
#             margin: 1cm;
#         }
#         body {
#             font-family: Arial, sans-serif;
#             font-size: 10px;
#             line-height: 1.2;
#         }
#         .header {
#             text-align: center;
#             margin-bottom: 20px;
#             border-bottom: 2px solid #333;
#             padding-bottom: 10px;
#         }
#         .company-name {
#             font-size: 18px;
#             font-weight: bold;
#             color: #333;
#         }
#         .document-title {
#             font-size: 14px;
#             margin-top: 5px;
#             color: #666;
#         }
#         .date-info {
#             font-size: 10px;
#             margin-top: 5px;
#             color: #888;
#         }
#         table {
#             width: 100%;
#             border-collapse: collapse;
#             margin-top: 10px;
#         }
#         th, td {
#             border: 1px solid #ddd;
#             padding: 6px;
#             text-align: left;
#         }
#         th {
#             background-color: #f5f5f5;
#             font-weight: bold;
#             font-size: 9px;
#         }
#         td {
#             font-size: 8px;
#         }
#         .code-col { width: 10%; }
#         .description-col { width: 35%; }
#         .unit-col { width: 8%; }
#         .location-col { width: 12%; }
#         .stock-col { width: 10%; text-align: center; }
#         .count-col { width: 15%; }
#         .signature-section {
#             margin-top: 30px;
#             page-break-inside: avoid;
#         }
#         .signature-box {
#             border: 1px solid #333;
#             height: 60px;
#             margin-top: 10px;
#         }
#         .footer {
#             position: fixed;
#             bottom: 1cm;
#             left: 1cm;
#             right: 1cm;
#             text-align: center;
#             font-size: 8px;
#             color: #666;
#         }
#         """
#         
#         # Gerar PDF
#         html_doc = HTML(string=html_content)
#         css_doc = CSS(string=css_content)
#         pdf_buffer = io.BytesIO()
#         html_doc.write_pdf(pdf_buffer, stylesheets=[css_doc], font_config=font_config)
#         pdf_buffer.seek(0)
#         
#         # Retornar PDF como resposta
#         return Response(
#             content=pdf_buffer.getvalue(),
#             media_type="application/pdf",
#             headers={"Content-Disposition": "attachment; filename=inventario.pdf"}
#         )
#         
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Erro ao gerar PDF: {str(e)}")

# def generate_inventory_pdf_html(materials):
#     """Gerar HTML para o PDF do inventário"""
#     now = datetime.now()
#     date_str = now.strftime("%d/%m/%Y às %H:%M")
#     
#     html = f"""
#     <!DOCTYPE html>
#     <html>
#     <head>
#         <meta charset="UTF-8">
#         <title>Inventário de Materiais</title>
#     </head>
#     <body>
#         <div class="header">
#             <div class="company-name">MTDL PCM - Sistema de Gestão</div>
#             <div class="document-title">FOLHA DE INVENTÁRIO FÍSICO</div>
#             <div class="date-info">Gerado em: {date_str}</div>
#         </div>
#         
#         <table>
#             <thead>
#                 <tr>
#                     <th class="code-col">Código</th>
#                     <th class="description-col">Descrição</th>
#                     <th class="unit-col">Unidade</th>
#                     <th class="location-col">Localização</th>
#                     <th class="stock-col">Saldo Sistema</th>
#                     <th class="count-col">Contagem Física</th>
#                 </tr>
#             </thead>
#             <tbody>
#     """
#     
#     for material in materials:
#         html += f"""
#                 <tr>
#                     <td>{material.code}</td>
#                     <td>{material.description}</td>
#                     <td>{material.unit}</td>
#                     <td>{material.location or '-'}</td>
#                     <td style="text-align: center;">{material.current_stock}</td>
#                     <td style="border: 2px solid #333; height: 25px;"></td>
#                 </tr>
#         """
#     
#     html += """
#             </tbody>
#         </table>
#         
#         <div class="signature-section">
#             <p><strong>Responsável pela Contagem:</strong></p>
#             <div class="signature-box"></div>
#             <p style="margin-top: 5px;">Nome: _________________________ Assinatura: _________________________ Data: ___/___/______</p>
#             
#             <p style="margin-top: 20px;"><strong>Supervisor/Conferente:</strong></p>
#             <div class="signature-box"></div>
#             <p style="margin-top: 5px;">Nome: _________________________ Assinatura: _________________________ Data: ___/___/______</p>
#         </div>
#         
#         <div class="footer">
#             <p>MTDL PCM - Sistema de Gestão de Almoxarifado | Página gerada automaticamente</p>
#         </div>
#     </body>
#     </html>
#     """
#     
#     return html

# ==================== ROTAS PARA ABASTECIMENTO ====================

@router.get("/fueling")
async def fueling_page(request: Request, db: Session = Depends(get_db)):
    """Página principal do módulo de abastecimento"""
    user, redirect = ensure_warehouse_access(request, db)
    if redirect:
        return redirect
    return templates.TemplateResponse("warehouse/fueling.html", {"request": request})

@router.get("/fueling/list")
async def get_fuelings(
    skip: int = 0,
    limit: int = 100,
    equipment_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Listar abastecimentos com filtros opcionais"""
    try:
        query = db.query(Fueling)
        
        if equipment_id:
            query = query.filter(Fueling.equipment_id == equipment_id)
        
        fuelings = query.order_by(Fueling.date.desc()).offset(skip).limit(limit).all()
        
        result = []
        for fueling in fuelings:
            result.append({
                "id": fueling.id,
                "equipment_id": fueling.equipment_id,
                "equipment_name": fueling.equipment.name if fueling.equipment else "N/A",
                "equipment_prefix": fueling.equipment.prefix if fueling.equipment else "N/A",
                "material_id": fueling.material_id,
                "fuel_type": fueling.material.description if fueling.material else "N/A",
                "date": fueling.date.isoformat() if fueling.date else None,
                "quantity": fueling.quantity,
                "horimeter": fueling.horimeter,
                "unit_cost": fueling.unit_cost,
                "total_cost": fueling.total_cost,
                "operator": fueling.operator,
                "notes": fueling.notes
            })
        
        return {"fuelings": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar abastecimentos: {str(e)}")

@router.post("/fueling")
async def create_fueling(fueling_data: dict, db: Session = Depends(get_db)):
    """Criar novo registro de abastecimento"""
    try:
        # Validar dados obrigatórios
        required_fields = ["equipment_id", "material_id", "quantity", "horimeter"]
        for field in required_fields:
            if field not in fueling_data or fueling_data[field] is None:
                raise HTTPException(status_code=400, detail=f"Campo obrigatório: {field}")
        
        # Verificar se o equipamento existe
        from app.models.equipment import Equipment
        equipment = db.query(Equipment).filter(Equipment.id == fueling_data["equipment_id"]).first()
        if not equipment:
            raise HTTPException(status_code=404, detail="Equipamento não encontrado")
        
        # Verificar se o material (combustível) existe
        material = db.query(Material).filter(Material.id == fueling_data["material_id"]).first()
        if not material:
            raise HTTPException(status_code=404, detail="Material não encontrado")
        
        # Validar horímetro em ordem crescente
        last_fueling = db.query(Fueling).filter(
            Fueling.equipment_id == fueling_data["equipment_id"]
        ).order_by(Fueling.horimeter.desc()).first()
        
        if last_fueling and fueling_data["horimeter"] <= last_fueling.horimeter:
            raise HTTPException(
                status_code=400, 
                detail=f"Horímetro deve ser maior que o último registro ({last_fueling.horimeter})"
            )
        
        # Calcular custo total se fornecido custo unitário
        total_cost = None
        if fueling_data.get("unit_cost"):
            total_cost = fueling_data["unit_cost"] * fueling_data["quantity"]
        
        # Criar registro de abastecimento
        fueling = Fueling(
            equipment_id=fueling_data["equipment_id"],
            material_id=fueling_data["material_id"],
            date=datetime.fromisoformat(fueling_data["date"]) if fueling_data.get("date") else datetime.now(),
            quantity=fueling_data["quantity"],
            horimeter=fueling_data["horimeter"],
            unit_cost=fueling_data.get("unit_cost"),
            total_cost=total_cost,
            operator=fueling_data.get("operator"),
            notes=fueling_data.get("notes")
        )
        
        db.add(fueling)
        
        # Criar movimentação de estoque (saída do combustível)
        stock_movement = StockMovement(
            material_id=fueling_data["material_id"],
            type="Saída",
            quantity=fueling_data["quantity"],
            unit_cost=fueling_data.get("unit_cost", 0),
            total_cost=total_cost or 0,
            previous_stock=material.current_stock,
            new_stock=material.current_stock - fueling_data["quantity"],
            reference_document="Abastecimento",
            reason=f"Abastecimento - {equipment.prefix} - {equipment.name}",
            performed_by=fueling_data.get("operator", "Sistema"),
            notes=f"Abastecimento - {equipment.prefix} - {equipment.name}"
        )
        
        db.add(stock_movement)
        db.commit()
        
        # Atualizar reference_id da movimentação
        stock_movement.reference_id = fueling.id
        db.commit()
        
        # Atualizar horímetro do equipamento
        equipment.current_horimeter = fueling_data["horimeter"]
        db.commit()
        
        # Verificar se precisa gerar ordem de manutenção
        await check_maintenance_schedule(equipment.id, fueling_data["horimeter"], db)
        
        return {
            "message": "Abastecimento registrado com sucesso",
            "fueling_id": fueling.id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao registrar abastecimento: {str(e)}")

@router.get("/fueling/{fueling_id}")
async def get_fueling(fueling_id: int, db: Session = Depends(get_db)):
    """Obter detalhes de um abastecimento específico"""
    fueling = db.query(Fueling).filter(Fueling.id == fueling_id).first()
    if not fueling:
        raise HTTPException(status_code=404, detail="Abastecimento não encontrado")
    
    return {
        "id": fueling.id,
        "equipment_id": fueling.equipment_id,
        "equipment_name": fueling.equipment.name if fueling.equipment else "N/A",
        "equipment_prefix": fueling.equipment.prefix if fueling.equipment else "N/A",
        "material_id": fueling.material_id,
        "fuel_type": fueling.material.description if fueling.material else "N/A",
        "date": fueling.date.isoformat() if fueling.date else None,
        "quantity": fueling.quantity,
        "horimeter": fueling.horimeter,
        "unit_cost": fueling.unit_cost,
        "total_cost": fueling.total_cost,
        "operator": fueling.operator,
        "notes": fueling.notes
    }

@router.get("/equipment/for-fueling")
async def get_equipment_for_fueling(db: Session = Depends(get_db)):
    """Listar equipamentos disponíveis para abastecimento"""
    try:
        from app.models.equipment import Equipment
        equipments = db.query(Equipment).filter(Equipment.status == "ativo").all()
        
        result = []
        for equipment in equipments:
            result.append({
                "id": equipment.id,
                "name": equipment.name,
                "prefix": equipment.prefix,
                "current_horimeter": equipment.current_horimeter or 0
            })
        
        return {"equipments": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar equipamentos: {str(e)}")

@router.get("/fuels")
async def get_fuel_materials(db: Session = Depends(get_db)):
    """Listar materiais da categoria Combustíveis"""
    try:
        from sqlalchemy import func
        from app.models.warehouse import StockMovement
        from datetime import datetime, timedelta
        
        fuels = db.query(Material).filter(
            Material.is_active == True,
            Material.category.in_(["Combustível", "Combustíveis"])
        ).all()
        
        # Data limite para os últimos 60 dias
        sixty_days_ago = datetime.now() - timedelta(days=60)
        
        result = []
        for fuel in fuels:
            # Calcular preço médio das entradas dos últimos 60 dias
            avg_price_result = db.query(
                func.avg(StockMovement.unit_cost).label('avg_price')
            ).filter(
                StockMovement.material_id == fuel.id,
                StockMovement.type == 'Entrada',
                StockMovement.unit_cost > 0,
                StockMovement.date >= sixty_days_ago
            ).first()
            
            avg_price = float(avg_price_result.avg_price) if avg_price_result.avg_price else 0.0
            
            result.append({
                "id": fuel.id,
                "code": fuel.code,
                "name": fuel.name,
                "description": fuel.description,
                "unit": fuel.unit,
                "current_stock": fuel.current_stock,
                "unit_price": fuel.unit_price or 0,
                "average_price": round(avg_price, 2)
            })
        
        return {"fuels": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar combustíveis: {str(e)}")

async def check_maintenance_schedule(equipment_id: int, current_horimeter: float, db: Session):
    """Verificar se é necessário gerar ordem de manutenção baseada no horímetro"""
    try:
        from app.models.equipment import Equipment
        from app.routers.maintenance import check_and_create_preventive_maintenance
        
        # Buscar equipamento
        equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
        if not equipment:
            return None
        
        # Atualizar horímetro atual do equipamento
        equipment.current_horimeter = current_horimeter
        db.commit()
        
        # Usar a função centralizada de verificação de manutenção preventiva
        result = await check_and_create_preventive_maintenance(equipment, db)
        
        return result
                    
    except Exception as e:
        print(f"Erro ao verificar cronograma de manutenção: {str(e)}")
        return None

async def create_maintenance_notification(equipment_id: int, plan_id: int, notification_type: str, db: Session):
    """Criar notificação de manutenção"""
    # Implementar sistema de notificações
    pass

async def create_automatic_work_order(equipment_id: int, plan_id: int, current_horimeter: float, db: Session):
    """Criar ordem de serviço automaticamente"""
    try:
        from app.models.maintenance import WorkOrder, MaintenancePlan
        
        plan = db.query(MaintenancePlan).filter(MaintenancePlan.id == plan_id).first()
        if not plan:
            return
        
        # Verificar se já existe ordem pendente para este plano
        existing_order = db.query(WorkOrder).filter(
            WorkOrder.equipment_id == equipment_id,
            WorkOrder.maintenance_plan_id == plan_id,
            WorkOrder.status.in_(["Pendente", "Em Andamento"])
        ).first()
        
        if existing_order:
            return  # Já existe ordem pendente
        
        # Gerar número da ordem
        order_count = db.query(WorkOrder).count() + 1
        order_number = f"OS-{order_count:06d}"
        
        # Criar ordem de serviço
        work_order = WorkOrder(
            order_number=order_number,
            equipment_id=equipment_id,
            maintenance_plan_id=plan_id,
            description=f"Manutenção Preventiva - {plan.description}",
            priority="Normal",
            status="Pendente",
            scheduled_date=datetime.now(),
            estimated_hours=plan.estimated_hours or 0,
            notes=f"Ordem gerada automaticamente - Horímetro: {current_horimeter}"
        )
        
        db.add(work_order)
        db.commit()
        
    except Exception as e:
        print(f"Erro ao criar ordem de serviço automática: {str(e)}")

@router.get("/fuels/{fuel_id}/average-price")
async def get_fuel_average_price(fuel_id: int, db: Session = Depends(get_db)):
    """Obter preço médio de um combustível baseado nas entradas de estoque dos últimos 60 dias"""
    try:
        from sqlalchemy import func
        from app.models.warehouse import StockMovement
        from datetime import datetime, timedelta
        
        # Data limite para os últimos 60 dias
        sixty_days_ago = datetime.now() - timedelta(days=60)
        
        # Calcular preço médio das entradas dos últimos 60 dias
        result = db.query(
            func.avg(StockMovement.unit_cost).label('avg_price'),
            func.count(StockMovement.id).label('count_entries')
        ).filter(
            StockMovement.material_id == fuel_id,
            StockMovement.type == 'Entrada',
            StockMovement.unit_cost > 0,
            StockMovement.date >= sixty_days_ago
        ).first()
        
        avg_price = float(result.avg_price) if result.avg_price else 0.0
        count_entries = result.count_entries or 0
        
        return {
            "fuel_id": fuel_id,
            "average_price": round(avg_price, 2),
            "entries_count": count_entries,
            "period_days": 60
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao calcular preço médio: {str(e)}")

# Rotas para Pedidos de Compra
@router.post("/purchase-orders", response_model=schemas.PurchaseOrderResponse, status_code=201)
async def create_purchase_order(
    purchase_order: schemas.PurchaseOrderCreate,
    db: Session = Depends(get_db)
):
    """Criar um novo pedido de compra"""
    try:
        # Verificar se a requisição existe
        purchase_request = db.query(PurchaseRequest).filter(
            PurchaseRequest.id == purchase_order.purchase_request_id
        ).first()
        
        if not purchase_request:
            raise HTTPException(status_code=404, detail="Requisição de compra não encontrada")
        
        # Verificar se já existe pedido para esta requisição
        existing_order = db.query(PurchaseOrder).filter(
            PurchaseOrder.purchase_request_id == purchase_order.purchase_request_id
        ).first()
        
        if existing_order:
            raise HTTPException(status_code=400, detail="Já existe um pedido de compra para esta requisição")
        
        # Gerar número sequencial para o pedido
        last_order = db.query(PurchaseOrder).order_by(PurchaseOrder.id.desc()).first()
        next_number = (last_order.id + 1) if last_order else 1
        order_number = f"PC{next_number:06d}"
        
        # Criar o pedido de compra
        db_purchase_order = PurchaseOrder(
            number=order_number,
            purchase_request_id=purchase_order.purchase_request_id,
            supplier_id=purchase_order.supplier_id,
            status="Pendente",
            total_value=purchase_order.total_value,
            delivery_date=purchase_order.delivery_date,
            payment_terms=purchase_order.payment_terms,
            notes=purchase_order.notes,
            created_by="Sistema",
            created_at=datetime.now()
        )
        
        db.add(db_purchase_order)
        db.commit()
        db.refresh(db_purchase_order)
        
        return db_purchase_order
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao criar pedido de compra: {str(e)}")

@router.get("/purchase-orders", response_model=List[schemas.PurchaseOrderResponse])
async def get_purchase_orders(
    skip: int = 0,
    limit: int = 100,
    status: str = Query(None, description="Filtrar por status"),
    db: Session = Depends(get_db)
):
    """Obter lista de pedidos de compra"""
    try:
        query = db.query(PurchaseOrder)
        
        if status:
            query = query.filter(PurchaseOrder.status == status)
        
        purchase_orders = query.order_by(PurchaseOrder.created_at.desc()).offset(skip).limit(limit).all()
        
        return purchase_orders
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter pedidos de compra: {str(e)}")

@router.get("/purchase-orders/{order_id}", response_model=schemas.PurchaseOrderResponse)
async def get_purchase_order(order_id: int, db: Session = Depends(get_db)):
    """Obter um pedido de compra específico"""
    purchase_order = db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
    
    if not purchase_order:
        raise HTTPException(status_code=404, detail="Pedido de compra não encontrado")
    
    return purchase_order

@router.put("/purchase-orders/{order_id}/status")
async def update_purchase_order_status(
    order_id: int,
    status: str = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """Atualizar status de um pedido de compra"""
    try:
        purchase_order = db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
        
        if not purchase_order:
            raise HTTPException(status_code=404, detail="Pedido de compra não encontrado")
        
        valid_statuses = ["Pendente", "Enviado", "Confirmado", "Entregue", "Cancelado"]
        if status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Status inválido. Use: {', '.join(valid_statuses)}")
        
        purchase_order.status = status
        purchase_order.updated_at = datetime.now()
        
        db.commit()
        
        return {"message": "Status atualizado com sucesso", "status": status}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar status: {str(e)}")

@router.post("/purchase-orders/{order_id}/quotations", response_model=schemas.PurchaseOrderQuotationResponse)
async def create_quotation(
    order_id: int,
    quotation: schemas.PurchaseOrderQuotationCreate,
    db: Session = Depends(get_db)
):
    """Criar uma cotação para um pedido de compra"""
    try:
        # Verificar se o pedido existe
        purchase_order = db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
        
        if not purchase_order:
            raise HTTPException(status_code=404, detail="Pedido de compra não encontrado")
        
        # Verificar se já existe cotação deste fornecedor para este pedido
        existing_quotation = db.query(PurchaseOrderQuotation).filter(
            PurchaseOrderQuotation.purchase_order_id == order_id,
            PurchaseOrderQuotation.supplier_id == quotation.supplier_id
        ).first()
        
        if existing_quotation:
            raise HTTPException(status_code=400, detail="Já existe uma cotação deste fornecedor para este pedido")
        
        # Criar a cotação
        db_quotation = PurchaseOrderQuotation(
            purchase_order_id=order_id,
            supplier_id=quotation.supplier_id,
            supplier_name=quotation.supplier_name,
            contact_name=quotation.contact_name,
            contact_phone=quotation.contact_phone,
            total_value=quotation.total_value,
            delivery_time=quotation.delivery_time,
            payment_terms=quotation.payment_terms,
            notes=quotation.notes,
            created_at=datetime.now()
        )
        
        db.add(db_quotation)
        db.commit()
        db.refresh(db_quotation)
        
        return db_quotation
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao criar cotação: {str(e)}")

@router.get("/purchase-orders/{order_id}/quotations", response_model=List[schemas.PurchaseOrderQuotationResponse])
async def get_quotations(order_id: int, db: Session = Depends(get_db)):
    """Obter cotações de um pedido de compra"""
    try:
        # Verificar se o pedido existe
        purchase_order = db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
        
        if not purchase_order:
            raise HTTPException(status_code=404, detail="Pedido de compra não encontrado")
        
        quotations = db.query(PurchaseOrderQuotation).filter(
            PurchaseOrderQuotation.purchase_order_id == order_id
        ).order_by(PurchaseOrderQuotation.total_value.asc()).all()
        
        return quotations
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter cotações: {str(e)}")

@router.get("/purchase-requests/{request_id}/eligible-for-order")
async def check_request_eligible_for_order(request_id: int, db: Session = Depends(get_db)):
    """Verificar se uma requisição está elegível para gerar pedido de compra"""
    try:
        # Verificar se a requisição existe
        purchase_request = db.query(PurchaseRequest).filter(
            PurchaseRequest.id == request_id
        ).first()
        
        if not purchase_request:
            raise HTTPException(status_code=404, detail="Requisição de compra não encontrada")
        
        # Verificar se já existe pedido para esta requisição
        existing_order = db.query(PurchaseOrder).filter(
            PurchaseOrder.purchase_request_id == request_id
        ).first()
        
        eligible = (
            purchase_request.status == "Aprovada" and 
            existing_order is None
        )
        
        return {
            "request_id": request_id,
            "eligible": eligible,
            "status": purchase_request.status,
            "has_existing_order": existing_order is not None,
            "existing_order_id": existing_order.id if existing_order else None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao verificar elegibilidade: {str(e)}")

@router.put("/quotations/{quotation_id}/select")
async def select_quotation(quotation_id: int, db: Session = Depends(get_db)):
    """Selecionar uma cotação como a escolhida"""
    try:
        # Verificar se a cotação existe
        quotation = db.query(PurchaseOrderQuotation).filter(
            PurchaseOrderQuotation.id == quotation_id
        ).first()
        
        if not quotation:
            raise HTTPException(status_code=404, detail="Cotação não encontrada")
        
        # Desmarcar todas as outras cotações do mesmo pedido
        db.query(PurchaseOrderQuotation).filter(
            PurchaseOrderQuotation.purchase_order_id == quotation.purchase_order_id
        ).update({"is_selected": False})
        
        # Marcar esta cotação como selecionada
        quotation.is_selected = True
        
        # Atualizar o valor total do pedido com a cotação selecionada
        purchase_order = db.query(PurchaseOrder).filter(
            PurchaseOrder.id == quotation.purchase_order_id
        ).first()
        
        if purchase_order:
            purchase_order.total_value = quotation.total_value
            purchase_order.supplier_id = quotation.supplier_id
        
        db.commit()
        
        return {"message": "Cotação selecionada com sucesso", "quotation_id": quotation_id}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao selecionar cotação: {str(e)}")

@router.delete("/quotations/{quotation_id}")
async def delete_quotation(quotation_id: int, db: Session = Depends(get_db)):
    """Excluir uma cotação"""
    try:
        # Verificar se a cotação existe
        quotation = db.query(PurchaseOrderQuotation).filter(
            PurchaseOrderQuotation.id == quotation_id
        ).first()
        
        if not quotation:
            raise HTTPException(status_code=404, detail="Cotação não encontrada")
        
        # Verificar se a cotação está selecionada
        if quotation.is_selected:
            raise HTTPException(status_code=400, detail="Não é possível excluir uma cotação selecionada")
        
        db.delete(quotation)
        db.commit()
        
        return {"message": "Cotação excluída com sucesso", "quotation_id": quotation_id}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao excluir cotação: {str(e)}")

@router.get("/purchase-orders/{order_id}/pdf")
async def generate_purchase_order_pdf(order_id: int, db: Session = Depends(get_db)):
    """Gerar PDF do pedido de compra"""
    try:
        # Buscar pedido e relacionamentos básicos
        purchase_order = db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
        if not purchase_order:
            raise HTTPException(status_code=404, detail="Pedido de compra não encontrado")
        
        supplier = purchase_order.supplier
        req = purchase_order.purchase_request

        # Buffer para PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm
        )

        # Estilos
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'PO_Title',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=colors.black
        )
        heading_style = ParagraphStyle(
            'PO_Heading',
            parent=styles['Heading2'],
            fontSize=12,
            spaceAfter=10,
            textColor=colors.black
        )
        normal_style = styles['Normal']

        story = []
        # Título
        story.append(Paragraph("PEDIDO DE COMPRA", title_style))
        story.append(Spacer(1, 12))

        # Info básica
        created_at_str = purchase_order.created_at.strftime('%d/%m/%Y') if purchase_order.created_at else ''
        po_info_data = [
            ['Pedido Nº:', purchase_order.number, 'Data:', created_at_str],
            ['Status:', purchase_order.status, 'Requisição Nº:', req.number if req else '']
        ]
        info_table = Table(po_info_data, colWidths=[3*cm, 6*cm, 3*cm, 4*cm])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 14))

        # Fornecedor
        story.append(Paragraph("Fornecedor", heading_style))
        supplier_name = supplier.name if supplier else ''
        supplier_cnpj = getattr(supplier, 'cnpj', '') if supplier else ''
        supplier_phone = getattr(supplier, 'phone', '') if supplier else ''
        supplier_email = getattr(supplier, 'email', '') if supplier else ''
        supplier_address = getattr(supplier, 'address', '') if supplier else ''
        supplier_data = [
            ['Nome:', supplier_name, 'CNPJ:', supplier_cnpj],
            ['Telefone:', supplier_phone, 'E-mail:', supplier_email],
            ['Endereço:', supplier_address, '', '']
        ]
        supplier_table = Table(supplier_data, colWidths=[3*cm, 6*cm, 3*cm, 4*cm])
        supplier_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(supplier_table)
        story.append(Spacer(1, 14))

        # Resumo do Pedido
        story.append(Paragraph("Resumo do Pedido", heading_style))
        delivery_date_str = purchase_order.delivery_date.strftime('%d/%m/%Y') if purchase_order.delivery_date else ''
        po_summary = [
            ['Valor Total:', f"R$ {purchase_order.total_value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.') , 'Entrega:', delivery_date_str],
            ['Condições Pagamento:', purchase_order.payment_terms or '', 'Observações:', purchase_order.notes or '']
        ]
        summary_table = Table(po_summary, colWidths=[4*cm, 8*cm, 3*cm, 3*cm])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 14))

        # Cotação selecionada (se houver)
        selected_quotation = db.query(PurchaseOrderQuotation).filter(
            PurchaseOrderQuotation.purchase_order_id == purchase_order.id,
            PurchaseOrderQuotation.is_selected == True
        ).first()
        if selected_quotation:
            story.append(Paragraph("Cotação Selecionada", heading_style))
            quotation_data = [
                ['Fornecedor:', selected_quotation.supplier_name, 'Valor:', f"R$ {selected_quotation.total_value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')],
                ['Prazo Entrega (dias):', str(selected_quotation.delivery_time or ''), 'Condições Pagamento:', selected_quotation.payment_terms or ''],
                ['Observações:', selected_quotation.notes or '', '', '']
            ]
            quotation_table = Table(quotation_data, colWidths=[4*cm, 8*cm, 3*cm, 3*cm])
            quotation_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            story.append(quotation_table)
            story.append(Spacer(1, 14))

        # Itens do Pedido (se existirem)
        if purchase_order.items and len(purchase_order.items) > 0:
            story.append(Paragraph("Itens do Pedido", heading_style))
            items_data = [['Material', 'Quantidade', 'Preço Unitário', 'Total']]
            for item in purchase_order.items:
                material_name = item.material.name if item.material else str(item.material_id)
                items_data.append([
                    material_name,
                    f"{item.quantity}",
                    f"R$ {item.unit_price:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                    f"R$ {item.total_price:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                ])
            items_table = Table(items_data, colWidths=[8*cm, 3*cm, 3*cm, 3*cm])
            items_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            story.append(items_table)
            story.append(Spacer(1, 20))

        # Assinaturas
        signature_data = [
            ['SOLICITANTE', 'APROVADOR', 'RESPONSÁVEL COMPRAS'],
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

        # Constrói e retorna PDF
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=pedido_compra_{order_id}.pdf"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar PDF: {str(e)}")