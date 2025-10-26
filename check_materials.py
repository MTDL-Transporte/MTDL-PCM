import sqlite3

def check_materials():
    conn = sqlite3.connect('mtdl_pcm.db')
    cursor = conn.cursor()
    
    # Verificar estrutura da tabela materials
    cursor.execute("PRAGMA table_info(materials)")
    columns = cursor.fetchall()
    print("Estrutura da tabela materials:")
    for col in columns:
        print(f"  {col[1]} ({col[2]})")
    print()
    
    # Verificar todos os materiais
    cursor.execute("SELECT * FROM materials")
    materials = cursor.fetchall()
    print(f"Total de materiais: {len(materials)}")
    print()
    
    # Verificar materiais relacionados a filtro
    cursor.execute("SELECT * FROM materials WHERE name LIKE '%filtro%' OR name LIKE '%FILTRO%'")
    filtros = cursor.fetchall()
    print("Materiais relacionados a filtro:")
    for material in filtros:
        print(f"  ID: {material[0]}, Código: {material[1]}, Nome: {material[2]}")
        if len(material) > 4:
            print(f"    Quantidade: {material[4]}, Valor Unitário: {material[5] if len(material) > 5 else 'N/A'}")
    print()
    
    # Verificar se existe código 100.000
    cursor.execute("SELECT * FROM materials WHERE code = '100.000'")
    item_100 = cursor.fetchone()
    if item_100:
        print(f"Item com código 100.000 encontrado: {item_100}")
    else:
        print("Nenhum item com código 100.000 encontrado")
    
    conn.close()

if __name__ == "__main__":
    check_materials()