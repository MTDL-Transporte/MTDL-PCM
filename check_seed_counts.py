from app.database import SessionLocal
from app.models.maintenance import WorkOrder, MaintenancePlan
from app.models.equipment import Equipment, HorimeterLog
from app.models.warehouse import Material, PurchaseRequest, PurchaseOrder, InventoryHistory

def main():
    s = SessionLocal()
    try:
        equip = s.query(Equipment).count()
        plans = s.query(MaintenancePlan).count()
        hlogs = s.query(HorimeterLog).count()
        prev_wos = s.query(WorkOrder).filter(WorkOrder.type == 'Preventiva').count()
        corr_wos = s.query(WorkOrder).filter(WorkOrder.type == 'Corretiva').count()
        mats = s.query(Material).count()
        prs = s.query(PurchaseRequest).count()
        pos = s.query(PurchaseOrder).count()
        invs = s.query(InventoryHistory).count()

        print({
            'Equipamentos': equip,
            'Planos': plans,
            'LogsHorimetro': hlogs,
            'OS_Preventivas': prev_wos,
            'OS_Corretivas': corr_wos,
            'Materiais': mats,
            'Requisicoes': prs,
            'Pedidos': pos,
            'Inventarios': invs,
        })
    finally:
        s.close()

if __name__ == '__main__':
    main()