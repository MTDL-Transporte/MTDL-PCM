import sys
import os
from typing import List

# Garantir que o diretório raiz do projeto esteja no PYTHONPATH
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

def main(codes: List[str]):
    from app.database import SessionLocal
    from app.models.warehouse import Material

    db = SessionLocal()
    try:
        # Remover duplicados e normalizar
        normalized = sorted(set(code.strip() for code in codes if code.strip()))
        print(f"Desativando materiais pelos códigos: {', '.join(normalized)}")

        mats = db.query(Material).filter(Material.code.in_(normalized)).all()
        if not mats:
            print("Nenhum material encontrado para os códigos fornecidos.")
            return

        for m in mats:
            if m.is_active:
                m.is_active = False
                print(f"- Desativado: code={m.code}, name={m.name}")
            else:
                print(f"- Já inativo: code={m.code}, name={m.name}")
        db.commit()
        print(f"Total processado: {len(mats)}")
    except Exception as e:
        db.rollback()
        print(f"Erro ao desativar materiais: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python scripts/deactivate_materials_by_code.py <code1> <code2> ...")
        sys.exit(1)
    main(sys.argv[1:])