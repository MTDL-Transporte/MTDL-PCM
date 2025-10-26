import sqlite3

def setup_250_1h():
    print("=== CONFIGURANDO 250.1H TRABALHADAS ===")
    
    # Conectar ao banco de dados
    conn = sqlite3.connect('mtdl_pcm.db')
    cursor = conn.cursor()
    
    # Para ter 250.1h trabalhadas com horímetro atual de 310h:
    # initial_horimeter = 310 - 250.1 = 59.9h
    target_hours_worked = 250.1
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
    
    # Verificar cenários
    print(f"\nVerificação para {target_hours_worked}h trabalhadas:")
    
    # Plano de 250h
    print(f"\n📋 Plano de 250h:")
    cycles_250 = int(target_hours_worked // 250)
    next_maintenance_250 = (cycles_250 + 1) * 250
    print(f"  Ciclos completados: {cycles_250}")
    print(f"  Próxima manutenção: {next_maintenance_250}h")
    print(f"  {target_hours_worked}h >= {next_maintenance_250}h? {target_hours_worked >= next_maintenance_250}")
    
    if target_hours_worked >= next_maintenance_250:
        print(f"  🔴 DEVERIA CRIAR OS para o {cycles_250 + 1}º ciclo")
    else:
        print(f"  🟢 Ainda não")
    
    # Mas vamos verificar se ultrapassou o primeiro ciclo de 250h
    first_cycle_250 = 250
    print(f"\n🔍 Verificação do primeiro ciclo de 250h:")
    print(f"  {target_hours_worked}h >= {first_cycle_250}h? {target_hours_worked >= first_cycle_250}")
    
    if target_hours_worked >= first_cycle_250:
        print(f"  🔴 ULTRAPASSOU O PRIMEIRO CICLO! Deveria criar OS para 250h")
    
    conn.close()
    print(f"\n=== CENÁRIO CONFIGURADO ===")
    print("Execute 'python test_maintenance_function.py' para testar")

if __name__ == "__main__":
    setup_250_1h()