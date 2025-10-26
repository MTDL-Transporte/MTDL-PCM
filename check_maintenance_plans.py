import sqlite3
from datetime import datetime

def check_maintenance_plans():
    print("=== VERIFICAÇÃO DE PLANOS DE MANUTENÇÃO ===")
    
    # Conectar ao banco de dados
    conn = sqlite3.connect('mtdl_pcm.db')
    cursor = conn.cursor()
    
    # 1. Verificar equipamentos
    print("\n1. Equipamentos disponíveis:")
    cursor.execute("""
        SELECT id, name, prefix, current_horimeter, initial_horimeter
        FROM equipments
        ORDER BY id
    """)
    equipments = cursor.fetchall()
    
    for eq in equipments:
        hours_worked = (eq[3] or 0) - (eq[4] or 0) if eq[3] and eq[4] else 0
        print(f"   ID: {eq[0]} | {eq[1]} ({eq[2]}) | Horímetro: {eq[3]}h | Horas trabalhadas: {hours_worked}h")
    
    # 2. Verificar planos de manutenção
    print("\n2. Planos de manutenção:")
    cursor.execute("""
        SELECT mp.id, mp.name, mp.equipment_id, e.name as equipment_name, 
               mp.interval_type, mp.interval_value, mp.is_active, mp.priority
        FROM maintenance_plans mp
        LEFT JOIN equipments e ON mp.equipment_id = e.id
        ORDER BY mp.equipment_id, mp.interval_value
    """)
    plans = cursor.fetchall()
    
    if not plans:
        print("   ❌ Nenhum plano de manutenção encontrado!")
    else:
        for plan in plans:
            status = "✅ Ativo" if plan[6] else "❌ Inativo"
            print(f"   ID: {plan[0]} | {plan[1]} | Equipamento: {plan[3]} (ID: {plan[2]})")
            print(f"      Tipo: {plan[4]} | Intervalo: {plan[5]} | Status: {status} | Prioridade: {plan[7]}")
    
    # 3. Verificar alertas de manutenção
    print("\n3. Alertas de manutenção:")
    cursor.execute("""
        SELECT ma.id, ma.equipment_id, e.name as equipment_name, 
               ma.alert_type, ma.current_horimeter, ma.target_horimeter, 
               ma.hours_remaining, ma.message, ma.is_acknowledged
        FROM maintenance_alerts ma
        LEFT JOIN equipments e ON ma.equipment_id = e.id
        ORDER BY ma.created_at DESC
        LIMIT 10
    """)
    alerts = cursor.fetchall()
    
    if not alerts:
        print("   ℹ️ Nenhum alerta de manutenção encontrado")
    else:
        for alert in alerts:
            ack_status = "✅ Reconhecido" if alert[8] else "⚠️ Pendente"
            print(f"   ID: {alert[0]} | {alert[2]} (ID: {alert[1]}) | Tipo: {alert[3]}")
            print(f"      Horímetro atual: {alert[4]}h | Meta: {alert[5]}h | Restante: {alert[6]}h")
            print(f"      Mensagem: {alert[7]} | Status: {ack_status}")
    
    # 4. Verificar ordens de trabalho de manutenção preventiva
    print("\n4. Ordens de trabalho preventivas:")
    cursor.execute("""
        SELECT wo.id, wo.number, wo.title, wo.equipment_id, e.name as equipment_name,
               wo.type, wo.status, wo.created_at
        FROM work_orders wo
        LEFT JOIN equipments e ON wo.equipment_id = e.id
        WHERE wo.type = 'Preventiva'
        ORDER BY wo.created_at DESC
        LIMIT 10
    """)
    work_orders = cursor.fetchall()
    
    if not work_orders:
        print("   ℹ️ Nenhuma ordem de trabalho preventiva encontrada")
    else:
        for wo in work_orders:
            print(f"   #{wo[1]} | {wo[2]} | {wo[5]} (ID: {wo[3]})")
            print(f"      Tipo: {wo[5]} | Status: {wo[6]} | Criada: {wo[7]}")
    
    # 5. Simular cálculo de alertas para equipamento ID 1
    print("\n5. Simulação de cálculo de alertas para Equipamento ID 1:")
    cursor.execute("""
        SELECT e.id, e.name, e.current_horimeter, e.initial_horimeter,
               mp.id as plan_id, mp.name as plan_name, mp.interval_value
        FROM equipments e
        LEFT JOIN maintenance_plans mp ON e.id = mp.equipment_id AND mp.is_active = 1 AND mp.interval_type = 'Horímetro'
        WHERE e.id = 1
    """)
    equipment_data = cursor.fetchall()
    
    if equipment_data:
        for data in equipment_data:
            eq_id, eq_name, current_h, initial_h, plan_id, plan_name, interval = data
            
            if plan_id:
                hours_worked = (current_h or 0) - (initial_h or 0) if current_h and initial_h else 0
                cycles_completed = int(hours_worked // interval) if interval else 0
                next_maintenance_hours = (cycles_completed + 1) * interval if interval else 0
                hours_until_maintenance = next_maintenance_hours - hours_worked if interval else 0
                ninety_percent_threshold = next_maintenance_hours - (interval * 0.1) if interval else 0
                
                print(f"   Equipamento: {eq_name} (ID: {eq_id})")
                print(f"   Plano: {plan_name} (ID: {plan_id}) - Intervalo: {interval}h")
                print(f"   Horímetro atual: {current_h}h | Inicial: {initial_h}h")
                print(f"   Horas trabalhadas: {hours_worked}h")
                print(f"   Ciclos completados: {cycles_completed}")
                print(f"   Próxima manutenção em: {next_maintenance_hours}h")
                print(f"   Horas até manutenção: {hours_until_maintenance}h")
                print(f"   Limite 90%: {ninety_percent_threshold}h")
                
                if hours_worked >= next_maintenance_hours:
                    print(f"   🔴 VENCIDO: {hours_worked - next_maintenance_hours}h de atraso")
                elif hours_worked >= ninety_percent_threshold:
                    print(f"   🟡 PRÓXIMO: Atingiu 90% do intervalo")
                else:
                    print(f"   🟢 OK: Ainda faltam {hours_until_maintenance}h")
            else:
                print(f"   ❌ Equipamento {eq_name} (ID: {eq_id}) não possui planos de manutenção ativos")
    
    conn.close()
    print("\n=== VERIFICAÇÃO CONCLUÍDA ===")

if __name__ == "__main__":
    check_maintenance_plans()