"""
MTDL-PCM - Sistema de Manutenção e Controle de Equipamentos
Aplicação principal FastAPI
"""

from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import uvicorn
import os
import sys
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from app.models.idempotency import IdempotencyRecord

# Carregar variáveis de ambiente do .env (antes de importar o banco)
load_dotenv()

# Importar configuração do banco de dados
from app.database import engine, Base, get_db

# Importar routers
from app.routers import dashboard, maintenance, warehouse, reports, hr, construction, admin
from app.routers.sync import router as sync_router

# Importar modelos para criar as tabelas
from app.models.equipment import Equipment, HorimeterLog
from app.models.maintenance import WorkOrder, MaintenancePlan, TimeLog, MaintenancePlanMaterial, WorkOrderMaterial
from app.models.warehouse import Material, Supplier, StockMovement, PurchaseRequest, PurchaseRequestItem, Quotation, QuotationItem
from app.models.hr import Employee
from app.models.admin import User, Role, Permission, UserRole, RolePermission, SessionToken, Module


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware para adicionar headers de segurança"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Content Security Policy
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "img-src 'self' data: https:; "
            "font-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "connect-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        
        # Adicionar headers de segurança
        response.headers["Content-Security-Policy"] = csp
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerenciar ciclo de vida da aplicação"""
    # Startup
    print("🚀 Iniciando MTDL-PCM...")
    
    # Criar tabelas do banco de dados
    print("📊 Criando tabelas do banco de dados...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tabelas criadas com sucesso!")
    # Migração simples: garantir colunas ausentes na tabela purchase_requests (SQLite)
    try:
        if "sqlite" in str(engine.url):
            from sqlalchemy import text
            with engine.connect() as conn:
                cols = {row[1] for row in conn.execute(text("PRAGMA table_info('purchase_requests')"))}
                if 'cost_center' not in cols:
                    conn.execute(text("ALTER TABLE purchase_requests ADD COLUMN cost_center VARCHAR(100)"))
                if 'stock_justification' not in cols:
                    conn.execute(text("ALTER TABLE purchase_requests ADD COLUMN stock_justification TEXT"))
                if 'total_value' not in cols:
                    conn.execute(text("ALTER TABLE purchase_requests ADD COLUMN total_value FLOAT DEFAULT 0.0"))
                if 'approved_date' not in cols:
                    conn.execute(text("ALTER TABLE purchase_requests ADD COLUMN approved_date DATETIME"))
                if 'approved_by' not in cols:
                    conn.execute(text("ALTER TABLE purchase_requests ADD COLUMN approved_by VARCHAR(100)"))
            print("🔄 Migração automática aplicada para purchase_requests (SQLite).")
            # Migração automática: adicionar coluna hr_matricula em technicians
            with engine.connect() as conn:
                tech_cols = {row[1] for row in conn.execute(text("PRAGMA table_info('technicians')"))}
                if 'hr_matricula' not in tech_cols:
                    conn.execute(text("ALTER TABLE technicians ADD COLUMN hr_matricula INTEGER"))
            print("🔄 Migração automática aplicada para technicians.hr_matricula (SQLite).")
            # Migração automática: adicionar colunas em stock_movements
            with engine.connect() as conn:
                sm_cols = {row[1] for row in conn.execute(text("PRAGMA table_info('stock_movements')"))}
                if 'cost_center' not in sm_cols:
                    conn.execute(text("ALTER TABLE stock_movements ADD COLUMN cost_center VARCHAR(100)"))
                if 'equipment_id' not in sm_cols:
                    conn.execute(text("ALTER TABLE stock_movements ADD COLUMN equipment_id INTEGER"))
                if 'application' not in sm_cols:
                    conn.execute(text("ALTER TABLE stock_movements ADD COLUMN application VARCHAR(200)"))
            print("🔄 Migração automática aplicada para stock_movements (SQLite).")
            # Migração automática: adicionar colunas em equipments
            with engine.connect() as conn:
                eq_cols = {row[1] for row in conn.execute(text("PRAGMA table_info('equipments')"))}
                if 'company_name' not in eq_cols:
                    conn.execute(text("ALTER TABLE equipments ADD COLUMN company_name VARCHAR(10)"))
                if 'demobilization_date' not in eq_cols:
                    conn.execute(text("ALTER TABLE equipments ADD COLUMN demobilization_date DATETIME"))
                # Adicionar coluna category para equipamentos (tipo do equipamento)
                if 'category' not in eq_cols:
                    conn.execute(text("ALTER TABLE equipments ADD COLUMN category VARCHAR(100)"))
                # Adicionar coluna fleet (frota: Propria/Terceirizada)
                if 'fleet' not in eq_cols:
                    conn.execute(text("ALTER TABLE equipments ADD COLUMN fleet VARCHAR(20)"))
                # Adicionar coluna cnpj (identificação da empresa)
                if 'cnpj' not in eq_cols:
                    conn.execute(text("ALTER TABLE equipments ADD COLUMN cnpj VARCHAR(18)"))
                # Adicionar coluna company_legal_name (razão social)
                if 'company_legal_name' not in eq_cols:
                    conn.execute(text("ALTER TABLE equipments ADD COLUMN company_legal_name VARCHAR(200)"))
                # Adicionar coluna monthly_quota (franquia mensal de horas)
                if 'monthly_quota' not in eq_cols:
                    conn.execute(text("ALTER TABLE equipments ADD COLUMN monthly_quota FLOAT"))
            print("🔄 Migração automática aplicada para equipments (SQLite).")
            # Migração automática: adicionar coluna status em error_logs
            with engine.connect() as conn:
                el_cols = {row[1] for row in conn.execute(text("PRAGMA table_info('error_logs')"))}
                if 'status' not in el_cols:
                    conn.execute(text("ALTER TABLE error_logs ADD COLUMN status VARCHAR(20) DEFAULT 'open'"))
            print("🔄 Migração automática aplicada para error_logs.status (SQLite).")
    except Exception as e:
        print(f"⚠️ Falha ao aplicar migração automática: {e}")

    # Reconciliação preventiva inicial com base nos dados existentes
    try:
        from app.database import SessionLocal
        from app.models.equipment import Equipment
        from app.routers.maintenance import check_and_create_preventive_maintenance

        db = SessionLocal()
        equipments = db.query(Equipment).filter(
            Equipment.initial_horimeter != None,
            Equipment.current_horimeter != None
        ).all()

        total_orders = 0
        total_alerts = 0

        for equipment in equipments:
            result = await check_and_create_preventive_maintenance(equipment, db)
            if isinstance(result, dict):
                total_orders += result.get("orders_created", 0)
                total_alerts += result.get("alerts_created", 0)

        db.close()
        print(f"🔎 Reconciliação preventiva inicial concluída: {total_orders} OS, {total_alerts} alertas.")
    except Exception as e:
        print(f"⚠️ Falha na reconciliação preventiva inicial: {e}")
    
    # Garantir usuário admin padrão
    try:
        from app.database import SessionLocal
        from app.models.admin import User, Role, UserRole
        from app.routers.admin import generate_salt, hash_password
        db = SessionLocal()
        admin_user = db.query(User).filter(User.username == 'admin').first()
        if not admin_user:
            salt = generate_salt()
            pwd_hash = hash_password('Admin@PCM2025!', salt)
            admin_user = User(
                username='admin',
                email='admin@mtdl.local',
                full_name='Administrador',
                sector='Admin',
                password_salt=salt,
                password_hash=pwd_hash,
                is_active=True,
                is_admin=True,
                must_change_password=False
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            # Garantir papel Admin
            role = db.query(Role).filter(Role.name == 'Admin').first()
            if not role:
                role = Role(name='Admin', description='Perfil Admin')
                db.add(role)
                db.commit()
                db.refresh(role)
            db.add(UserRole(user_id=admin_user.id, role_id=role.id))
            db.commit()
            print("👑 Usuário padrão 'admin' criado com senha inicial.")
        else:
            # Garantir flag is_admin e associação de perfil
            if not admin_user.is_admin:
                admin_user.is_admin = True
                db.add(admin_user)
                db.commit()
            role = db.query(Role).filter(Role.name == 'Admin').first()
            from sqlalchemy import and_
            if role:
                assoc = db.query(UserRole).filter(and_(UserRole.user_id == admin_user.id, UserRole.role_id == role.id)).first()
                if not assoc:
                    db.add(UserRole(user_id=admin_user.id, role_id=role.id))
                    db.commit()
        db.close()
    except Exception as e:
        print(f"⚠️ Falha ao garantir usuário admin padrão: {e}")

    # Semear módulos padrão
    try:
        from app.database import SessionLocal
        from app.models.admin import Module
        db = SessionLocal()
        default_modules = [
            ("dashboard", "Dashboard principal"),
            ("maintenance", "Manutenção"),
            ("warehouse", "Almoxarifado"),
            ("reports", "Relatórios"),
            ("hr", "Recursos Humanos"),
            ("construction", "Apropriação de Obra"),
            ("commercial", "Comercial"),
            ("admin", "Administração"),
        ]
        created = 0
        for name, desc in default_modules:
            exists = db.query(Module).filter(Module.name == name).first()
            if not exists:
                db.add(Module(name=name, description=desc, is_active=True))
                created += 1
        if created:
            db.commit()
            print(f"🌱 Módulos padrão semeados: {created}")
        db.close()
    except Exception as e:
        print(f"⚠️ Falha ao semear módulos padrão: {e}")

    yield
    
    # Shutdown
    print("🛑 Encerrando MTDL-PCM...")


# Criar instância do FastAPI
app = FastAPI(
    title="MTDL-PCM",
    description="Sistema de Manutenção e Controle de Equipamentos",
    version="1.0.0",
    lifespan=lifespan
)

class IdempotencyMiddleware(BaseHTTPMiddleware):
    """Middleware para idempotência em rotas de API mutáveis.
    Usa header 'X-Idempotency-Key' para retornar a mesma resposta
    quando a operação já foi realizada com o mesmo payload.
    """
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method.upper()
        # Somente para rotas de API mutáveis
        if not path.startswith('/api/') or method not in ('POST','PUT','PATCH','DELETE'):
            return await call_next(request)
        key = request.headers.get('X-Idempotency-Key')
        if not key:
            return await call_next(request)
        # Ler o corpo da requisição e calcular hash
        body = await request.body()
        try:
            import hashlib
            body_hash = hashlib.sha256(body or b'').hexdigest()
        except Exception:
            body_hash = 'no-body'
        # Checar registro existente
        from app.database import SessionLocal
        db = SessionLocal()
        try:
            existing = db.query(IdempotencyRecord).filter_by(
                key=key, method=method, path=path, body_hash=body_hash
            ).first()
        finally:
            db.close()
        if existing:
            # Retornar resposta previamente armazenada
            return Response(content=existing.response_body or '', status_code=existing.status_code, media_type='application/json')
        # Repassar a requisição (reconstituindo o corpo)
        async def receive():
            return {'type': 'http.request', 'body': body, 'more_body': False}
        request = Request(request.scope, receive)
        response = await call_next(request)
        # Capturar corpo da resposta
        resp_body = b''
        async for chunk in response.body_iterator:
            resp_body += chunk
        # Armazenar resposta para a chave
        db2 = SessionLocal()
        try:
            rec = IdempotencyRecord(
                key=key,
                method=method,
                path=path,
                body_hash=body_hash,
                status_code=response.status_code,
                response_body=resp_body.decode('utf-8', errors='ignore')
            )
            db2.add(rec)
            db2.commit()
        except Exception as e:
            db2.rollback()
            print('⚠️ Falha ao salvar idempotência:', e)
        finally:
            db2.close()
        # Retornar resposta com corpo reconstruído
        return Response(content=resp_body, status_code=response.status_code, headers=dict(response.headers), media_type=response.media_type)

# Configurar middlewares de segurança
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(IdempotencyMiddleware)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configurar arquivos estáticos e templates com cache busting
# Suporte a PyInstaller: usar base dir com _MEIPASS quando existir
BASE_DIR = getattr(sys, '_MEIPASS', os.getcwd())
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

# Adicionar função para cache busting
import time
# Importar configuração de templates
from app.templates_config import templates
# Versão do app para API
from app.version import APP_VERSION

# Rota raiz movida acima dos routers para priorizar redirecionamento

# Incluir routers
app.include_router(dashboard.router, prefix="", tags=["Admin"])  # mantém dashboard atual
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard API"])  
# Admin API
app.include_router(admin.router, prefix="/api/admin", tags=["Admin API"]) 
# Demais APIs
app.include_router(maintenance.router, prefix="/api/maintenance", tags=["Manutenção API"]) 
app.include_router(warehouse.router, prefix="/api/warehouse", tags=["Almoxarifado API"]) 
app.include_router(reports.router, prefix="/api/reports", tags=["Relatórios API"]) 
app.include_router(hr.router, prefix="", tags=["RH API"]) 
app.include_router(construction.router, prefix="", tags=["Apropriação de Obra"]) 
app.include_router(sync_router, prefix="/api/sync", tags=["Sync API"])

# Incluir routers para páginas HTML
app.include_router(maintenance.router, prefix="/maintenance", tags=["Manutenção Páginas"]) 
app.include_router(maintenance.router, prefix="/equipment", tags=["Equipamentos"]) 
app.include_router(warehouse.router, prefix="/warehouse", tags=["Almoxarifado Páginas"]) 
app.include_router(warehouse.router, prefix="/inventory", tags=["Inventário"]) 
app.include_router(reports.router, prefix="/reports", tags=["Relatórios Páginas"]) 
# Admin páginas HTML
app.include_router(admin.router, prefix="/admin", tags=["Painel Admin Páginas"])


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Página inicial - redireciona para login"""
    return RedirectResponse(url="/admin/login", status_code=302)


@app.get("/health")
async def health_check():
    """Endpoint para verificação de saúde da aplicação"""
    return {
        "status": "healthy",
        "message": "MTDL-PCM está funcionando corretamente",
        "version": "1.0.0"
    }


@app.get("/favicon.ico")
async def favicon():
    return RedirectResponse(url="/static/img/favicon.svg")

@app.get("/offline", response_class=HTMLResponse)
async def offline_page(request: Request):
    """Página de fallback para navegação em modo offline"""
    return templates.TemplateResponse("offline.html", {"request": request})

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handler para páginas não encontradas"""
    return templates.TemplateResponse(
        "error.html", 
        {
            "request": request, 
            "error_code": 404,
            "error_message": "Página não encontrada"
        },
        status_code=404
    )


@app.exception_handler(403)
async def forbidden_handler(request: Request, exc):
    """Handler para acesso não autorizado"""
    # Se for uma rota de API, retornar JSON
    if request.url.path.startswith("/api/"):
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=403,
            content={
                "error_code": 403,
                "error_message": "Acesso não autorizado"
            }
        )
    # Caso contrário, página HTML amigável
    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "error_code": 403,
            "error_message": "Você não tem autorização para acessar este módulo"
        },
        status_code=403
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Handler para erros internos do servidor"""
    import traceback
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    print("\n===== ERRO 500 DETALHES =====\n", tb)
    # Se for uma rota de API, retornar JSON para facilitar o consumo
    if request.url.path.startswith("/api/"):
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=500,
            content={
                "error_code": 500,
                "error_message": "Erro interno do servidor",
                "detail": str(exc),
            }
        )
    # Caso contrário, retornar página HTML amigável
    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "error_code": 500,
            "error_message": "Erro interno do servidor"
        },
        status_code=500
    )


if __name__ == "__main__":
    # Configurações para desenvolvimento
    print("🔧 MTDL-PCM - Sistema de Manutenção e Controle de Equipamentos")
    print("📍 Acesse: http://localhost:8000")
    print("📚 Documentação da API: http://localhost:8000/docs")
    print("🔍 Redoc: http://localhost:8000/redoc")
    
    # Verificar se o diretório de banco de dados existe
    db_dir = "data"
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
        print(f"📁 Diretório {db_dir} criado para o banco de dados")
    
    # Executar servidor
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
# Registrar exceções globais em ErrorLog sem alterar respostas padrão
from app.database import SessionLocal
from app.models.admin import ErrorLog
import traceback, json

def _extract_module_from_path(path: str) -> str:
    try:
        if path.startswith('/api/'):
            seg = path[5:].split('/', 1)[0]
            return seg or 'api'
        seg = path.lstrip('/').split('/', 1)[0]
        return seg or 'root'
    except Exception:
        return 'unknown'

async def _log_error_to_db(request: Request, exc: Exception):
    tb = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    module = _extract_module_from_path(request.url.path)
    ctx = {
        'path': request.url.path,
        'method': request.method,
        'query': dict(request.query_params or {}),
        'client': getattr(request, 'client', None).host if getattr(request, 'client', None) else None,
        'headers_subset': {k.lower(): request.headers.get(k) for k in ['User-Agent','X-Request-ID']}
    }
    try:
        db = SessionLocal()
        log = ErrorLog(module=module, error_type=type(exc).__name__, message=str(exc), stack=tb, context=json.dumps(ctx, ensure_ascii=False))
        db.add(log)
        db.commit()
    except Exception as e:
        print('⚠️ Falha ao gravar ErrorLog:', e)
    finally:
        try:
            db.close()
        except Exception:
            pass

@app.middleware("http")
async def exception_logging_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:
        await _log_error_to_db(request, exc)
        raise