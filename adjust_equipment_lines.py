import sys
from pathlib import Path
from collections import defaultdict

# Garantir que o diretório do projeto esteja no sys.path para importar o pacote app
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.database import SessionLocal
from app.models.equipment import Equipment

# Mapeamento de linhas por categoria e função principal
LINE_MAP = {
    "Amarela": {
        "func": "Movimentação de terra e obras pesadas",
        "categories": {
            # Construção pesada
            "escavadeira", "escavadeira hidraulica", "escavadeira hidráulica",
            "retroescavadeira", "pá carregadeira", "pa carregadeira",
            "rolo compactador", "motoniveladora", "perfuratriz",
            "usina de asfalto",
            # Geral
            "tratores", "trator", "trator de esteira",
        },
    },
    "Branca": {
        "func": "Apoio logístico e transporte",
        "categories": {
            "caminhões", "caminhao", "caminhão",
            "van", "vans",
            "pickup", "pick-up", "pick up", "pickups",
            # Equipamentos de apoio que já estavam marcados como 'linha_branca' nos seeds
            "betoneira", "geradores", "outros",
        },
    },
    "Verde": {
        "func": "Agricultura e florestamento",
        "categories": {
            "trator agrícola", "tratores agrícolas",
            "colheitadeira", "plantadeira",
        },
    },
    "Azul": {
        "func": "Movimentação de cargas e logística",
        "categories": {
            "empilhadeira", "empilhadeiras",
            "guindastes", "guindaste",
            "ponte rolante", "pontes rolantes",
        },
    },
    "Cinza/Preta": {
        "func": "Mineração e indústria pesada",
        "categories": {
            "britador", "britadores",
            "peneira", "peneiras",
            "caminhão fora de estrada", "caminhoes fora de estrada",
        },
    },
    "Vermelha": {
        "func": "Segurança e emergência",
        "categories": {
            "caminhão de bombeiros", "bombeiro", "bombeiros",
            "resgate", "ambulância", "ambulancia",
        },
    },
}

# Funções utilitárias

def norm(s: str) -> str:
    return (s or "").strip().lower()


def classify_by_category(category: str):
    c = norm(category)
    for line, cfg in LINE_MAP.items():
        if c in cfg["categories"]:
            return line, cfg["func"]
    return None, None


def main():
    db = SessionLocal()
    try:
        equipments = db.query(Equipment).all()
        if not equipments:
            print("Nenhum equipamento encontrado.")
            return

        updates = 0
        before_counts = defaultdict(int)
        after_counts = defaultdict(int)

        for eq in equipments:
            before_counts[(eq.equipment_class or "(vazio)")] += 1
            new_line, main_func = classify_by_category(eq.category)

            if new_line is None:
                # Sem mapeamento explícito: não altera; apenas contabiliza
                after_counts[(eq.equipment_class or "(vazio)")] += 1
                continue

            # Atualiza somente se diferente do atual
            if (eq.equipment_class or "").strip() != new_line:
                eq.equipment_class = new_line
                # Anexa a função principal na descrição, mantendo texto existente
                desc = (eq.description or "").strip()
                suffix = f" [Linha {new_line} – {main_func}]"
                if suffix not in desc:
                    eq.description = (desc + suffix).strip()
                updates += 1
            after_counts[new_line] += 1

        if updates:
            db.commit()
        else:
            db.rollback()

        print("Ajuste de classificação de equipamentos concluído.")
        print(f"Registros atualizados: {updates}")
        print("\nDistribuição antes:")
        for k, v in sorted(before_counts.items(), key=lambda x: x[0]):
            print(f"  {k}: {v}")

        print("\nDistribuição depois:")
        for k, v in sorted(after_counts.items(), key=lambda x: x[0]):
            print(f"  {k}: {v}")

    finally:
        db.close()


if __name__ == "__main__":
    main()