import sqlite3

def setup_alert_scenario():
    print("=== CONFIGURANDO CENÁRIO PARA ALERTAS ===")
    
    # Conectar ao banco de dados
    conn = sqlite3.connect('mtdl_pcm.db')
    cursor = conn.cursor()
    
    # Para ter 460h trabalhadas com horímetro atual de 310h:
    # initial_horimeter = 310 - 460 = -150h
    target_hours_worked = 460.0
    current_horimeter = 310.0
    new_initial_horimeter = current_horimeter - target_hours_worked
    
    print(f"Configurando para {target_hours_worked}h trabalhadas:")
    print(f"  Horímetro atual: {current_horimeter}h")
    print(f"  Horímetro inicial: {new_initial_horimeter}h")
    print(f"  Horas trabalhadas: {target_hours_worked}h")
    
    cursor.execute("""
        UPDATE equipments 
        SET initial_horimeter = ?
        WHERE id = 1
    """, (new_initial_horimeter,))
    
    conn.commit()
    
    # Verificar cenários de alerta
    print(f"\nVerificação de alertas para {target_hours_worked}h trabalhadas:")
    
    # Plano de 250h
    print(f"\n📋 Plano de 250h:")
    cycles_250 = int(target_hours_worked // 250)
    next_maintenance_250 = (cycles_250 + 1) * 250
    hours_until_250 = next_maintenance_250 - target_hours_worked
    limit_90_250 = next_maintenance_250 - (250 * 0.1)
    
    print(f"  Ciclos completados: {cycles_250}")
    print(f"  Próxima manutenção: {next_maintenance_250}h")
    print(f"  Horas até manutenção: {hours_until_250}h")
    print(f"  Limite 90%: {limit_90_250}h")
    
    if target_hours_worked >= next_maintenance_250:
        print(f"  🔴 VENCIDO: Deveria criar OS")
    elif target_hours_worked >= limit_90_250:
        print(f"  🟡 ALERTA: Deveria criar alerta de 90%")
    else:
        print(f"  🟢 OK: Ainda não")
    
    # Plano de 500h
    print(f"\n📋 Plano de 500h:")
    cycles_500 = int(target_hours_worked // 500)
    next_maintenance_500 = (cycles_500 + 1) * 500
    hours_until_500 = next_maintenance_500 - target_hours_worked
    limit_90_500 = next_maintenance_500 - (500 * 0.1)
    
    print(f"  Ciclos completados: {cycles_500}")
    print(f"  Próxima manutenção: {next_maintenance_500}h")
    print(f"  Horas até manutenção: {hours_until_500}h")
    print(f"  Limite 90%: {limit_90_500}h")
    
    if target_hours_worked >= next_maintenance_500:
        print(f"  🔴 VENCIDO: Deveria criar OS")
    elif target_hours_worked >= limit_90_500:
        print(f"  🟡 ALERTA: Deveria criar alerta de 90%")
    else:
        print(f"  🟢 OK: Ainda não")
    
    conn.close()
    print(f"\n=== CENÁRIO CONFIGURADO ===")
    print("Execute 'python test_maintenance_function.py' para testar")

if __name__ == "__main__":
    setup_alert_scenario()