import httpx
import json

def main():
    url = "http://127.0.0.1:8789/maintenance/equipment"
    payload = {
        "prefix": "EQP-NOTIF-001",
        "name": "Equipamento Teste Notificações",
        "model": "ZX330",
        "manufacturer": "Hitachi",
        "plan_generation_mode": "padrao",
        # Campos opcionais
        "year": 2020,
        "status": "Ativo",
        "initial_horimeter": 0,
        "current_horimeter": 0
    }

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(url, json=payload)
        print("Status:", resp.status_code)
        try:
            print("Resposta:", json.dumps(resp.json(), ensure_ascii=False))
        except Exception:
            print("Resposta:", resp.text)
    except Exception as e:
        print("Erro ao criar equipamento de teste:", e)

if __name__ == "__main__":
    main()