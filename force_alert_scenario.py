import sqlite3

def force_alert_scenario():
    print("=== FORÇANDO CENÁRIO DE ALERTA ===")
    
    # Conectar ao banco de dados
    conn = sqlite3.connect('mtdl_pcm.db')
    cursor = conn.cursor()
    
    # Cenário 1: Equipamento próximo ao limite de 90% (225h)
    # Vamos definir horímetro inicial como 90h, para que com 310h atual tenhamos 220h trabalhadas
    initial_horimeter_scenario1 = 90.0
    
    cursor.execute("""
        UPDATE equipments 
        SET initial_horimeter = ?
        WHERE id = 1
    """, (initial_horimeter_scenario1,))
    
    conn.commit()
    
    # Verificar o resultado
    cursor.execute("""
        SELECT id, name, current_horimeter, initial_horimeter
        FROM equipments
        WHERE id = 1
    """)
    equipment = cursor.fetchone()
    
    hours_worked = equipment[2] - equipment[3]
    
    print(f"Cenário 1 - Próximo ao alerta (90%):")
    print(f"  Horímetro atual: {equipment[2]}h")
    print(f"  Horímetro inicial: {equipment[3]}h")
    print(f"  Horas trabalhadas: {hours_worked}h")
    
    # Verificar alertas para plano de 250h
    ninety_percent_250 = 250 * 0.9  # 225h
    print(f"  Limite 90% para 250h: {ninety_percent_250}h")
    
    if hours_worked >= ninety_percent_250:
        print(f"  🟡 DEVE GERAR ALERTA: {hours_worked}h >= {ninety_percent_250}h")
    else:
        print(f"  🟢 Ainda não: {hours_worked}h < {ninety_percent_250}h")
        print(f"  Faltam {ninety_percent_250 - hours_worked}h para o alerta")
    
    print("\n" + "="*50)
    
    # Cenário 2: Equipamento que ultrapassou o limite de manutenção
    # Vamos definir horímetro inicial como -50h, para que com 310h atual tenhamos 360h trabalhadas
    initial_horimeter_scenario2 = -50.0
    
    cursor.execute("""
        UPDATE equipments 
        SET initial_horimeter = ?
        WHERE id = 1
    """, (initial_horimeter_scenario2,))
    
    conn.commit()
    
    # Verificar o resultado
    cursor.execute("""
        SELECT id, name, current_horimeter, initial_horimeter
        FROM equipments
        WHERE id = 1
    """)
    equipment = cursor.fetchone()
    
    hours_worked = equipment[2] - equipment[3]
    
    print(f"Cenário 2 - Manutenção vencida:")
    print(f"  Horímetro atual: {equipment[2]}h")
    print(f"  Horímetro inicial: {equipment[3]}h")
    print(f"  Horas trabalhadas: {hours_worked}h")
    
    # Verificar para plano de 250h
    cycles_completed = int(hours_worked // 250)
    next_maintenance = (cycles_completed + 1) * 250
    overdue_hours = hours_worked - (cycles_completed * 250)
    
    print(f"  Ciclos de 250h completados: {cycles_completed}")
    print(f"  Próxima manutenção deveria ser em: {next_maintenance}h")
    print(f"  Horas além do último ciclo: {overdue_hours}h")
    
    if overdue_hours >= 250:
        print(f"  🔴 VENCIDO: Manutenção atrasada!")
    elif overdue_hours >= ninety_percent_250:
        print(f"  🟡 PRÓXIMO: Atingiu 90% do próximo ciclo")
    else:
        print(f"  🟢 OK: Ainda faltam {250 - overdue_hours}h para próximo ciclo")
    
    conn.close()
    print("\n=== CENÁRIOS CONFIGURADOS ===")
    print("Execute 'python check_maintenance_plans.py' para ver os resultados")

if __name__ == "__main__":
    force_alert_scenario()