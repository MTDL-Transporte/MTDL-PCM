#!/usr/bin/env python3
"""
Validação do fluxo de geração de OS por alerta e encerramento automático
- Busca alertas preventivos
- Gera OS via endpoint de alerta
- Verifica criação de Notificação de Estoque Pendente
- Fecha a OS e valida que a notificação muda para Atendida/Cancelada
"""
import sys
import json
from datetime import datetime

try:
    import requests
except Exception:
    print("❌ Biblioteca 'requests' não encontrada. Instale-a com 'pip install requests'.")
    sys.exit(1)

BASE_URL = "http://localhost:8000"

def get_preventive_alert():
    # Preferir endpoint mais detalhado
    url = f"{BASE_URL}/maintenance/preventive-alerts"
    r = requests.get(url, timeout=10)
    if r.status_code != 200:
        print(f"❌ Falha ao buscar alertas: {r.status_code} {r.text[:200]}")
        return None
    data = r.json()
    alerts = data.get("alerts") or []
    if not alerts:
        print("ℹ️ Nenhum alerta retornado." )
        return None
    # Escolher primeiro alerta com plan_id
    for a in alerts:
        if a.get("plan_id"):
            return a
    print("ℹ️ Alertas retornados não possuem 'plan_id'.")
    return None

def generate_work_order_from_alert(plan_id):
    url = f"{BASE_URL}/api/maintenance/generate-work-order-from-alert"
    payload = {"plan_id": plan_id}
    r = requests.post(url, json=payload, timeout=15)
    print(f"🔧 Geração via alerta: {r.status_code}")
    try:
        data = r.json()
    except Exception:
        print("❌ Resposta não JSON:", r.text[:200])
        return None
    # Pode retornar work_order ou apenas work_order_id se já existir
    wo_id = None
    if isinstance(data, dict):
        wo = data.get("work_order")
        if wo and isinstance(wo, dict):
            wo_id = wo.get("id")
            print(f"✅ OS criada: #{wo.get('number')} (ID {wo_id})")
        if not wo_id:
            wo_id = data.get("work_order_id")
            if wo_id:
                print(f"ℹ️ OS já existente vinculada ao alerta: ID {wo_id}")
    return wo_id

def list_notifications(status="Pendente"):
    url = f"{BASE_URL}/api/warehouse/stock-notifications?status={status}"
    r = requests.get(url, timeout=10)
    if r.status_code != 200:
        print(f"❌ Falha ao buscar notificações ({status}): {r.status_code}")
        return []
    return r.json()

def close_work_order(wo_id):
    url = f"{BASE_URL}/maintenance/api/work-orders/{wo_id}"
    payload = {"status": "Fechada", "notes": "Fechamento automático de validação"}
    r = requests.put(url, json=payload, timeout=15)
    print(f"🔒 Fechamento da OS: {r.status_code}")
    if r.status_code != 200:
        print("❌ Falha ao fechar OS:", r.text[:200])
        return False
    return True

def main():
    print("=== Validação: OS via alerta + Notificações de Estoque ===\n")

    # 1) Alertas
    alert = get_preventive_alert()
    if not alert:
        print("Encerrando: sem alerta disponível.")
        return
    plan_id = alert.get("plan_id")
    print(f"⚠️ Alerta encontrado para plano {plan_id}: {alert.get('message')}")

    # 2) Geração de OS a partir do alerta
    wo_id = generate_work_order_from_alert(plan_id)
    if not wo_id:
        print("Encerrando: não foi possível obter ID da OS.")
        return

    # 3) Verificar notificações pendentes vinculadas
    pendentes = list_notifications("Pendente")
    pendentes_os = [n for n in pendentes if n.get("work_order_id") == wo_id]
    print(f"📦 Notificações pendentes totais: {len(pendentes)} | da OS: {len(pendentes_os)}")
    if pendentes_os:
        n = pendentes_os[0]
        print(f"   ➤ Notificação #{n['id']} | Itens: {len(n.get('items', []))}")
    else:
        print("   ℹ️ Nenhuma notificação pendente para esta OS (pode haver já existente ou falha silenciosa).")

    # 4) Fechar a OS
    if not close_work_order(wo_id):
        return

    # 5) Verificar notificações atendidas/canceladas
    atendidas = list_notifications("Atendida")
    canceladas = list_notifications("Cancelada")
    atendidas_os = [n for n in atendidas if n.get("work_order_id") == wo_id]
    canceladas_os = [n for n in canceladas if n.get("work_order_id") == wo_id]

    print(f"\n📊 Pós-fechamento: Atendidas={len(atendidas_os)} | Canceladas={len(canceladas_os)}")
    for n in atendidas_os:
        print(f"   ✅ Notificação {n['id']} marcada como Atendida")
    for n in canceladas_os:
        print(f"   ❎ Notificação {n['id']} marcada como Cancelada")

    print("\n=== Concluído ===")

if __name__ == "__main__":
    main()