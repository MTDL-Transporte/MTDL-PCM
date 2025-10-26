#!/usr/bin/env python3
"""
Script para configurar cenário de teste para alertas no frontend
Configurar 450h trabalhadas (90% de 500h) para gerar alerta
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import get_db
from app.models.equipment import Equipment

def setup_alert_frontend_test():
    """Configurar equipamento com 450h trabalhadas para gerar alerta"""
    db = next(get_db())
    
    try:
        # Buscar equipamento ID 1
        equipment = db.query(Equipment).filter(Equipment.id == 1).first()
        
        if not equipment:
            print("❌ Equipamento ID 1 não encontrado!")
            return
        
        print(f"📋 Equipamento encontrado: {equipment.name} ({equipment.prefix})")
        print(f"   Horímetro atual: {equipment.current_horimeter}h")
        
        # Para ter 450h trabalhadas com horímetro atual de 310h:
        # hours_worked = current_horimeter - initial_horimeter
        # 450 = 310 - initial_horimeter
        # initial_horimeter = 310 - 450 = -140
        
        new_initial_horimeter = 310.0 - 450.0  # = -140.0
        
        print(f"   Ajustando horímetro inicial para: {new_initial_horimeter}h")
        
        equipment.initial_horimeter = new_initial_horimeter
        db.commit()
        
        # Verificar cálculo
        hours_worked = equipment.current_horimeter - equipment.initial_horimeter
        print(f"   ✅ Horas trabalhadas: {hours_worked}h")
        
        # Análise dos planos
        print("\n🔍 Análise dos planos de manutenção:")
        
        # Plano de 250h
        cycles_250 = int(hours_worked // 250)
        next_250 = (cycles_250 + 1) * 250
        threshold_250 = next_250 - (250 * 0.1)  # 90%
        print(f"   📊 Plano 250h:")
        print(f"      Ciclos completados: {cycles_250}")
        print(f"      Próxima manutenção: {next_250}h")
        print(f"      Limite 90%: {threshold_250}h")
        print(f"      Status: {'🔔 ALERTA' if hours_worked >= threshold_250 and hours_worked < next_250 else '✅ OK'}")
        
        # Plano de 500h  
        cycles_500 = int(hours_worked // 500)
        next_500 = (cycles_500 + 1) * 500
        threshold_500 = next_500 - (500 * 0.1)  # 90%
        print(f"   📊 Plano 500h:")
        print(f"      Ciclos completados: {cycles_500}")
        print(f"      Próxima manutenção: {next_500}h")
        print(f"      Limite 90%: {threshold_500}h")
        print(f"      Status: {'🔔 ALERTA' if hours_worked >= threshold_500 and hours_worked < next_500 else '✅ OK'}")
        
        print(f"\n✅ Cenário configurado! Execute test_maintenance_function.py para gerar alertas")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    setup_alert_frontend_test()