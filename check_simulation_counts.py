#!/usr/bin/env python3
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from app.models.equipment import HorimeterLog
from app.models.warehouse import Fueling
from app.models.maintenance import WorkOrder


def main():
    db = SessionLocal()
    try:
        hl = db.query(HorimeterLog).count()
        fu = db.query(Fueling).count()
        wo_total = db.query(WorkOrder).count()
        wo_prev = db.query(WorkOrder).filter(WorkOrder.type == "Preventiva").count()
        wo_corr = db.query(WorkOrder).filter(WorkOrder.type == "Corretiva").count()
        print(f"HorimeterLog: {hl}")
        print(f"Fueling: {fu}")
        print(f"WorkOrders: {wo_total}")
        print(f"Preventivas: {wo_prev}")
        print(f"Corretivas: {wo_corr}")
    finally:
        db.close()


if __name__ == "__main__":
    main()