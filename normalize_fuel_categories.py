#!/usr/bin/env python3
"""
Normalizar categorias de materiais de combustível para o singular 'Combustível'.
Execute uma vez para migrar registros existentes que estejam com 'Combustíveis' ou variações.
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from sqlalchemy import text


def normalize():
    db = SessionLocal()
    try:
        print("=== Normalizando categorias de combustíveis ===")
        # Contar ocorrências com variações
        cnt_before = db.execute(text(
            "SELECT COUNT(*) FROM materials WHERE LOWER(category) IN ('combustiveis','combustíveis','combustivel','combustível','fuel','fuels')"
        )).fetchone()[0]
        print(f"Registros a atualizar: {cnt_before}")

        db.execute(text(
            """
            UPDATE materials
            SET category = 'Combustível'
            WHERE LOWER(category) IN ('combustiveis','combustíveis','combustivel','combustível','fuel','fuels')
            """
        ))
        db.commit()

        cnt_after = db.execute(text(
            "SELECT COUNT(*) FROM materials WHERE category = 'Combustível'"
        )).fetchone()[0]
        print(f"Concluído. Registros com categoria 'Combustível': {cnt_after}")
    except Exception as e:
        print(f"Erro ao normalizar categorias: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    normalize()