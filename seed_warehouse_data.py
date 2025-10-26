#!/usr/bin/env python3
"""
Script de seed para dados do Almoxarifado.
Cria materiais, movimentações de estoque (entradas/saídas), fornecedores,
requisições e pedidos de compra (incluindo um entregue), e um histórico de inventário
para alimentar os KPIs de: Giro, Cobertura, Ruptura, Acuracidade e Custo de Armazenagem.
"""

import os
import sys
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, engine, Base
from sqlalchemy import and_

# Modelos necessários
from app.models.warehouse import (
    Material,
    StockMovement,
    Supplier,
    PurchaseRequest,
    PurchaseRequestItem,
    PurchaseOrder,
    InventoryHistory,
    InventoryHistoryItem,
)


def seed_warehouse_data():
    # Garantir criação das tabelas (útil após limpeza manual)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        # Apagar eventuais restos para evitar duplicidades (idempotência leve)
        db.query(InventoryHistoryItem).delete()
        db.query(InventoryHistory).delete()
        db.query(PurchaseOrder).delete()
        db.query(PurchaseRequestItem).delete()
        db.query(PurchaseRequest).delete()
        db.query(StockMovement).delete()
        db.query(Material).delete()
        db.query(Supplier).delete()
        db.commit()

        # 1) Fornecedores
        suppliers = [
            Supplier(name="Fornecedor Alfa", cnpj="00.000.000/0001-00", rating=4.5, email="alfa@forn.com"),
            Supplier(name="Fornecedor Beta", cnpj="11.111.111/0001-11", rating=3.8, email="beta@forn.com"),
            Supplier(name="Fornecedor Gama", cnpj="22.222.222/0001-22", rating=4.2, email="gama@forn.com"),
        ]
        db.add_all(suppliers)
        db.commit()

        # 2) Materiais (três categorias diferentes)
        materials_data = [
            {
                "code": "MAT001",
                "name": "Óleo Hidráulico HLP68",
                "category": "Lubrificantes",
                "unit": "L",
                "minimum_stock": 50,
                "maximum_stock": 300,
                "average_cost": 25.0,
                "unit_price": 25.0,
                "location": "A1-01",
                "current_stock": 0.0,
            },
            {
                "code": "MAT002",
                "name": "Filtro de Ar - Linha Pesada",
                "category": "Peças",
                "unit": "UN",
                "minimum_stock": 5,
                "maximum_stock": 30,
                "average_cost": 180.0,
                "unit_price": 180.0,
                "location": "B2-07",
                "current_stock": 0.0,
            },
            {
                "code": "MAT003",
                "name": "Graxa EP2",
                "category": "Lubrificantes",
                "unit": "KG",
                "minimum_stock": 20,
                "maximum_stock": 120,
                "average_cost": 18.5,
                "unit_price": 18.5,
                "location": "A1-03",
                "current_stock": 0.0,
            },
            {
                "code": "MAT004",
                "name": "Capacete de Segurança Classe B",
                "category": "EPI",
                "unit": "UN",
                "minimum_stock": 10,
                "maximum_stock": 80,
                "average_cost": 75.0,
                "unit_price": 75.0,
                "location": "C3-02",
                "current_stock": 0.0,
            },
            {
                "code": "MAT005",
                "name": "Luva Nitrílica",
                "category": "EPI",
                "unit": "PAR",
                "minimum_stock": 20,
                "maximum_stock": 200,
                "average_cost": 12.0,
                "unit_price": 12.0,
                "location": "C3-03",
                "current_stock": 0.0,
            },
        ]

        materials = []
        for md in materials_data:
            m = Material(**md)
            db.add(m)
            materials.append(m)
        db.commit()
        for m in materials:
            db.refresh(m)

        # 3) Movimentações de estoque
        # Estratégia: para cada material, criar uma entrada inicial e duas saídas em datas diferentes
        base_date = datetime.now()
        for m in materials:
            # Entrada inicial (60 dias atrás)
            qty_in = 100 if m.unit in ("UN", "PAR") else 200
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
                reference_document="NF-0001",
                reason="Reposição inicial para testes",
                performed_by="Seed",
                date=base_date - timedelta(days=60),
                notes="Entrada inicial",
                cost_center="ALMOX",
            )
            db.add(mv_in)

            # Saída 1 (30 dias atrás)
            qty_out1 = max(5, int(qty_in * 0.2))
            prev1 = new
            new1 = prev1 - qty_out1
            mv_out1 = StockMovement(
                material_id=m.id,
                type="Saída",
                quantity=qty_out1,
                unit_cost=m.average_cost,
                total_cost=(m.average_cost or 0.0) * qty_out1,
                previous_stock=prev1,
                new_stock=new1,
                reference_document="OS-1001",
                reason="Consumo operacional",
                performed_by="Seed",
                date=base_date - timedelta(days=30),
                notes="Saída 1",
                cost_center="PROD",
            )
            db.add(mv_out1)

            # Saída 2 (10 dias atrás)
            qty_out2 = max(3, int(qty_in * 0.1))
            prev2 = new1
            new2 = prev2 - qty_out2
            mv_out2 = StockMovement(
                material_id=m.id,
                type="Saída",
                quantity=qty_out2,
                unit_cost=m.average_cost,
                total_cost=(m.average_cost or 0.0) * qty_out2,
                previous_stock=prev2,
                new_stock=new2,
                reference_document="OS-1002",
                reason="Consumo operacional",
                performed_by="Seed",
                date=base_date - timedelta(days=10),
                notes="Saída 2",
                cost_center="PROD",
            )
            db.add(mv_out2)

            # Atualizar estoque atual do material
            m.current_stock = new2
            db.add(m)

        db.commit()

        # 4) Requisições de compra (para taxa de ruptura e tempo de atendimento)
        s_alfa, s_beta, s_gama = suppliers

        # PR Aprovada e atendida (com pedido Entregue)
        pr1 = PurchaseRequest(
            number="RC000001",
            requester="João",
            department="Operações",
            cost_center="ALMOX",
            justification="Repor lubrificantes",
            status="Aprovada",
            priority="Alta",
            supplier_id=s_alfa.id,
            total_value=0.0,
            requested_date=base_date - timedelta(days=8),
            approved_date=base_date - timedelta(days=6),
            approved_by="Gerente",
        )
        db.add(pr1)
        db.commit(); db.refresh(pr1)
        pr1_item = PurchaseRequestItem(
            purchase_request_id=pr1.id,
            material_id=materials[0].id,  # Óleo Hidráulico
            quantity=80,
            unit_price=materials[0].unit_price,
            total_price=80 * (materials[0].unit_price or 0.0),
            specifications="Óleo HLP68 bidões de 20L",
        )
        db.add(pr1_item)
        pr1.total_value = pr1_item.total_price
        db.add(pr1)
        db.commit()

        po1 = PurchaseOrder(
            number="PC000001",
            purchase_request_id=pr1.id,
            supplier_id=s_alfa.id,
            status="Entregue",
            total_value=pr1.total_value,
            delivery_date=base_date - timedelta(days=2),
            payment_terms="30 dias",
            notes="Pedido atendido para testes",
            created_by="Seed",
            created_at=base_date - timedelta(days=5),
            sent_at=base_date - timedelta(days=5),
            confirmed_at=base_date - timedelta(days=3),
        )
        db.add(po1)

        # PR Pendente (não atendida)
        pr2 = PurchaseRequest(
            number="RC000002",
            requester="Maria",
            department="Segurança",
            cost_center="EPI",
            justification="EPI para equipe",
            status="Pendente",
            priority="Normal",
            supplier_id=s_beta.id,
            total_value=0.0,
            requested_date=base_date - timedelta(days=12),
        )
        db.add(pr2)
        db.commit(); db.refresh(pr2)
        pr2_item = PurchaseRequestItem(
            purchase_request_id=pr2.id,
            material_id=materials[3].id,  # Capacete
            quantity=40,
            unit_price=materials[3].unit_price,
            total_price=40 * (materials[3].unit_price or 0.0),
            specifications="Capacete classe B com jugular",
        )
        db.add(pr2_item)
        pr2.total_value = pr2_item.total_price
        db.add(pr2)

        # PR Rejeitada (conta como não atendida)
        pr3 = PurchaseRequest(
            number="RC000003",
            requester="Carlos",
            department="Manutenção",
            cost_center="PEÇAS",
            justification="Peças de reposição",
            status="Rejeitada",
            priority="Alta",
            supplier_id=s_gama.id,
            total_value=0.0,
            requested_date=base_date - timedelta(days=20),
        )
        db.add(pr3)
        db.commit(); db.refresh(pr3)
        pr3_item = PurchaseRequestItem(
            purchase_request_id=pr3.id,
            material_id=materials[1].id,  # Filtro de Ar
            quantity=10,
            unit_price=materials[1].unit_price,
            total_price=10 * (materials[1].unit_price or 0.0),
            specifications="Filtros linha pesada padrão",
        )
        db.add(pr3_item)
        pr3.total_value = pr3_item.total_price
        db.add(pr3)
        db.commit()

        # 5) Histórico de Inventário (para acuracidade)
        inv = InventoryHistory(
            inventory_number="INV0001",
            process_date=base_date - timedelta(days=1),
            processed_by="Seed",
            notes="Inventário de teste",
            total_items=len(materials),
            items_counted=len(materials),
            items_correct=0,  # calculado abaixo
            items_with_difference=0,  # calculado abaixo
            accuracy_percentage=0.0,  # calculado abaixo
            total_adjustments=0,
        )
        db.add(inv)
        db.commit(); db.refresh(inv)

        correct = 0
        diff = 0
        for idx, m in enumerate(materials):
            # Alternar entre item correto e com diferença
            if idx % 2 == 0:
                physical = m.current_stock
            else:
                physical = max(0.0, (m.current_stock or 0.0) - 2)  # diferença negativa pequena

            system_stock = m.current_stock or 0.0
            difference = physical - system_stock
            is_correct = (abs(difference) < 1e-6)
            if is_correct:
                correct += 1
            else:
                diff += 1

            item = InventoryHistoryItem(
                inventory_id=inv.id,
                material_id=m.id,
                system_stock=system_stock,
                physical_count=physical,
                difference=difference,
                adjustment_made=False,
            )
            db.add(item)

        # Atualizar métricas do inventário
        inv.items_correct = correct
        inv.items_with_difference = diff
        inv.accuracy_percentage = round((correct / (len(materials) or 1)) * 100.0, 2)
        db.add(inv)

        db.commit()

        # Estatísticas rápidas
        mat_count = db.query(Material).count()
        mv_count = db.query(StockMovement).count()
        pr_count = db.query(PurchaseRequest).count()
        po_count = db.query(PurchaseOrder).count()
        inv_count = db.query(InventoryHistory).count()
        print("✅ Seed do Almoxarifado concluído com sucesso!")
        print(f"📦 Materiais: {mat_count}")
        print(f"🔄 Movimentações: {mv_count}")
        print(f"📝 Requisições: {pr_count}")
        print(f"🧾 Pedidos: {po_count}")
        print(f"📊 Inventários: {inv_count}")

    except Exception as e:
        db.rollback()
        print(f"❌ Erro no seed do Almoxarifado: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_warehouse_data()