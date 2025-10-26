import sqlite3

def setup_exact_250h():
    print("=== CONFIGURANDO EXATAMENTE 250H TRABALHADAS ===")
    
    # Conectar ao banco de dados
    conn = sqlite3.connect('mtdl_pcm.db')
    cursor = conn.cursor()
    
    # Para ter exatamente 250h trabalhadas com horímetro atual de 310h:
    # initial_horimeter = 310 - 250 = 60h
    target_hours_worked = 250.0
    current_horimeter = 310.0
    new_initial_horimeter = current_horimeter - target_hours_worked
    
    print(f"Configurando para exatamente {target_hours_worked}h trabalhadas:")
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
    print(f"\nVerificação para exatamente {target_hours_worked}h trabalhadas:")
    
    # Plano de 250h
    print(f"\n📋 Plano de 250h:")
    cycles_250 = int(target_hours_worked // 250)
    next_maintenance_250 = (cycles_250 + 1) * 250
    print(f"  Ciclos completados: {cycles_250}")
    print(f"  Próxima manutenção: {next_maintenance_250}h")
    print(f"  250h >= {next_maintenance_250}h? {target_hours_worked >= next_maintenance_250}")
    
    if target_hours_worked >= next_maintenance_250:
        print(f"  🔴 DEVERIA CRIAR OS para o {cycles_250 + 1}º ciclo")
    else:
        print(f"  🟢 Ainda não")
    
    # Plano de 500h
    print(f"\n📋 Plano de 500h:")
    cycles_500 = int(target_hours_worked // 500)
    next_maintenance_500 = (cycles_500 + 1) * 500
    print(f"  Ciclos completados: {cycles_500}")
    print(f"  Próxima manutenção: {next_maintenance_500}h")
    print(f"  250h >= {next_maintenance_500}h? {target_hours_worked >= next_maintenance_500}")
    
    if target_hours_worked >= next_maintenance_500:
        print(f"  🔴 DEVERIA CRIAR OS para o {cycles_500 + 1}º ciclo")
    else:
        print(f"  🟢 Ainda não")
    
    # Teste com 250.1h para garantir que ultrapasse o primeiro ciclo de 250h
    print(f"\n🔍 Teste conceitual com 250.1h:")
    test_hours = 250.1
    cycles_250_test = int(test_hours // 250)
    next_maintenance_250_test = (cycles_250_test + 1) * 250
    print(f"  Ciclos completados: {cycles_250_test}")
    print(f"  Próxima manutenção: {next_maintenance_250_test}h")
    print(f"  250.1h >= {next_maintenance_250_test}h? {test_hours >= next_maintenance_250_test}")
    
    if test_hours >= next_maintenance_250_test:
        print(f"  🔴 COM 250.1h DEVERIA CRIAR OS!")
    
    conn.close()
    print(f"\n=== CENÁRIO CONFIGURADO ===")
    print("Execute 'python test_maintenance_function.py' para testar")

if __name__ == "__main__":
    setup_exact_250h()