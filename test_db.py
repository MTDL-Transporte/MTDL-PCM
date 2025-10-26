#!/usr/bin/env python3
"""
Script para testar a criação das tabelas e verificar o modelo Equipment
"""

import os
from sqlalchemy import create_engine, inspect
from app.database import Base
from app.models.equipment import Equipment
from app.models.maintenance import WorkOrder, MaintenancePlan, TimeLog
from app.models.warehouse import Material

# Remover banco existente
if os.path.exists("test_mtdl.db"):
    os.remove("test_mtdl.db")

# Criar novo banco
engine = create_engine("sqlite:///test_mtdl.db")

print("Criando tabelas...")
Base.metadata.create_all(bind=engine)

# Verificar colunas da tabela equipments
inspector = inspect(engine)
columns = inspector.get_columns('equipments')

print("\nColunas da tabela 'equipments':")
for column in columns:
    print(f"  - {column['name']}: {column['type']}")

print(f"\nTotal de colunas: {len(columns)}")

# Verificar se mobilization_date existe
mobilization_date_exists = any(col['name'] == 'mobilization_date' for col in columns)
print(f"Coluna 'mobilization_date' existe: {mobilization_date_exists}")

print("\nTeste concluído!")