#!/usr/bin/env python3
"""
Script para debugar o cálculo do valor total dos materiais
"""

import sqlite3
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def debug_total_value():
    """Debug do cálculo do valor total"""
    
    # Conectar ao banco de dados
    conn = sqlite3.connect('mtdl_pcm.db')
    cursor = conn.cursor()
    
    print("=== DEBUG CÁLCULO VALOR TOTAL ===\n")
    
    # Buscar todos os materiais ativos
    cursor.execute("""
        SELECT id, code, name, current_stock, unit_price, 
               (current_stock * COALESCE(unit_price, 0)) as calculated_value
        FROM materials 
        WHERE is_active = 1
        ORDER BY calculated_value DESC
    """)
    
    materials = cursor.fetchall()
    
    print(f"Total de materiais ativos: {len(materials)}\n")
    
    total_value = 0
    print("MATERIAIS COM MAIOR VALOR:")
    print("-" * 80)
    print(f"{'ID':<5} {'Código':<10} {'Nome':<30} {'Estoque':<10} {'Preço':<10} {'Valor Total':<12}")
    print("-" * 80)
    
    for material in materials[:10]:  # Top 10
        material_id, code, name, stock, price, calc_value = material
        total_value += calc_value or 0
        
        print(f"{material_id:<5} {code:<10} {name[:28]:<30} {stock:<10.2f} {price or 0:<10.2f} {calc_value or 0:<12.2f}")
    
    print("-" * 80)
    print(f"Valor total dos top 10: R$ {sum(m[5] or 0 for m in materials[:10]):.2f}")
    
    # Calcular valor total de todos os materiais
    cursor.execute("""
        SELECT SUM(current_stock * COALESCE(unit_price, 0)) as total_value
        FROM materials 
        WHERE is_active = 1
    """)
    
    db_total = cursor.fetchone()[0] or 0
    print(f"Valor total no banco: R$ {db_total:.2f}")
    
    # Verificar materiais com problemas
    print("\n=== MATERIAIS COM POSSÍVEIS PROBLEMAS ===")
    cursor.execute("""
        SELECT id, code, name, current_stock, unit_price
        FROM materials 
        WHERE is_active = 1 
        AND (unit_price IS NULL OR unit_price = 0 OR current_stock < 0)
        ORDER BY current_stock DESC
    """)
    
    problem_materials = cursor.fetchall()
    
    if problem_materials:
        print(f"Materiais com problemas: {len(problem_materials)}")
        print("-" * 70)
        print(f"{'ID':<5} {'Código':<10} {'Nome':<30} {'Estoque':<10} {'Preço':<10}")
        print("-" * 70)
        
        for material in problem_materials[:5]:  # Top 5 problemas
            material_id, code, name, stock, price = material
            print(f"{material_id:<5} {code:<10} {name[:28]:<30} {stock:<10.2f} {price or 'NULL':<10}")
    else:
        print("Nenhum material com problemas encontrado.")
    
    # Verificar se há diferença entre o cálculo manual e o do banco
    manual_total = sum(m[5] or 0 for m in materials)
    print(f"\nCálculo manual: R$ {manual_total:.2f}")
    print(f"Cálculo do banco: R$ {db_total:.2f}")
    print(f"Diferença: R$ {abs(manual_total - db_total):.2f}")
    
    # Verificar material específico mencionado (26 x 20 = 520)
    print("\n=== VERIFICAÇÃO MATERIAL ESPECÍFICO ===")
    cursor.execute("""
        SELECT id, code, name, current_stock, unit_price,
               (current_stock * COALESCE(unit_price, 0)) as calculated_value
        FROM materials 
        WHERE current_stock = 26 OR unit_price = 20
        ORDER BY calculated_value DESC
    """)
    
    specific_materials = cursor.fetchall()
    
    if specific_materials:
        print("Materiais com estoque 26 ou preço 20:")
        print("-" * 80)
        print(f"{'ID':<5} {'Código':<10} {'Nome':<30} {'Estoque':<10} {'Preço':<10} {'Valor':<12}")
        print("-" * 80)
        
        for material in specific_materials:
            material_id, code, name, stock, price, calc_value = material
            print(f"{material_id:<5} {code:<10} {name[:28]:<30} {stock:<10.2f} {price or 0:<10.2f} {calc_value or 0:<12.2f}")
    else:
        print("Nenhum material encontrado com estoque 26 ou preço 20.")
    
    conn.close()

if __name__ == "__main__":
    debug_total_value()