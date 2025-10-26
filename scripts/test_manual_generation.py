#!/usr/bin/env python3
"""
Script para validar geração de planos via modo manual (PDF/XML),
com verificação de materiais já cadastrados e notificação apenas dos ausentes.
"""

import requests
import time

BASE = "http://localhost:8000"

def create_material_if_absent():
    """Cria um material conhecido (FO-123) se não existir, para testar o caso 'já cadastrado'."""
    # Tentar buscar pela lista (simplificado)
    try:
        resp = requests.get(f"{BASE}/api/warehouse/materials")
        if resp.status_code == 200:
            mats = resp.json()
            for m in mats:
                # Precisamos dos dados completos para checar reference; se não tiver, criamos mesmo assim
                pass
    except Exception:
        pass

    # Criar material com referência FO-123
    payload = {
        "name": "Filtro de óleo do motor",
        "description": "Filtro para motor",
        "reference": "FO-123",
        "unit": "un",
        "category": "Filtros",
    }
    try:
        resp = requests.post(f"{BASE}/api/warehouse/materials", json=payload)
        print("[create_material]", resp.status_code, resp.text[:120])
    except Exception as e:
        print("[create_material] exception:", e)


def upload_manual_xml(equipment_id: int):
    """Faz upload de um manual XML com alguns materiais (um existente, outros ausentes)."""
    xml = """
<manual>
  <maintenance interval="250h">
    <material>
      <name>Filtro de óleo do motor</name>
      <reference>FO-123</reference>
      <unit>un</unit>
      <quantity>1</quantity>
      <category>Filtros</category>
    </material>
    <material>
      <name>Óleo do motor SAE 15W-40</name>
      <reference>OM-15W40</reference>
      <unit>L</unit>
      <quantity>10</quantity>
      <category>Óleos e Lubrificantes</category>
    </material>
  </maintenance>
  <maintenance interval="500h">
    <material>
      <name>Filtro de combustível</name>
      <reference>FC-456</reference>
      <unit>un</unit>
      <quantity>1</quantity>
      <category>Filtros</category>
    </material>
  </maintenance>
</manual>
""".strip()

    files = {"file": ("manual.xml", xml, "application/xml")}
    try:
        resp = requests.post(f"{BASE}/api/maintenance/equipment/{equipment_id}/manual/upload", files=files)
        print("[upload_manual]", resp.status_code, resp.text[:200])
        return resp.json()
    except Exception as e:
        print("[upload_manual] exception:", e)
        return None


def generate_plans_manual_mode(equipment_id: int):
    payload = {"mode": "manual"}
    try:
        resp = requests.post(f"{BASE}/api/maintenance/equipment/{equipment_id}/plans/generate", json=payload)
        print("[generate_plans]", resp.status_code, resp.text[:200])
        return resp.json() if resp.headers.get("content-type", "").startswith("application/json") else None
    except Exception as e:
        print("[generate_plans] exception:", e)
        return None


def list_stock_notifications():
    try:
        resp = requests.get(f"{BASE}/api/warehouse/stock-notifications", params={"status": "Pendente"})
        print("[stock_notifications]", resp.status_code)
        if resp.status_code == 200:
            data = resp.json()
            print(f"Total notificações: {len(data)}")
            for n in data[:5]:
                print("- Notificação:", n.get("id"), n.get("message")[:100], "...")
        else:
            print(resp.text[:200])
    except Exception as e:
        print("[stock_notifications] exception:", e)


def main():
    equipment_id = 8  # Equipamento de teste criado anteriormente
    create_material_if_absent()
    up = upload_manual_xml(equipment_id)
    # Esperar um pouco para garantir escrita em disco
    time.sleep(0.5)
    gen = generate_plans_manual_mode(equipment_id)
    list_stock_notifications()


if __name__ == "__main__":
    main()