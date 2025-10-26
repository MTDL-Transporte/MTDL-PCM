"""
Centralização da versão do aplicativo
- Lê de variável de ambiente APP_VERSION ou do arquivo VERSION
"""
import os

DEFAULT_VERSION = "1.0.0"

APP_VERSION = os.getenv("APP_VERSION")
if not APP_VERSION:
    try:
        if os.path.exists("VERSION"):
            with open("VERSION", "r", encoding="utf-8") as f:
                APP_VERSION = f.read().strip() or DEFAULT_VERSION
        else:
            APP_VERSION = DEFAULT_VERSION
    except Exception:
        APP_VERSION = DEFAULT_VERSION