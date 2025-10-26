#!/usr/bin/env python3
"""
Seed massivo para dados de 2025 (Jan até hoje), cobrindo:
- Almoxarifado: materiais, fornecedores, movimentações, requisições e pedidos
- Manutenção: equipamentos (20 por categoria), planos de manutenção, ações, materiais dos planos
- Horímetro: logs mensais para disparar OS preventivas via função existente
- OS corretivas: ordens variadas com time logs e estados distintos

Observações:
- Apaga dados existentes das tabelas relacionadas para garantir idempotência simples
- Usa intervalos de horímetro ("Horímetro") para geração automática de OS preventivas
- Variedade de datas e estados para alimentar gráficos e KPIs
"""

import os
import sys
import random
from datetime import datetime, timedelta
import asyncio

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, engine, Base
from sqlalchemy import and_, func

# Modelos
from app.models.warehouse import (
    Material,
    StockMovement,
    Supplier,
    PurchaseRequest,
    PurchaseRequestItem,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseOrderQuotation,
    PurchaseOrderQuotationItem,
    Quotation,
    QuotationItem,
    InventoryHistory,
    InventoryHistoryItem,
    Fueling,
    StockNotification,
    StockNotificationItem,
)
from app.models.equipment import Equipment, HorimeterLog, WeeklyHours
from app.models.maintenance import (
    WorkOrder,
    MaintenancePlan,
    MaintenancePlanMaterial,
    MaintenancePlanAction,
    MaintenanceAlert,
    TimeLog,
    WorkOrderChecklist,
    Technician,
)

# Função de geração automática de preventiva
from app.routers.maintenance import check_and_create_preventive_maintenance


def _rand_date_in_month(year: int, month: int) -> datetime:
    """Retorna data aleatória dentro de um mês/ano."""
    day = random.randint(1, 28)
    return datetime(year, month, day, random.randint(6, 18), random.randint(0, 59))


def _progress_print(msg: str):
    print(msg, flush=True)


def clear_existing_data(db):
    """Apaga dados das tabelas chave para idempotência simples."""
    _progress_print("🧹 Limpando dados existentes...")

    # Ordem de deleção para respeitar FKs
    db.query(StockNotificationItem).delete()
    db.query(StockNotification).delete()
    db.query(InventoryHistoryItem).delete()
    db.query(InventoryHistory).delete()
    db.query(PurchaseOrderQuotationItem).delete()
    db.query(PurchaseOrderQuotation).delete()
    db.query(PurchaseOrderItem).delete()
    db.query(PurchaseOrder).delete()
    db.query(QuotationItem).delete()
    db.query(Quotation).delete()
    db.query(PurchaseRequestItem).delete()
    db.query(PurchaseRequest).delete()
    db.query(StockMovement).delete()
    db.query(Fueling).delete()

    db.query(MaintenanceAlert).delete()
    db.query(WorkOrderChecklist).delete()
    db.query(TimeLog).delete()
    # db.query(WorkOrderMaterial).delete()  # desabilitado no modelo
    db.query(WorkOrder).delete()
    db.query(MaintenancePlanMaterial).delete()
    db.query(MaintenancePlanAction).delete()
    db.query(MaintenancePlan).delete()

    db.query(WeeklyHours).delete()
    db.query(HorimeterLog).delete()
    db.query(Equipment).delete()

    db.query(Material).delete()
    db.query(Supplier).delete()
    db.commit()


def seed_suppliers(db):
    _progress_print("👨‍💼 Criando fornecedores...")
    suppliers = [
        Supplier(name="Fornecedor Alfa", cnpj="00.000.000/0001-00", rating=4.5, email="alfa@forn.com"),
        Supplier(name="Fornecedor Beta", cnpj="11.111.111/0001-11", rating=3.8, email="beta@forn.com"),
        Supplier(name="Fornecedor Gama", cnpj="22.222.222/0001-22", rating=4.2, email="gama@forn.com"),
        Supplier(name="Fornecedor Delta", cnpj="33.333.333/0001-33", rating=4.0, email="delta@forn.com"),
        Supplier(name="Fornecedor Épsilon", cnpj="44.444.444/0001-44", rating=3.9, email="epsilon@forn.com"),
        Supplier(name="Fornecedor Zeta", cnpj="55.555.555/0001-55", rating=4.1, email="zeta@forn.com"),
        Supplier(name="Fornecedor Ômega", cnpj="66.666.666/0001-66", rating=4.4, email="omega@forn.com"),
        Supplier(name="Fornecedor Sigma", cnpj="77.777.777/0001-77", rating=3.7, email="sigma@forn.com"),
    ]
    db.add_all(suppliers)
    db.commit()
    return suppliers


def seed_materials(db):
    _progress_print("📦 Criando materiais...")
    materials_data = [
        {"code": "MAT001", "name": "Óleo Hidráulico HLP68", "category": "Lubrificantes", "unit": "L", "minimum_stock": 50, "maximum_stock": 500, "average_cost": 25.0, "unit_price": 25.0, "location": "A1-01", "current_stock": 0.0},
        {"code": "MAT002", "name": "Filtro de Ar - Linha Pesada", "category": "Peças", "unit": "UN", "minimum_stock": 10, "maximum_stock": 100, "average_cost": 180.0, "unit_price": 180.0, "location": "B2-07", "current_stock": 0.0},
        {"code": "MAT003", "name": "Graxa EP2", "category": "Lubrificantes", "unit": "KG", "minimum_stock": 50, "maximum_stock": 400, "average_cost": 18.5, "unit_price": 18.5, "location": "A1-03", "current_stock": 0.0},
        {"code": "MAT004", "name": "Capacete de Segurança Classe B", "category": "EPI", "unit": "UN", "minimum_stock": 20, "maximum_stock": 200, "average_cost": 75.0, "unit_price": 75.0, "location": "C3-02", "current_stock": 0.0},
        {"code": "MAT005", "name": "Luva Nitrílica", "category": "EPI", "unit": "PAR", "minimum_stock": 50, "maximum_stock": 400, "average_cost": 12.0, "unit_price": 12.0, "location": "C3-03", "current_stock": 0.0},
        {"code": "MAT006", "name": "Filtro de Óleo Motor", "category": "Peças", "unit": "UN", "minimum_stock": 20, "maximum_stock": 150, "average_cost": 95.0, "unit_price": 95.0, "location": "B1-02", "current_stock": 0.0},
        {"code": "MAT007", "name": "Óleo Diesel S10", "category": "Combustível", "unit": "L", "minimum_stock": 500, "maximum_stock": 5000, "average_cost": 6.2, "unit_price": 6.2, "location": "TANQ-01", "current_stock": 0.0},
        {"code": "MAT008", "name": "Filtro Hidráulico", "category": "Peças", "unit": "UN", "minimum_stock": 10, "maximum_stock": 100, "average_cost": 150.0, "unit_price": 150.0, "location": "B1-05", "current_stock": 0.0},
        {"code": "MAT009", "name": "Óleo de Motor 15W40", "category": "Lubrificantes", "unit": "L", "minimum_stock": 100, "maximum_stock": 1000, "average_cost": 19.9, "unit_price": 19.9, "location": "A2-01", "current_stock": 0.0},
        {"code": "MAT010", "name": "Filtro de Combustível", "category": "Peças", "unit": "UN", "minimum_stock": 20, "maximum_stock": 150, "average_cost": 110.0, "unit_price": 110.0, "location": "B1-06", "current_stock": 0.0},
    ]
    mats = []
    for md in materials_data:
        m = Material(**md)
        db.add(m)
        mats.append(m)
    db.commit()
    for m in mats:
        db.refresh(m)
    return mats


def seed_initial_stock(db, materials):
    _progress_print("📈 Movimentando estoque inicial...")
    base_date = datetime.now()
    for m in materials:
        qty_in = {
            "UN": 120,
            "PAR": 200,
            "KG": 500,
            "L": 2000,
        }.get(m.unit, 100)
        prev = 0.0
        new = prev + qty_in
        mv_in = StockMovement(
            material_id=m.id,
            type="Entrada",
            quantity=qty_in,
            unit_cost=m.average_cost,
            total_cost=(m.average_cost or 0.0) * qty_in,
            previous_stock=prev,
            new_stock=new,
            reference_document="NF-2025-INIT",
            reason="Entrada inicial seed 2025",
            performed_by="Seed-2025",
            date=base_date - timedelta(days=120),
            notes="Carga inicial",
            cost_center="ALMOX",
        )
        db.add(mv_in)

        # Pequenas saídas em meses distintos
        for delta_days in [90, 60, 30]:
            qty_out = max(5, int(qty_in * random.uniform(0.05, 0.15)))
            prev_stock = new
            new = prev_stock - qty_out
            mv_out = StockMovement(
                material_id=m.id,
                type="Saída",
                quantity=qty_out,
                unit_cost=m.average_cost,
                total_cost=(m.average_cost or 0.0) * qty_out,
                previous_stock=prev_stock,
                new_stock=new,
                reference_document=f"OS-{1000 + random.randint(1,999)}",
                reason="Consumo operacional",
                performed_by="Seed-2025",
                date=base_date - timedelta(days=delta_days),
                notes="Saída seed",
                cost_center="PROD",
            )
            db.add(mv_out)

        m.current_stock = new
        db.add(m)
    db.commit()


def seed_equipments(db):
    _progress_print("🚜 Criando equipamentos (20 por categoria)...")
    categories = [
        "Escavadeira Hidraulica",
        "Retroescavadeira",
        "Pá carregadeira",
        "Rolo compactador",
        "Motoniveladora",
        "Perfuratriz",
        "Betoneira",
        "Usina de asfalto",
        "Caminhões",
        "Tratores",
        "Outros",
    ]
    equipments = []
    base_date = datetime(2025, 1, 5)
    for cat in categories:
        for i in range(1, 21):
            prefix_seed = {
                "Escavadeira Hidraulica": "ESC",
                "Retroescavadeira": "RET",
                "Pá carregadeira": "PAC",
                "Rolo compactador": "ROL",
                "Motoniveladora": "MOT",
                "Perfuratriz": "PER",
                "Betoneira": "BET",
                "Usina de asfalto": "USA",
                "Caminhões": "CAM",
                "Tratores": "TRA",
                "Outros": "OUT",
            }[cat]

            eq = Equipment(
                prefix=f"{prefix_seed}-{i:03d}",
                name=f"{cat} {i:03d}",
                model=f"Modelo-{random.randint(100,999)}",
                manufacturer=random.choice(["Caterpillar", "Volvo", "Komatsu", "JCB", "Scania", "John Deere", "Wirtgen"]),
                year=random.randint(2015, 2024),
                serial_number=f"SN-{random.randint(100000,999999)}",
                cost_center=random.choice(["55000004001", "55000001001", "55000011001"]),
                company_name="MTDL",
                status=random.choice(["operacional", "manutencao", "ativo"]),
                mobilization_date=base_date + timedelta(days=random.randint(0, 20)),
                demobilization_date=None,
                initial_horimeter=float(random.randint(0, 50)),
                current_horimeter=None,  # setado após primeiro log
                equipment_class="linha_amarela" if cat not in ("Betoneira", "Outros") else "linha_branca",
                category=cat,
                monthly_quota=random.choice([160.0, 180.0, 200.0, 220.0]),
                location=random.choice(["Site A", "Site B", "Planta 01", "Planta 02"]),
                description=f"Equipamento da categoria {cat}.",
            )
            db.add(eq)
            equipments.append(eq)
    db.commit()
    for e in equipments:
        db.refresh(e)
    return equipments


def seed_maintenance_plans(db, equipments, materials_map):
    _progress_print("🛠️ Criando planos de manutenção, ações e materiais...")
    plans = []
    actions = []
    plan_materials = []
    for eq in equipments:
        # Plano 1: troca de óleo a cada 250 horas
        plan1 = MaintenancePlan(
            name=f"Troca de óleo {eq.prefix}",
            equipment_id=eq.id,
            type="Preventiva",
            interval_type="Horímetro",
            interval_value=250,
            description="Troca de óleo do motor e inspeções básicas",
            checklist_template={"items": ["Checar níveis", "Inspecionar vazamentos"]},
            is_active=True,
            estimated_hours=4.0,
            priority=random.choice(["Normal", "Alta"]),
        )
        db.add(plan1)
        db.flush()  # garantir ID para ações e materiais
        plans.append(plan1)

        # Plano 2: inspeção geral a cada 500 horas
        plan2 = MaintenancePlan(
            name=f"Inspeção geral {eq.prefix}",
            equipment_id=eq.id,
            type="Preventiva",
            interval_type="Horímetro",
            interval_value=500,
            description="Inspeção geral do equipamento, filtros e limpeza",
            checklist_template={"items": ["Checagem estrutural", "Limpeza", "Aperto de fixações"]},
            is_active=True,
            estimated_hours=6.0,
            priority=random.choice(["Normal", "Alta"]),
        )
        db.add(plan2)
        db.flush()  # garantir ID para ações e materiais
        plans.append(plan2)

        # Ações
        for p in (plan1, plan2):
            act1 = MaintenancePlanAction(
                plan_id=p.id,
                description="Inspeção visual",
                action_type="Inspeção",
                sequence_order=1,
                estimated_time_minutes=30,
            )
            act2 = MaintenancePlanAction(
                plan_id=p.id,
                description="Troca de óleo e filtro",
                action_type="Troca",
                sequence_order=2,
                estimated_time_minutes=120,
            )
            act3 = MaintenancePlanAction(
                plan_id=p.id,
                description="Lubrificação de pontos críticos",
                action_type="Ajuste",
                sequence_order=3,
                estimated_time_minutes=60,
            )
            db.add_all([act1, act2, act3])
            actions.extend([act1, act2, act3])

            # Materiais dos planos
            mat_pairs = [
                ("MAT009", 20.0, "L"),  # Óleo de Motor 15W40
                ("MAT002", 1.0, "UN"),  # Filtro de Ar
            ]
            for code, qty, unit in mat_pairs:
                mat = materials_map.get(code)
                if mat:
                    pm = MaintenancePlanMaterial(
                        plan_id=p.id,
                        material_id=mat.id,
                        quantity=qty,
                        unit=unit,
                    )
                    db.add(pm)
                    plan_materials.append(pm)
    db.commit()
    # refresh opcional
    return plans


async def seed_horimeter_and_preventive(db, equipments):
    _progress_print("⏱️ Criando logs de horímetro mensais e disparando preventivas...")
    # Meses de Jan 2025 até mês atual
    today = datetime.now()
    months = []
    m = datetime(2025, 1, 1)
    while m <= today:
        months.append((m.year, m.month))
        # avança um mês
        if m.month == 12:
            m = datetime(m.year + 1, 1, 1)
        else:
            m = datetime(m.year, m.month + 1, 1)

    for eq in equipments:
        # Inicializar current_horimeter
        current = float(eq.initial_horimeter or 0)
        last_update = None
        for (yr, mo) in months:
            # Horas trabalhadas no mês (variável por equipamento/categoria)
            base_hours = random.choice([120, 150, 180, 200, 220])
            variation = random.uniform(-20, 30)
            month_hours = max(40, base_hours + variation)
            new_value = current + month_hours
            recorded_at = _rand_date_in_month(yr, mo)

            # Criar log
            hl = HorimeterLog(
                equipment_id=eq.id,
                previous_value=current,
                new_value=new_value,
                difference=new_value - current,
                recorded_by="Seed-2025",
                recorded_at=recorded_at,
                notes=f"Horas do mês {mo:02d}/{yr}",
            )
            db.add(hl)

            # Atualizar equipamento
            current = new_value
            eq.current_horimeter = current
            eq.last_horimeter_update = recorded_at
            db.add(eq)

            # Pequenos abastecimentos (vincular combustível se disponível)
            try:
                diesel = db.query(Material).filter(Material.code == "MAT007").first()
                if diesel:
                    qty = random.uniform(50, 200)
                    f = Fueling(
                        equipment_id=eq.id,
                        material_id=diesel.id,
                        date=recorded_at - timedelta(days=1),
                        quantity=qty,
                        horimeter=current - random.uniform(1, 5),
                        unit_cost=diesel.unit_price,
                        total_cost=diesel.unit_price * qty,
                        operator="Seed-2025",
                        notes="Abastecimento para testes",
                    )
                    db.add(f)
            except Exception:
                pass

            db.commit()

            # Disparar verificação/preventiva (função async existente)
            # Usar instância atualizada do equipamento
            eq_refreshed = db.query(Equipment).filter(Equipment.id == eq.id).first()
            try:
                await check_and_create_preventive_maintenance(eq_refreshed, db)
            except Exception as e:
                print(f"⚠️ Falha ao criar preventiva para {eq.prefix}: {e}")


def seed_corrective_work_orders(db, equipments):
    _progress_print("🔧 Criando OS corretivas variadas...")
    statuses = ["Aberta", "Em andamento", "Fechada"]
    causes = ["Falha operacional", "Desgaste natural", "Ajuste necessário"]
    for eq in random.sample(equipments, min(80, len(equipments))):
        # 1 a 3 OS por equipamento
        for _ in range(random.randint(1, 3)):
            last_order = db.query(WorkOrder).order_by(WorkOrder.id.desc()).first()
            next_number = 100000 if not last_order else int(last_order.number) + 1
            created_at = _rand_date_in_month(random.choice([2025, datetime.now().year]), random.choice(list(range(1, 13))))
            status = random.choice(statuses)
            started_at = created_at + timedelta(days=random.randint(0, 5)) if status in ("Em andamento", "Fechada") else None
            completed_at = started_at + timedelta(days=random.randint(1, 10)) if status == "Fechada" else None
            due_date = created_at + timedelta(days=random.randint(2, 15))

            wo = WorkOrder(
                number=str(next_number),
                title=f"Manutenção Corretiva - {eq.prefix}",
                description="Correção de anomalia identificada em inspeção de rotina",
                priority=random.choice(["Baixa", "Normal", "Alta", "Crítica"]),
                type="Corretiva",
                maintenance_cause=random.choice(causes),
                status=status,
                equipment_id=eq.id,
                requested_by=random.choice(["Operador", "Supervisor", "Sistema"]),
                assigned_to=random.choice(["Equipe A", "Equipe B", "Equipe C"]),
                estimated_hours=random.choice([4.0, 6.0, 8.0]),
                actual_hours=random.choice([2.0, 4.0, 6.0, 8.0]),
                cost=round(random.uniform(500, 5000), 2),
                created_at=created_at,
                started_at=started_at,
                completed_at=completed_at,
                due_date=due_date,
                notes="OS criada pelo seed 2025",
            )
            db.add(wo)
            db.commit()
            db.refresh(wo)

            # Time logs
            if started_at:
                tl_count = random.randint(1, 3)
                for i in range(tl_count):
                    st = started_at + timedelta(hours=i * 2)
                    et = st + timedelta(hours=random.randint(1, 4))
                    tl = TimeLog(
                        work_order_id=wo.id,
                        technician=random.choice(["Téc. João", "Téc. Maria", "Téc. Carlos"]),
                        start_time=st,
                        end_time=et,
                        hours_worked=(et - st).total_seconds() / 3600,
                        activity_description="Atividade de reparo",
                        date=st.date(),
                    )
                    db.add(tl)
            db.commit()


def seed_purchase_flow(db, suppliers, materials):
    _progress_print("🧾 Criando requisições e pedidos de compra...")
    base_number_pr = 250000
    base_number_po = 350000
    materials_ids = [m.id for m in materials]
    # 30 requisições ao longo do período, com estados variados
    for i in range(1, 31):
        supplier = random.choice(suppliers)
        req_date = datetime(2025, random.randint(1, max(1, datetime.now().month)), random.randint(1, 28))
        status = random.choice(["Pendente", "Aprovada", "Rejeitada", "Comprada"])
        pr = PurchaseRequest(
            number=f"RC{i + base_number_pr}",
            requester=random.choice(["João", "Maria", "Carlos", "Ana", "Pedro"]),
            department=random.choice(["Operações", "Manutenção", "Segurança", "Compras"]),
            cost_center=random.choice(["ALMOX", "PROD", "MANUT", "SESMT"]),
            justification="Repor materiais para manutenção 2025",
            status=status,
            priority=random.choice(["Baixa", "Normal", "Alta"]),
            supplier_id=supplier.id,
            total_value=0.0,
            requested_date=req_date,
            approved_date=req_date + timedelta(days=random.randint(1, 7)) if status in ("Aprovada", "Comprada") else None,
            approved_by="Gerente" if status in ("Aprovada", "Comprada") else None,
        )
        db.add(pr)
        db.commit(); db.refresh(pr)

        # Itens (1 a 3)
        item_count = random.randint(1, 3)
        total = 0.0
        for _ in range(item_count):
            mat = random.choice(materials)
            qty = random.randint(5, 50)
            it = PurchaseRequestItem(
                purchase_request_id=pr.id,
                material_id=mat.id,
                quantity=qty,
                unit_price=mat.unit_price,
                total_price=(mat.unit_price or 0.0) * qty,
                specifications=f"{mat.name} especificação teste",
            )
            db.add(it)
            total += it.total_price or 0.0
        pr.total_value = total
        db.add(pr)
        db.commit()

        # Cotações (2)
        qt1 = Quotation(
            number=f"QT{i + base_number_pr}",
            supplier_id=supplier.id,
            purchase_request_id=pr.id,
            status=random.choice(["Recebida", "Aprovada", "Pendente"]),
            total_value=round(total * random.uniform(0.9, 1.1), 2),
            delivery_time=random.randint(3, 20),
            payment_terms="30 dias",
            validity_date=req_date + timedelta(days=30),
        )
        db.add(qt1)
        db.commit(); db.refresh(qt1)
        # Itens cotação
        for _ in range(item_count):
            mat = random.choice(materials)
            qty = random.randint(5, 50)
            qti = QuotationItem(
                quotation_id=qt1.id,
                material_id=mat.id,
                quantity=qty,
                unit_price=mat.unit_price,
                total_price=(mat.unit_price or 0.0) * qty,
            )
            db.add(qti)
        db.commit()

        # Pedido de compra para parte das requisições
        if status in ("Aprovada", "Comprada"):
            po = PurchaseOrder(
                number=f"PC{i + base_number_po}",
                purchase_request_id=pr.id,
                supplier_id=supplier.id,
                status=random.choice(["Pendente", "Enviado", "Confirmado", "Entregue"]),
                total_value=pr.total_value or 0.0,
                delivery_date=req_date + timedelta(days=random.randint(5, 25)),
                payment_terms="30 dias",
                notes="Pedido seed 2025",
                created_by="Seed-2025",
                created_at=req_date + timedelta(days=random.randint(1, 3)),
                sent_at=req_date + timedelta(days=random.randint(2, 5)),
                confirmed_at=req_date + timedelta(days=random.randint(3, 7)),
            )
            db.add(po)
            db.commit(); db.refresh(po)

            # Itens do pedido (espelhar parcialmente a PR)
            po_item_count = random.randint(1, 3)
            for _ in range(po_item_count):
                mat = random.choice(materials)
                qty = random.randint(5, 50)
                poi = PurchaseOrderItem(
                    purchase_order_id=po.id,
                    material_id=mat.id,
                    quantity=qty,
                    unit_price=mat.unit_price,
                    total_price=(mat.unit_price or 0.0) * qty,
                )
                db.add(poi)
            db.commit()

            # Cotações do pedido (comparativos)
            for s in random.sample(suppliers, k=2):
                poq = PurchaseOrderQuotation(
                    purchase_order_id=po.id,
                    supplier_id=s.id,
                    supplier_name=s.name,
                    contact_name=random.choice(["Contato A", "Contato B", "Contato C"]),
                    contact_phone="(11) 99999-0000",
                    total_value=round(pr.total_value * random.uniform(0.9, 1.15), 2),
                    delivery_time=random.randint(5, 20),
                    payment_terms="30 dias",
                    attachment_path="/path/fake.pdf",
                    is_selected=random.choice([True, False]),
                    notes="Cotação comparativa",
                )
                db.add(poq)
                db.commit(); db.refresh(poq)
                # Itens da cotação
                for _ in range(po_item_count):
                    mat = random.choice(materials)
                    qty = random.randint(5, 50)
                    poqi = PurchaseOrderQuotationItem(
                        quotation_id=poq.id,
                        material_id=mat.id,
                        quantity=qty,
                        unit_price=mat.unit_price,
                        total_price=(mat.unit_price or 0.0) * qty,
                    )
                    db.add(poqi)
            db.commit()


def seed_inventory_history(db, materials):
    _progress_print("📊 Criando inventários para acuracidade...")
    # Dois inventários: meio do ano e recente
    for idx, when in enumerate([datetime(2025, 6, 15), datetime.now() - timedelta(days=2)]):
        inv = InventoryHistory(
            inventory_number=f"INV2025-{idx+1:02d}",
            process_date=when,
            processed_by="Seed-2025",
            notes="Inventário seed massivo",
            total_items=len(materials),
            items_counted=len(materials),
            items_correct=0,
            items_with_difference=0,
            accuracy_percentage=0.0,
            total_adjustments=0,
        )
        db.add(inv)
        db.commit(); db.refresh(inv)

        correct = 0
        diff = 0
        for i, m in enumerate(materials):
            # alterna diferenças
            physical = max(0.0, (m.current_stock or 0.0) + (5 if i % 3 == 0 else -3))
            system = m.current_stock or 0.0
            difference = physical - system
            item = InventoryHistoryItem(
                inventory_id=inv.id,
                material_id=m.id,
                system_stock=system,
                physical_count=physical,
                difference=difference,
                adjustment_made=False,
            )
            db.add(item)
            if abs(difference) < 1e-6:
                correct += 1
            else:
                diff += 1
        inv.items_correct = correct
        inv.items_with_difference = diff
        inv.accuracy_percentage = round((correct / (len(materials) or 1)) * 100.0, 2)
        db.add(inv)
        db.commit()


def seed_mass_2025():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        clear_existing_data(db)

        suppliers = seed_suppliers(db)
        materials = seed_materials(db)
        seed_initial_stock(db, materials)
        materials_map = {m.code: m for m in materials}

        equipments = seed_equipments(db)
        seed_maintenance_plans(db, equipments, materials_map)

        # Horímetro e preventivas (async)
        asyncio.run(seed_horimeter_and_preventive(db, equipments))

        # OS corretivas
        seed_corrective_work_orders(db, equipments)

        # Fluxo de compras
        seed_purchase_flow(db, suppliers, materials)

        # Inventários
        seed_inventory_history(db, materials)

        # Estatísticas rápidas
        _progress_print("✅ Seed 2025 concluído!")
        print(f"Equipamentos: {db.query(Equipment).count()}")
        print(f"Planos: {db.query(MaintenancePlan).count()}")
        print(f"Logs Horímetro: {db.query(HorimeterLog).count()}")
        print(f"OS Preventivas: {db.query(WorkOrder).filter(WorkOrder.type=='Preventiva').count()}")
        print(f"OS Corretivas: {db.query(WorkOrder).filter(WorkOrder.type=='Corretiva').count()}")
        print(f"Materiais: {db.query(Material).count()}")
        print(f"Requisições: {db.query(PurchaseRequest).count()}")
        print(f"Pedidos: {db.query(PurchaseOrder).count()}")
        print(f"Inventários: {db.query(InventoryHistory).count()}")

    except Exception as e:
        db.rollback()
        print(f"❌ Erro no seed 2025: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_mass_2025()