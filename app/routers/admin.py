"""
Router para Painel Admin (Backoffice)
"""

from fastapi import APIRouter, Request, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.templates_config import templates
from app.models.maintenance import WorkOrder
from app.models.equipment import Equipment
from app.models.warehouse import Material
from app.models.hr import Employee

from datetime import datetime, timedelta
import secrets
import hashlib
import smtplib
from email.message import EmailMessage
import os
from app.models.admin import User, Role, Permission, UserRole, RolePermission, SessionToken
from app.models.admin import Module, License
from starlette.responses import RedirectResponse
from typing import Optional
from app.version import APP_VERSION

router = APIRouter()

# Utilitários de autenticação
HASH_ITERATIONS = 130_000
TOKEN_TTL_HOURS = 24

# Helpers: configurações, política de senha e auditoria
from typing import Optional
from app.models.admin import SystemSetting, AuditLog, Sector
from app.models.admin import ErrorLog

def get_setting_int(db: Session, key: str, default: int) -> int:
    setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if not setting or setting.value is None:
        return default
    try:
        return int(setting.value)
    except Exception:
        return default

import re

def validate_password_policy(password: str) -> Optional[str]:
    if len(password) < 8:
        return "A senha deve ter pelo menos 8 caracteres"
    if not re.search(r"[A-Z]", password):
        return "A senha deve conter uma letra maiúscula"
    if not re.search(r"[a-z]", password):
        return "A senha deve conter uma letra minúscula"
    if not re.search(r"\d", password):
        return "A senha deve conter um dígito"
    if not re.search(r"[!@#$%^&*()_+\-={}\[\]:;\"'<>.,.?/]", password):
        return "A senha deve conter um símbolo"
    return None

def log_audit(db: Session, user_id: Optional[int], action: str, entity: Optional[str] = None, entity_id: Optional[int] = None, changes: Optional[str] = None):
    db.add(AuditLog(user_id=user_id, action=action, entity=entity, entity_id=entity_id, changes=changes))
    db.commit()

def send_email_stub(db: Session, to: Optional[str], subject: str, body: str, user_id: Optional[int] = None):
    # Simula envio e registra log
    log_audit(db, user_id, "email_sent", entity="email", changes=f"to={to}; subject={subject}; body={body[:200]}")

# Envio real via SMTP; se faltar configuração, faz fallback para stub
def send_email_smtp(db: Session, to: Optional[str], subject: str, body: str, user_id: Optional[int] = None) -> bool:
    server = os.getenv("SMTP_SERVER")
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    email_from = os.getenv("EMAIL_FROM") or username
    if not (server and username and password and email_from and to):
        # Sem configuração completa: registra via stub
        send_email_stub(db, to, subject, body, user_id)
        return False
    try:
        msg = EmailMessage()
        msg["From"] = email_from
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)
        with smtplib.SMTP(server, port, timeout=10) as smtp:
            smtp.starttls()
            smtp.login(username, password)
            smtp.send_message(msg)
        log_audit(db, user_id, "email_sent", entity="email", changes=f"to={to}; subject={subject}; via=smtp")
        return True
    except Exception as e:
        try:
            db.add(ErrorLog(module="admin", error_type="email_send_failure", message=str(e), context=f"to={to}; subject={subject}"))
            db.commit()
        except Exception:
            pass
        send_email_stub(db, to, subject, body, user_id)
        return False

def generate_salt() -> str:
    return secrets.token_hex(16)

# Senha temporária simples e memorizável
def generate_simple_temp_password() -> str:
    # Prefixo identificável + 6 dígitos
    return f"mtdl{secrets.randbelow(900000)+100000}"

# Normalizar código de Obra/Empresa para formato 3 dígitos (001-999)
def normalize_company_code(code: Optional[str]) -> Optional[str]:
    if code is None:
        return None
    s = str(code).strip()
    if not s:
        return None
    # manter apenas dígitos
    digits = ''.join(ch for ch in s if ch.isdigit())
    if not digits:
        return None
    try:
        n = int(digits)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Código de Obra/Empresa inválido")
    if n < 1 or n > 999:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Código de Obra/Empresa deve ser de 001 a 999")
    return str(n).zfill(3)

def hash_password(password: str, salt_hex: str) -> str:
    return hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        bytes.fromhex(salt_hex),
        HASH_ITERATIONS
    ).hex()

def verify_password(password: str, salt_hex: str, stored_hash_hex: str) -> bool:
    return hash_password(password, salt_hex) == stored_hash_hex

def create_session_token(user_id: int, db: Session, ttl_hours: Optional[int] = None) -> SessionToken:
    ttl = ttl_hours if ttl_hours is not None else get_setting_int(db, "token_ttl_hours", TOKEN_TTL_HOURS)
    token = secrets.token_urlsafe(32)
    expires = datetime.utcnow() + timedelta(hours=ttl)
    session = SessionToken(user_id=user_id, token=token, expires_at=expires)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session

# Página inicial do Painel Admin (protegida abaixo)
# Removida definição duplicada não protegida

# Página de Login
@router.get("/login")
async def admin_login_page(request: Request):
    return templates.TemplateResponse("admin/login.html", {"request": request})

# API: overview com contagens básicas
@router.get("/overview")
async def admin_overview(db: Session = Depends(get_db)):
    """Resumo rápido para cards do Painel Admin"""
    total_work_orders = db.query(func.count(WorkOrder.id)).scalar() or 0
    total_equipment = db.query(func.count(Equipment.id)).scalar() or 0
    total_materials = db.query(func.count(Material.id)).scalar() or 0
    total_employees = db.query(func.count(Employee.id)).scalar() or 0
    return {
        "status": "ok",
        "metrics": {
            "work_orders": int(total_work_orders),
            "equipment": int(total_equipment),
            "materials": int(total_materials),
            "employees": int(total_employees),
        }
    }

# API: cadastro de usuário
@router.post("/auth/register")
async def admin_register(request: Request, db: Session = Depends(get_db)):
    payload = await request.json()
    username = (payload.get("username") or "").strip()
    email = (payload.get("email") or None)
    full_name = (payload.get("full_name") or None)
    sector = (payload.get("sector") or None)
    # novo: código de Obra/Empresa
    company_code = normalize_company_code(payload.get("company_code"))
    is_admin = bool(payload.get("is_admin", False))
    role_name = payload.get("role_name") or ("Admin" if is_admin else "Usuario")

    if not username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="username obrigatório")

    existing = db.query(User).filter(User.username == username).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Usuário já existe")

    raw_password = payload.get("password")
    generate_temp_password = bool(payload.get("generate_temp_password", not bool(raw_password)))
    if not raw_password:
        raw_password = generate_simple_temp_password()

    # Política de senha apenas para senha definida manualmente
    if not generate_temp_password:
        policy_error = validate_password_policy(raw_password)
        if policy_error:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=policy_error)

    salt = generate_salt()
    pwd_hash = hash_password(raw_password, salt)

    user = User(
        username=username,
        email=email,
        full_name=full_name,
        sector=sector,
        company_code=company_code,  # novo campo
        password_hash=pwd_hash,
        password_salt=salt,
        is_active=True,
        is_admin=is_admin,
        must_change_password=generate_temp_password,
        temp_password_expires_at=(datetime.utcnow() + timedelta(days=90)) if generate_temp_password else None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    role = db.query(Role).filter(Role.name == role_name).first()
    if not role:
        role = Role(name=role_name, description=f"Perfil {role_name}")
        db.add(role)
        db.commit()
        db.refresh(role)

    db.add(UserRole(user_id=user.id, role_id=role.id))
    db.commit()

    # Conceder licença de módulo com base no setor informado
    try:
        if sector:
            sector_norm = (sector or "").strip().upper()
            sector_to_module = {
                "ALMOXARIFADO": "warehouse",
                "MANUTENÇÃO": "maintenance",
                "RECURSOS HUMANOS": "hr",
                "COMERCIAL": "commercial",
                "APROPRIAÇÃO DE OBRA": "construction",
            }
            mod_name = sector_to_module.get(sector_norm)
            if mod_name:
                mod = db.query(Module).filter(Module.name == mod_name).first()
                if mod:
                    existing_license = db.query(License).filter(License.user_id == user.id, License.module_id == mod.id).first()
                    if not existing_license:
                        db.add(License(user_id=user.id, module_id=mod.id, license_type="restricted", expires_at=None, is_active=True))
                        db.commit()
    except Exception:
        # manter robustez do cadastro mesmo se licença falhar
        pass

    # Registrar auditoria
    log_audit(db, user_id=user.id, action="create_user", entity="users", entity_id=user.id, changes=f"username={username}; is_admin={is_admin}")

    # Enviar e-mail com senha temporária, se aplicável
    if generate_temp_password and email:
        send_email_smtp(db, to=email, subject="Credenciais de acesso temporárias", body=f"Login: {username}\nSenha: {raw_password}\nLink: /admin/login", user_id=user.id)

    session = create_session_token(user.id, db)

    return {
        "status": "ok",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "company_code": user.company_code,  # novo
            "is_admin": user.is_admin,
            "must_change_password": user.must_change_password,
        },
        "token": session.token,
        "temp_password": raw_password if generate_temp_password else None,
    }

# API: login
@router.post("/auth/login")
async def admin_login(request: Request, db: Session = Depends(get_db)):
    payload = await request.json()
    username = (payload.get("username") or "").strip()
    password = payload.get("password") or ""

    if not username or not password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Credenciais inválidas")

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário ou senha incorretos")

    if not verify_password(password, user.password_salt, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário ou senha incorretos")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuário inativo")

    session = create_session_token(user.id, db)

    return {
        "status": "ok",
        "token": session.token,
        "expires_at": session.expires_at.isoformat(),
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "company_code": user.company_code,  # novo
            "is_admin": user.is_admin,
            "must_change_password": user.must_change_password,
            "modules": get_user_modules(user.id, db),
        },
    }

# API: dados do usuário corrente
@router.get("/auth/me")
async def admin_me(request: Request, db: Session = Depends(get_db)):
    auth_header = request.headers.get("Authorization") or ""
    token_value = None
    if auth_header.lower().startswith("bearer "):
        token_value = auth_header.split(" ", 1)[1].strip()
    if not token_value:
        token_value = request.query_params.get("token")
    if not token_value:
        try:
            payload = await request.json()
            token_value = payload.get("token") if isinstance(payload, dict) else None
        except Exception:
            token_value = None

    if not token_value:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token ausente")

    session = db.query(SessionToken).filter(
        SessionToken.token == token_value,
        SessionToken.is_revoked == False,
    ).first()
    if not session or session.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido ou expirado")

    user = db.query(User).get(session.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")

    return {
        "status": "ok",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "sector": user.sector,
            "company_code": user.company_code,  # novo
            "is_admin": user.is_admin,
            "must_change_password": user.must_change_password,
            "modules": get_user_modules(user.id, db),
        }
    }

# API: logout (revoga token e apaga cookie)
@router.post("/auth/logout")
async def admin_logout(request: Request, response: Response, db: Session = Depends(get_db)):
    payload = await request.json()
    token_value = (payload.get("token") or "").strip()
    if not token_value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token obrigatório")

    session = db.query(SessionToken).filter(SessionToken.token == token_value).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sessão não encontrada")

    session.is_revoked = True
    db.add(session)
    db.commit()
    # Apagar cookie de autenticação
    response.delete_cookie("auth_token", path="/")
    return {"status": "ok"}

# Helper: obtém usuário pelo token do request (header/cookie/query/body)
def get_user_from_request_token(request: Request, db: Session) -> Optional[User]:
    auth_header = request.headers.get("Authorization") or ""
    token_value = None
    if auth_header.lower().startswith("bearer "):
        token_value = auth_header.split(" ", 1)[1].strip()
    # tenta cookie
    if not token_value:
        token_value = request.cookies.get("auth_token")
    # fallback query
    if not token_value:
        token_value = request.query_params.get("token")
    # fallback body
    if not token_value:
        try:
            payload = request.json() if hasattr(request, 'json') else None
        except Exception:
            payload = None
        if payload and isinstance(payload, dict):
            token_value = payload.get("token")
    if not token_value:
        return None
    session = db.query(SessionToken).filter(
        SessionToken.token == token_value,
        SessionToken.is_revoked == False,
    ).first()
    if not session or session.expires_at < datetime.utcnow():
        return None
    return db.query(User).get(session.user_id)

# Protege página inicial do Admin com redirect para login + RBAC
@router.get("/")
async def admin_home(request: Request, db: Session = Depends(get_db)):
    user = get_user_from_request_token(request, db)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito ao perfil Admin")
    return templates.TemplateResponse("admin/index.html", {"request": request, "current_user": user})

# Página de troca de senha
@router.get("/change-password")
async def admin_change_password_page(request: Request, db: Session = Depends(get_db)):
    user = get_user_from_request_token(request, db)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)
    return templates.TemplateResponse("admin/change_password.html", {"request": request, "current_user": user})

# Endpoint: troca de senha
@router.post("/auth/change-password")
async def admin_change_password(request: Request, db: Session = Depends(get_db)):
    # identifica usuário pelo token (header/cookie)
    auth_header = request.headers.get("Authorization") or ""
    token_value = None
    if auth_header.lower().startswith("bearer "):
        token_value = auth_header.split(" ", 1)[1].strip()
    if not token_value:
        token_value = request.cookies.get("auth_token")
    if not token_value:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token ausente")

    session = db.query(SessionToken).filter(
        SessionToken.token == token_value,
        SessionToken.is_revoked == False,
    ).first()
    if not session or session.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido ou expirado")

    user = db.query(User).get(session.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")

    payload = await request.json()
    old_password = (payload.get("old_password") or "").strip()
    new_password = (payload.get("new_password") or "").strip()

    # Validação por política de segurança
    policy_error = validate_password_policy(new_password)
    if policy_error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=policy_error)

    # Se não exigir troca obrigatória, valida senha antiga
    if not user.must_change_password:
        if not old_password or not verify_password(old_password, user.password_salt, user.password_hash):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Senha atual incorreta")

    new_salt = generate_salt()
    new_hash = hash_password(new_password, new_salt)
    user.password_salt = new_salt
    user.password_hash = new_hash
    user.must_change_password = False
    user.temp_password_expires_at = None
    db.add(user)
    db.commit()

    # Auditoria
    log_audit(db, user_id=user.id, action="change_password", entity="users", entity_id=user.id, changes="Senha atualizada")

    return {"status": "ok"}

@router.get("/users")
async def list_users(request: Request, db: Session = Depends(get_db)):
    current = get_user_from_request_token(request, db)
    if not current or not current.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito ao perfil Admin")

    qp = request.query_params
    search = (qp.get("search") or "").strip()
    sector = (qp.get("sector") or None)
    is_admin = qp.get("is_admin")
    is_active = qp.get("is_active")
    fmt = (qp.get("format") or "json").lower()

    q = db.query(User)
    if search:
        like = f"%{search}%"
        q = q.filter((User.username.ilike(like)) | (User.email.ilike(like)) | (User.full_name.ilike(like)))
    if sector:
        q = q.filter(User.sector == sector)
    if is_admin is not None:
        if is_admin in ("true", "1", "True"):
            q = q.filter(User.is_admin == True)
        elif is_admin in ("false", "0", "False"):
            q = q.filter(User.is_admin == False)
    if is_active is not None:
        if is_active in ("true", "1", "True"):
            q = q.filter(User.is_active == True)
        elif is_active in ("false", "0", "False"):
            q = q.filter(User.is_active == False)

    users = q.order_by(User.created_at.desc()).all()

    if fmt == "csv":
        import csv
        from io import StringIO
        sio = StringIO()
        writer = csv.writer(sio)
        writer.writerow(["id", "username", "email", "full_name", "sector", "company_code", "is_admin", "is_active", "created_at"]) 
        for u in users:
            writer.writerow([u.id, u.username, u.email or "", u.full_name or "", u.sector or "", u.company_code or "", int(bool(u.is_admin)), int(bool(u.is_active)), (u.created_at.isoformat() if u.created_at else "")])
        csv_data = sio.getvalue()
        return Response(content=csv_data, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=usuarios.csv"})

    return {
        "status": "ok",
        "total": len(users),
        "items": [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "full_name": u.full_name,
                "sector": u.sector,
                "company_code": u.company_code,  # novo
                "is_admin": u.is_admin,
                "is_active": u.is_active,
                "created_at": (u.created_at.isoformat() if u.created_at else None),
            } for u in users
        ]
    }

@router.put("/users/{user_id}")
async def update_user(user_id: int, request: Request, db: Session = Depends(get_db)):
    current = get_user_from_request_token(request, db)
    if not current or not current.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito ao perfil Admin")

    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")

    payload = await request.json()
    email = payload.get("email")
    full_name = payload.get("full_name")
    sector = payload.get("sector")
    company_code = normalize_company_code(payload.get("company_code"))  # novo
    is_active = payload.get("is_active")
    is_admin = payload.get("is_admin")

    before = {
        "email": user.email,
        "full_name": user.full_name,
        "sector": user.sector,
        "company_code": user.company_code,  # novo
        "is_active": user.is_active,
        "is_admin": user.is_admin,
    }

    if email is not None:
        user.email = email
    if full_name is not None:
        user.full_name = full_name
    if sector is not None:
        user.sector = sector
    if company_code is not None:
        user.company_code = company_code
    if is_active is not None:
        user.is_active = bool(is_active)
    if is_admin is not None:
        user.is_admin = bool(is_admin)

    db.add(user)
    db.commit()

    # Atualizar associação de perfil simples (Admin/Usuario)
    role_name = "Admin" if user.is_admin else "Usuario"
    role = db.query(Role).filter(Role.name == role_name).first()
    if not role:
        role = Role(name=role_name, description=f"Perfil {role_name}")
        db.add(role)
        db.commit()
        db.refresh(role)
    # garantir que exista uma associação para este perfil
    assoc = db.query(UserRole).filter(UserRole.user_id == user.id).first()
    if not assoc:
        db.add(UserRole(user_id=user.id, role_id=role.id))
    else:
        assoc.role_id = role.id
        db.add(assoc)
    db.commit()

    # Auditoria
    after = {
        "email": user.email,
        "full_name": user.full_name,
        "sector": user.sector,
        "company_code": user.company_code,  # novo
        "is_active": user.is_active,
        "is_admin": user.is_admin,
    }
    try:
        import json
        changes = json.dumps({"before": before, "after": after}, ensure_ascii=False)
    except Exception:
        changes = f"email:{before['email']}->{after['email']}; is_admin:{before['is_admin']}->{after['is_admin']}"
    log_audit(db, user_id=current.id, action="update_user", entity="users", entity_id=user.id, changes=changes)

    return {"status": "ok"}

@router.delete("/users/{user_id}")
async def delete_user(user_id: int, request: Request, db: Session = Depends(get_db)):
    current = get_user_from_request_token(request, db)
    if not current or not current.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito ao perfil Admin")

    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")

    db.delete(user)
    db.commit()

    # Auditoria
    log_audit(db, user_id=current.id, action="delete_user", entity="users", entity_id=user_id, changes="Usuário removido")

    return {"status": "ok"}

# Página: Gestão de Usuários
@router.get("/users-page")
async def admin_users_page(request: Request, db: Session = Depends(get_db)):
    user = get_user_from_request_token(request, db)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito ao perfil Admin")
    return templates.TemplateResponse("admin/users.html", {"request": request, "current_user": user})

# Página: Logs de Auditoria/Erros
@router.get("/logs-page")
async def admin_logs_page(request: Request, db: Session = Depends(get_db)):
    user = get_user_from_request_token(request, db)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito ao perfil Admin")
    return templates.TemplateResponse("admin/logs.html", {"request": request, "current_user": user})

# Página: Logs de Erros
@router.get("/errors-page")
async def admin_errors_page(request: Request, db: Session = Depends(get_db)):
    user = get_user_from_request_token(request, db)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito ao perfil Admin")
    return templates.TemplateResponse("admin/errors.html", {"request": request, "current_user": user})

@router.get("/error-logs")
async def list_error_logs(request: Request, db: Session = Depends(get_db)):
    current = get_user_from_request_token(request, db)
    if not current or not current.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito ao perfil Admin")
    qp = request.query_params
    module = (qp.get("module") or "").strip()
    error_type = (qp.get("error_type") or "").strip()
    status_filter = (qp.get("status") or "").strip()  # open|resolved|''
    start = qp.get("start_date")
    end = qp.get("end_date")
    search = (qp.get("search") or "").strip()
    fmt = (qp.get("format") or "json").lower()

    q = db.query(ErrorLog)
    if module:
        q = q.filter(ErrorLog.module.ilike(f"%{module}%"))
    if error_type:
        q = q.filter(ErrorLog.error_type.ilike(f"%{error_type}%"))
    if status_filter:
        q = q.filter(ErrorLog.status == status_filter)
    if search:
        like = f"%{search}%"
        q = q.filter((ErrorLog.message.ilike(like)) | (ErrorLog.stack.ilike(like)) | (ErrorLog.context.ilike(like)))
    # Datas
    from dateutil import parser
    try:
        if start:
            start_dt = parser.parse(start)
            q = q.filter(ErrorLog.created_at >= start_dt)
        if end:
            end_dt = parser.parse(end)
            q = q.filter(ErrorLog.created_at <= end_dt)
    except Exception:
        pass

    logs = q.order_by(ErrorLog.created_at.desc()).limit(1000).all()

    if fmt == "csv":
        import csv
        from io import StringIO
        sio = StringIO()
        writer = csv.writer(sio)
        writer.writerow(["ID","Data","Módulo","Tipo","Mensagem","Status"]) 
        for l in logs:
            writer.writerow([
                l.id,
                l.created_at.isoformat() if l.created_at else "",
                l.module or "",
                l.error_type or "",
                (l.message or "").replace("\n"," ")[:500],
                l.status or "open"
            ])
        return Response(content=sio.getvalue(), media_type="text/csv")

    return {
        "status": "ok",
        "items": [
            {
                "id": l.id,
                "created_at": l.created_at.isoformat() if l.created_at else None,
                "module": l.module,
                "error_type": l.error_type,
                "message": l.message,
                "stack": l.stack,
                "status": l.status,
            } for l in logs
        ],
        "total": len(logs),
    }

@router.post("/error-logs/{log_id}/status")
async def update_error_log_status(log_id: int, request: Request, db: Session = Depends(get_db)):
    current = get_user_from_request_token(request, db)
    if not current or not current.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito ao perfil Admin")
    payload = await request.json()
    new_status = (payload.get("status") or "").strip()
    if new_status not in ("open","resolved"):
        raise HTTPException(status_code=400, detail="Status inválido: use 'open' ou 'resolved'")
    log = db.query(ErrorLog).get(log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log não encontrado")
    log.status = new_status
    db.add(log)
    db.commit()
    return {"status":"ok","id":log.id,"new_status":log.status}

@router.get("/audit-logs")
async def list_audit_logs(request: Request, db: Session = Depends(get_db)):
    current = get_user_from_request_token(request, db)
    if not current or not current.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito ao perfil Admin")
    qp = request.query_params
    user_id = qp.get("user_id")
    action = (qp.get("action") or "").strip()
    entity = (qp.get("entity") or "").strip()
    start = qp.get("start_date")
    end = qp.get("end_date")
    fmt = (qp.get("format") or "json").lower()

    q = db.query(AuditLog)
    if user_id:
        try:
            q = q.filter(AuditLog.user_id == int(user_id))
        except Exception:
            pass
    if action:
        q = q.filter(AuditLog.action.ilike(f"%{action}%"))
    if entity:
        q = q.filter(AuditLog.entity.ilike(f"%{entity}%"))
    from datetime import datetime as dt
    from dateutil import parser
    try:
        if start:
            start_dt = parser.parse(start)
            q = q.filter(AuditLog.created_at >= start_dt)
        if end:
            end_dt = parser.parse(end)
            q = q.filter(AuditLog.created_at <= end_dt)
    except Exception:
        pass

    logs = q.order_by(AuditLog.created_at.desc()).limit(1000).all()

    if fmt == "csv":
        import csv
        from io import StringIO
        sio = StringIO()
        writer = csv.writer(sio)
        writer.writerow(["id", "user_id", "action", "entity", "entity_id", "changes", "created_at"]) 
        for l in logs:
            writer.writerow([l.id, l.user_id or "", l.action, l.entity or "", l.entity_id or "", (l.changes or "").replace("\n"," ").replace("\r"," "), l.created_at.isoformat()])
        csv_data = sio.getvalue()
        return Response(content=csv_data, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=audit_logs.csv"})

    return {
        "status": "ok",
        "total": len(logs),
        "items": [
            {
                "id": l.id,
                "user_id": l.user_id,
                "action": l.action,
                "entity": l.entity,
                "entity_id": l.entity_id,
                "changes": l.changes,
                "created_at": l.created_at.isoformat(),
            } for l in logs
        ]
    }

@router.get("/sectors")
async def list_sectors(request: Request, db: Session = Depends(get_db)):
    current = get_user_from_request_token(request, db)
    if not current or not current.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito ao perfil Admin")
    sectors = db.query(Sector).order_by(Sector.name.asc()).all()
    return {"status": "ok", "items": [{"id": s.id, "name": s.name, "description": s.description, "is_active": s.is_active} for s in sectors]}

@router.post("/sectors")
async def create_sector(request: Request, db: Session = Depends(get_db)):
    current = get_user_from_request_token(request, db)
    if not current or not current.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito ao perfil Admin")
    payload = await request.json()
    name = (payload.get("name") or "").strip()
    description = payload.get("description")
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nome do setor é obrigatório")
    existing = db.query(Sector).filter(Sector.name == name).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Setor já existe")
    sector = Sector(name=name, description=description)
    db.add(sector)
    db.commit()
    db.refresh(sector)
    return {"status": "ok", "sector": {"id": sector.id, "name": sector.name}}

def get_user_modules(user_id: int, db: Session):
    """Retorna a lista de nomes de módulos ativos e não expirados licenciados ao usuário."""
    try:
        from sqlalchemy import and_, or_
        now = datetime.utcnow()
        rows = (
            db.query(Module.name)
            .join(License, License.module_id == Module.id)
            .filter(
                License.user_id == user_id,
                License.is_active == True,
                Module.is_active == True,
                or_(License.expires_at == None, License.expires_at > now)
            )
            .all()
        )
        return [r[0] for r in rows]
    except Exception:
        return []

@router.get("/version")
async def api_version():
    """Retorna a versão atual do aplicativo"""
    return {"version": APP_VERSION}