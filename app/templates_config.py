"""
Configuração centralizada de templates
"""

import os
import sys
from fastapi.templating import Jinja2Templates

# Suporte a PyInstaller: base dir considera _MEIPASS
BASE_DIR = getattr(sys, '_MEIPASS', os.getcwd())
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Instância global de templates
templates = Jinja2Templates(directory=TEMPLATES_DIR)

def get_static_url(path: str) -> str:
    """Gerar URL com cache busting para arquivos estáticos"""
    try:
        file_path = os.path.join(STATIC_DIR, path.lstrip("/"))
        if os.path.exists(file_path):
            # Usar timestamp de modificação do arquivo para cache busting
            mtime = os.path.getmtime(file_path)
            return f"/static/{path}?v={int(mtime)}"
        else:
            return f"/static/{path}"
    except:
        return f"/static/{path}"

# Adicionar função ao contexto dos templates
templates.env.globals["static_url"] = get_static_url