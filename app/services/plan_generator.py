"""
Serviço para gerar planos de manutenção a partir de diferentes fontes:
- Manual do fabricante (arquivo anexado)
- Busca na internet/IA (heurística com fallback)

Retorna especificações de planos compatíveis com MaintenancePlan,
incluindo ações (plan_actions) para criação automática.
Também pode incluir materiais (materials) para anexar ao plano.
"""

from typing import List, Dict, Optional, Tuple
import os
import re

def _extract_text_from_pdf(pdf_path: str) -> str:
    """Extrair texto simples de um PDF, se biblioteca estiver disponível.
    Retorna string vazia se não for possível.
    """
    try:
        import PyPDF2  # type: ignore
        text = []
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                content = page.extract_text() or ""
                text.append(content)
        return "\n".join(text)
    except Exception:
        return ""

def _extract_materials_from_xml(xml_path: str) -> Dict[int, List[Dict[str, object]]]:
    """Extrair materiais de um XML genérico.
    Heurística: procurar nós com nomes 'material', 'part', 'item' e atributos/filhos
    como 'name', 'reference', 'code', e associar a intervalos com base em 'interval', 'hours'.
    """
    import xml.etree.ElementTree as ET
    materials_by_interval: Dict[int, List[Dict[str, object]]] = {}
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except Exception:
        return materials_by_interval

    candidates = []
    for elem in root.iter():
        tag = elem.tag.lower().split('}')[-1]
        if tag in {"material", "part", "item"}:
            # Capturar campos principais e possíveis informações complementares/descrição
            description = (
                elem.attrib.get("description")
                or (elem.findtext("description") or "").strip()
                or (elem.findtext("details") or "").strip()
                or (elem.findtext("info") or "").strip()
                or (elem.findtext("observations") or "").strip()
            )
            data = {
                "name": elem.attrib.get("name") or (elem.findtext("name") or "").strip(),
                "reference": elem.attrib.get("reference") or (elem.findtext("reference") or "").strip(),
                "unit": elem.attrib.get("unit") or (elem.findtext("unit") or "un").strip() or "un",
                "quantity": elem.attrib.get("quantity") or (elem.findtext("quantity") or "1"),
                "category": elem.attrib.get("category") or (elem.findtext("category") or "").strip(),
                "description": description,
            }
            # Determinar intervalo próximo ao item
            interval_text = (
                elem.attrib.get("interval")
                or elem.attrib.get("hours")
                or elem.findtext("interval")
                or elem.findtext("hours")
                or ""
            )
            candidates.append((data, str(interval_text)))

    def _interval_from_text(s: str) -> Optional[int]:
        s = s.lower()
        m = re.search(r"(\d{2,4})\s*h", s)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                return None
        # fallback por palavra
        if "250" in s:
            return 250
        if "500" in s:
            return 500
        return None

    for data, int_text in candidates:
        interval = _interval_from_text(int_text) or 0
        # Se não conseguir determinar intervalo, tentar heurística por nomes
        if interval == 0:
            nm = (data.get("name") or "").lower()
            if any(k in nm for k in ["250h", "250 h", "250 horas"]):
                interval = 250
            elif any(k in nm for k in ["500h", "500 h", "500 horas"]):
                interval = 500

        if interval:
            try:
                data["quantity"] = float(data.get("quantity") or 1)
            except Exception:
                data["quantity"] = 1.0
            materials_by_interval.setdefault(interval, []).append(data)

    return materials_by_interval

def _extract_materials_from_text(text: str) -> Dict[int, List[Dict[str, object]]]:
    """Extrair materiais a partir de texto do manual (PDF convertido em texto).
    Heurística: procurar cabeçalhos com '250h' e '500h' e, nas linhas subsequentes,
    itens que contenham palavras-chave de materiais (óleo, filtro, graxa), capturando referências.
    """
    materials_by_interval: Dict[int, List[Dict[str, object]]] = {250: [], 500: []}
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    interval = None
    for ln in lines:
        low = ln.lower()
        if re.search(r"\b250\s*h(oras)?\b", low):
            interval = 250
            continue
        if re.search(r"\b500\s*h(oras)?\b", low):
            interval = 500
            continue
        # Capturar itens com palavras-chave
        if interval in (250, 500):
            if any(kw in low for kw in ["óleo", "lubr" , "filtro", "graxa", "hidráulico"]):
                # Extrair possível referência (P/N, Código, Ref)
                ref = None
                m = re.search(r"(P/?N|Part\s*No|Código|Cod\.|Ref\.|Referência)\s*[:\-]?\s*([A-Z0-9\-_/]+)", ln, re.I)
                if m:
                    ref = m.group(2).strip()
                # Quantidade simples
                qty = 1.0
                mq = re.search(r"(\d+[\.,]?\d*)\s*(un|l|kg|m)\b", ln, re.I)
                unit = "un"
                if mq:
                    try:
                        qty = float(mq.group(1).replace(',', '.'))
                    except Exception:
                        qty = 1.0
                    unit = mq.group(2).lower()

                materials_by_interval.setdefault(interval, []).append({
                    "name": ln,
                    "reference": ref,
                    "quantity": qty,
                    "unit": unit,
                    "description": ln,
                })

    # Limpeza dos nomes para serem mais curtos
    for iv in list(materials_by_interval.keys()):
        cleaned: List[Dict[str, object]] = []
        for item in materials_by_interval[iv]:
            name = str(item.get("name") or "").strip()
            # Remover marcadores
            name = re.sub(r"^[\-•\*\d\.\)\s]+", "", name)
            # Reduzir descrição extensa
            name = name[:200]
            item["name"] = name
            cleaned.append(item)
        materials_by_interval[iv] = cleaned

    return materials_by_interval

def extract_materials_from_document(manual_path: Optional[str]) -> Dict[int, List[Dict[str, object]]]:
    """Extrair materiais a partir de documento anexado (PDF ou XML).
    Retorna um dict mapeando intervalo (e.g., 250, 500) para lista de materiais.
    """
    if not manual_path:
        return {}
    ext = os.path.splitext(manual_path)[1].lower()
    if ext == ".xml":
        return _extract_materials_from_xml(manual_path)
    if ext == ".pdf":
        text = _extract_text_from_pdf(manual_path)
        if text:
            return _extract_materials_from_text(text)
        return {}
    # Outros formatos não suportados neste MVP
    return {}

try:
    # Pode não estar configurado; serviço deve funcionar com fallback
    from app.services.llm_provider import llm_generate  # type: ignore
except Exception:
    llm_generate = None  # Fallback se provedor não estiver disponível


# Materiais padrão por intervalo (heurística genérica)
def _default_materials_for_hours(hours: int, equipment: object) -> List[Dict[str, object]]:
    """Retorna materiais padrão esperados para manutenção preventiva de X horas.
    Este é um MVP que usa boas práticas comuns. Quantidades são estimativas e podem ser ajustadas no almoxarifado.
    """
    category_hint = getattr(equipment, "category", "") or ""
    manufacturer = getattr(equipment, "manufacturer", "") or ""
    model = getattr(equipment, "model", "") or ""

    base_filters = [
        {
            "name": "Filtro de óleo",
            "description": f"Filtro de óleo do motor {manufacturer} {model}",
            "unit": "un",
            "quantity": 1,
            "category": "Filtros",
            "reference": "FILTRO-OLEO",
            "is_critical": True,
        },
        {
            "name": "Óleo do motor",
            "description": f"Óleo lubrificante do motor para {manufacturer} {model}",
            "unit": "L",
            "quantity": 10,  # estimativa genérica
            "category": "Óleos e lubrificantes",
            "reference": "OLEO-MOTOR",
            "is_critical": True,
        },
        {
            "name": "Filtro de combustível",
            "description": f"Filtro de combustível {manufacturer} {model}",
            "unit": "un",
            "quantity": 1,
            "category": "Filtros",
            "reference": "FILTRO-COMBUSTIVEL",
            "is_critical": False,
        },
        {
            "name": "Filtro de ar",
            "description": f"Elemento filtrante de ar {manufacturer} {model}",
            "unit": "un",
            "quantity": 1,
            "category": "Filtros",
            "reference": "FILTRO-AR",
            "is_critical": False,
        },
        {
            "name": "Graxa multiuso",
            "description": f"Graxa para pontos de lubrificação {manufacturer} {model}",
            "unit": "kg",
            "quantity": 2,
            "category": "Óleos e lubrificantes",
            "reference": "GRAXA-MULTI",
            "is_critical": False,
        },
    ]

    extra_500h = [
        {
            "name": "Óleo da transmissão",
            "description": f"Óleo/transmissão {manufacturer} {model}",
            "unit": "L",
            "quantity": 8,
            "category": "Óleos e lubrificantes",
            "reference": "OLEO-TRANSMISSAO",
            "is_critical": True,
        },
        {
            "name": "Filtro hidráulico",
            "description": f"Filtro do sistema hidráulico {manufacturer} {model}",
            "unit": "un",
            "quantity": 1,
            "category": "Filtros",
            "reference": "FILTRO-HIDRAULICO",
            "is_critical": True,
        },
        {
            "name": "Óleo hidráulico",
            "description": f"Óleo do sistema hidráulico {manufacturer} {model}",
            "unit": "L",
            "quantity": 20,
            "category": "Óleos e lubrificantes",
            "reference": "OLEO-HIDRAULICO",
            "is_critical": True,
        },
    ]

    # Ajustes simples por categoria
    if "caminhao" in category_hint.lower():
        # caminhões costumam usar mais óleo
        for m in base_filters:
            if m["reference"] == "OLEO-MOTOR":
                m["quantity"] = 20
    if "escavadeira" in category_hint.lower() or "hidrául" in category_hint.lower():
        # máquinas hidráulicas: mais foco em filtro/óleo hidráulico
        for m in extra_500h:
            if m["reference"] == "OLEO-HIDRAULICO":
                m["quantity"] = 30

    return base_filters + (extra_500h if hours >= 500 else [])

def _default_actions_for_hours(interval_hours: int) -> List[Dict[str, str]]:
    actions: List[Dict[str, str]] = [
        {"description": "Inspeção visual", "action_type": "Inspeção"},
        {"description": "Lubrificação de pontos críticos", "action_type": "Ajuste"},
    ]
    if interval_hours <= 300:
        actions.extend([
            {"description": "Troca de óleo do motor", "action_type": "Troca"},
            {"description": "Troca de filtro de óleo", "action_type": "Troca"},
        ])
    else:
        actions.extend([
            {"description": "Troca de óleo e filtros (motor/transmissão)", "action_type": "Troca"},
            {"description": "Verificação de sistema hidráulico (mangueiras, conexões)", "action_type": "Inspeção"},
        ])
    return actions


def _plan_spec(
    equipment_id: int,
    name: str,
    interval_type: str,
    interval_value: int,
    description: str,
    equipment: Optional[object] = None,
) -> Dict[str, object]:
    return {
        "name": name,
        "equipment_id": equipment_id,
        "type": "Preventiva",
        "interval_type": interval_type,
        "interval_value": interval_value,
        "description": description,
        "actions": _default_actions_for_hours(interval_value if interval_type == "Horímetro" else 0),
        "materials": _default_materials_for_hours(interval_value if interval_type == "Horímetro" else 0, equipment) if equipment else [],
    }


def generate_plans_from_manual(
    equipment: object,
    manual_path: Optional[str],
) -> List[Dict[str, object]]:
    """Gera planos com base em manual anexado.
    Implementação: tenta extrair materiais/peças do documento (PDF/XML). Se nada for encontrado,
    aplica heurística padrão (250h/500h) e materiais genéricos.
    """
    eq_name = getattr(equipment, "name", "Equipamento")
    prefix = getattr(equipment, "prefix", "")
    label = f"{eq_name}" + (f" ({prefix})" if prefix else "")
    base_desc = "Planos gerados automaticamente a partir de manual do fabricante anexado."
    if manual_path:
        base_desc += f" Fonte: {os.path.basename(manual_path)}."

    extracted = extract_materials_from_document(manual_path)

    plans: List[Dict[str, object]] = []
    for iv in [250, 500]:
        materials = extracted.get(iv, []) if extracted else []
        spec = _plan_spec(
            equipment_id=equipment.id,
            name=f"Preventiva {iv}h — {label}",
            interval_type="Horímetro",
            interval_value=iv,
            description=base_desc + (" (Materiais extraídos do documento)" if materials else " (Materiais heurísticos)") ,
            equipment=equipment,
        )
        # Substituir materiais se foram extraídos do documento
        if materials:
            spec["materials"] = materials
        plans.append(spec)

    # Se LLM estiver configurado, tentar enriquecer a descrição (sem quebrar caso falhe)
    try:
        if llm_generate:
            prompt = [
                {
                    "role": "user",
                    "content": (
                        "Sugira em 2-3 linhas um resumo claro dos planos preventivos de 250h/500h, "
                        "com foco em troca de óleo, filtros e inspeções para equipamentos pesados."
                    ),
                }
            ]
            enriched = None
            # llm_generate é async; pode não estar disponível; manter robustez
            # Chamadas síncronas não são suportadas diretamente aqui. Mantemos heurística.
            # O enriquecimento poderá ser feito no futuro no endpoint (async context).
            _ = enriched  # placeholder
    except Exception:
        pass

    return plans


def generate_plans_via_internet(equipment: object) -> List[Dict[str, object]]:
    """Gera planos via heurística/IA (MVP) quando usuário escolhe buscar na internet.
    Caso IA não esteja configurada, retorna conjuntos padrão.
    """
    eq_name = getattr(equipment, "name", "Equipamento")
    prefix = getattr(equipment, "prefix", "")
    label = f"{eq_name}" + (f" ({prefix})" if prefix else "")
    base_desc = "Planos gerados automaticamente via heurística/IA (sem garantia de fabricante)."

    return [
        _plan_spec(
            equipment_id=equipment.id,
            name=f"Preventiva 250h — {label}",
            interval_type="Horímetro",
            interval_value=250,
            description=base_desc + " Inclui lubrificação e trocas básicas.",
        ),
        _plan_spec(
            equipment_id=equipment.id,
            name=f"Preventiva 500h — {label}",
            interval_type="Horímetro",
            interval_value=500,
            description=base_desc + " Inclui inspeções complementares e verificação do sistema hidráulico.",
        ),
    ]