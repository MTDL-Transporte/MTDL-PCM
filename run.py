import os
import sys

# Permite configurar porta por variável de ambiente
PORT = int(os.getenv("PORT", "8000"))

# Habilita modo PyInstaller (_MEIPASS) se necessário
BASE_DIR = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__)))

# Inicializa o servidor FastAPI via Uvicorn
if __name__ == "__main__":
    import uvicorn
    from main import app
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info", reload=False)