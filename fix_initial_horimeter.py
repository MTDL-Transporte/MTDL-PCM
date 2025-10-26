import sqlite3

def fix_initial_horimeter():
    print("=== CORREÇÃO DO HORÍMETRO INICIAL ===")
    
    # Conectar ao banco de dados
    conn = sqlite3.connect('mtdl_pcm.db')
    cursor = conn.cursor()
    
    # Verificar estado atual
    cursor.execute("""
        SELECT id, name, current_horimeter, initial_horimeter
        FROM equipments
        WHERE id = 1
    """)
    equipment = cursor.fetchone()
    
    if equipment:
        print(f"Estado atual do equipamento {equipment[1]}:")
        print(f"  Horímetro atual: {equipment[2]}h")
        print(f"  Horímetro inicial: {equipment[3]}h")
        
        # Definir um horímetro inicial realista (por exemplo, 200h)
        # Isso fará com que as horas trabalhadas sejam 310 - 200 = 110h
        new_initial_horimeter = 200.0
        
        cursor.execute("""
            UPDATE equipments 
            SET initial_horimeter = ?
            WHERE id = 1
        """, (new_initial_horimeter,))
        
        conn.commit()
        
        # Verificar após a atualização
        cursor.execute("""
            SELECT id, name, current_horimeter, initial_horimeter
            FROM equipments
            WHERE id = 1
        """)
        updated_equipment = cursor.fetchone()
        
        hours_worked = updated_equipment[2] - updated_equipment[3]
        
        print(f"\nApós correção:")
        print(f"  Horímetro atual: {updated_equipment[2]}h")
        print(f"  Horímetro inicial: {updated_equipment[3]}h")
        print(f"  Horas trabalhadas: {hours_worked}h")
        
        # Verificar se agora deve gerar alertas
        print(f"\nVerificação de alertas:")
        for interval in [250, 500]:
            cycles_completed = int(hours_worked // interval)
            next_maintenance_hours = (cycles_completed + 1) * interval
            hours_until_maintenance = next_maintenance_hours - hours_worked
            ninety_percent_threshold = next_maintenance_hours - (interval * 0.1)
            
            print(f"\nPlano de {interval}h:")
            print(f"  Ciclos completados: {cycles_completed}")
            print(f"  Próxima manutenção: {next_maintenance_hours}h")
            print(f"  Horas até manutenção: {hours_until_maintenance}h")
            print(f"  Limite 90%: {ninety_percent_threshold}h")
            
            if hours_worked >= next_maintenance_hours:
                print(f"  🔴 VENCIDO: {hours_worked - next_maintenance_hours}h de atraso")
            elif hours_worked >= ninety_percent_threshold:
                print(f"  🟡 PRÓXIMO: Atingiu 90% do intervalo")
            else:
                print(f"  🟢 OK: Ainda faltam {hours_until_maintenance}h")
    
    conn.close()
    print("\n=== CORREÇÃO CONCLUÍDA ===")

if __name__ == "__main__":
    fix_initial_horimeter()