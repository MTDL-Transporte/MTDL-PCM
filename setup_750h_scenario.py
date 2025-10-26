#!/usr/bin/env python3
"""
Script para configurar cenário de teste com 750h trabalhadas
Deve gerar OS para 250h, 500h e 750h do plano de 250h
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import get_db
from app.models.equipment import Equipment

def setup_750h_scenario():
    """Configurar equipamento com 750h trabalhadas"""
    db = next(get_db())
    
    try:
        # Buscar equipamento ID 1
        equipment = db.query(Equipment).filter(Equipment.id == 1).first()
        
        if not equipment:
            print("❌ Equipamento ID 1 não encontrado!")
            return
        
        print(f"📋 Equipamento encontrado: {equipment.name} ({equipment.prefix})")
        print(f"   Horímetro atual: {equipment.current_horimeter}h")
        
        # Para ter 750h trabalhadas com horímetro atual de 310h:
        # hours_worked = current_horimeter - initial_horimeter
        # 750 = 310 - initial_horimeter
        # initial_horimeter = 310 - 750 = -440
        
        new_initial_horimeter = 310.0 - 750.0  # = -440.0
        
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
        print(f"   📊 Plano 250h: {cycles_250} ciclos completados")
        print(f"      Marcos atingidos: 250h, 500h, 750h")
        print(f"      Próxima manutenção: {(cycles_250 + 1) * 250}h")
        
        # Plano de 500h  
        cycles_500 = int(hours_worked // 500)
        print(f"   📊 Plano 500h: {cycles_500} ciclos completados")
        print(f"      Marcos atingidos: 500h")
        print(f"      Próxima manutenção: {(cycles_500 + 1) * 500}h")
        
        print(f"\n✅ Cenário configurado! Execute test_maintenance_function.py")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    setup_750h_scenario()