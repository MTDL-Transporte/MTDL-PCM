import asyncio
import sqlite3
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import get_db
from app.models.equipment import Equipment
from app.routers.maintenance import check_and_create_preventive_maintenance

# Configurar banco de dados
DATABASE_URL = "sqlite:///./mtdl_pcm.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

async def test_maintenance_function():
    print("=== TESTE DA FUNÇÃO DE MANUTENÇÃO PREVENTIVA ===")
    
    # Criar sessão do banco
    db = SessionLocal()
    
    try:
        # Buscar o equipamento ID 1
        equipment = db.query(Equipment).filter(Equipment.id == 1).first()
        
        if not equipment:
            print("❌ Equipamento ID 1 não encontrado!")
            return
        
        print(f"Equipamento encontrado: {equipment.name} ({equipment.prefix})")
        print(f"Horímetro atual: {equipment.current_horimeter}h")
        print(f"Horímetro inicial: {equipment.initial_horimeter}h")
        
        hours_worked = equipment.current_horimeter - equipment.initial_horimeter
        print(f"Horas trabalhadas: {hours_worked}h")
        
        # Chamar a função de verificação
        print("\n🔍 Executando verificação de manutenção preventiva...")
        result = await check_and_create_preventive_maintenance(equipment, db)
        
        print(f"\n📊 Resultado:")
        print(f"  Ordens criadas: {result['orders_created']}")
        print(f"  Alertas criados: {result['alerts_created']}")
        
        if result['orders']:
            print(f"\n📋 Ordens de trabalho criadas:")
            for order in result['orders']:
                print(f"    ID: {order['id']} | Número: {order['number']} | Título: {order['title']}")
        
        if result['alerts']:
            print(f"\n⚠️ Alertas criados:")
            for alert in result['alerts']:
                print(f"    ID: {alert['id']} | Horas restantes: {alert['hours_remaining']}")
                print(f"    Mensagem: {alert['message']}")
        
        if result['orders_created'] == 0 and result['alerts_created'] == 0:
            print("\n💡 Nenhum alerta ou ordem foi criado. Possíveis motivos:")
            print("   - Horas trabalhadas ainda não atingiram 90% do intervalo")
            print("   - Já existem alertas/ordens para este ciclo")
            print("   - Planos de manutenção não estão configurados corretamente")
            
            # Verificar planos de manutenção
            from app.models.maintenance import MaintenancePlan
            plans = db.query(MaintenancePlan).filter(
                MaintenancePlan.equipment_id == equipment.id,
                MaintenancePlan.is_active == True,
                MaintenancePlan.interval_type == "Horímetro"
            ).all()
            
            print(f"\n📋 Planos de manutenção ativos: {len(plans)}")
            for plan in plans:
                cycles_completed = int(hours_worked // plan.interval_value)
                next_maintenance_hours = (cycles_completed + 1) * plan.interval_value
                hours_until_maintenance = next_maintenance_hours - hours_worked
                ninety_percent_threshold = next_maintenance_hours - (plan.interval_value * 0.1)
                
                print(f"\n   Plano: {plan.name} (Intervalo: {plan.interval_value}h)")
                print(f"     Ciclos completados: {cycles_completed}")
                print(f"     Próxima manutenção: {next_maintenance_hours}h")
                print(f"     Horas até manutenção: {hours_until_maintenance}h")
                print(f"     Limite 90%: {ninety_percent_threshold}h")
                
                if hours_worked >= next_maintenance_hours:
                    print(f"     🔴 DEVERIA CRIAR OS: {hours_worked}h >= {next_maintenance_hours}h")
                elif hours_worked >= ninety_percent_threshold:
                    print(f"     🟡 DEVERIA CRIAR ALERTA: {hours_worked}h >= {ninety_percent_threshold}h")
                else:
                    print(f"     🟢 OK: {hours_worked}h < {ninety_percent_threshold}h")
    
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()
    
    print("\n=== TESTE CONCLUÍDO ===")

if __name__ == "__main__":
    asyncio.run(test_maintenance_function())