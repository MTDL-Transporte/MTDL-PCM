#!/usr/bin/env python3
"""
Script utilitário para cancelar todas as notificações de estoque com status 'Pendente'.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.warehouse import StockNotification


def cancel_pending_notifications():
    db = SessionLocal()
    try:
        pending = db.query(StockNotification).filter(StockNotification.status == "Pendente").all()
        count = 0
        for n in pending:
            n.status = "Cancelada"
            n.notes = (n.notes or "") + "\n[auto] Limpeza manual de notificações de teste"
            count += 1
            db.add(n)
        db.commit()
        print(f"✅ Notificações canceladas: {count}")
    except Exception as e:
        db.rollback()
        print(f"❌ Erro ao cancelar notificações: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    cancel_pending_notifications()