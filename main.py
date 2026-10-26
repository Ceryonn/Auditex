
from fastapi import FastAPI, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import inspect, text

from rotas import auth, users, registro, admin, leitora, auditoria
from database.database import Base, engine, obter_db
from models import User
from rotas.auth import obter_usuario_logado_web


# ============================================================
# BANCO DE DADOS
# ============================================================

Base.metadata.create_all(bind=engine)


colunas_users = {
    coluna["name"]
    for coluna in inspect(engine).get_columns("users")
}

if "session_version" not in colunas_users:
    with engine.begin() as conexao:
        conexao.execute(
            text(
                "ALTER TABLE users "
                "ADD COLUMN session_version "
                "INTEGER NOT NULL DEFAULT 0"
            )
        )


# ============================================================
# APLICAÇÃO
# ============================================================

app = FastAPI(
    title="Auditex",
    version="1.0.0"
)

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)

app.include_router(auth.router)
app.include_router(auth.logout_router)
app.include_router(users.router)
app.include_router(registro.router)
app.include_router(admin.router)
app.include_router(leitora.router)
app.include_router(auditoria.router)


templates = Jinja2Templates(
    directory="templates"
)


# ============================================================
# DASHBOARD
# GET /
# ============================================================

@app.get("/")
async def homepage(
    request: Request,
    db: Session = Depends(obter_db)
):
    usuario_logado = obter_usuario_logado_web(
        request,
        db
    )

    if usuario_logado is None:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={
            "titulo": "Dashboard",
            "versao": "1.0.0",
            "usuario_logado": usuario_logado
        }
    )


# ============================================================
# TELA DE LOGIN
# GET /login
# ============================================================

@app.get("/login")
async def login_page(
    request: Request,
    db: Session = Depends(obter_db)
):
    usuario_logado = obter_usuario_logado_web(
        request,
        db
    )

    # Se já estiver autenticado, volta ao dashboard.
    if usuario_logado is not None:
        return RedirectResponse(
            url="/",
            status_code=303
        )

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "titulo": "Login",
            "versao": "1.0.0",
            "error": None,
            "email": "",
            "usuario_logado": None
        }
    )
