from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from sqlalchemy import select
from sqlalchemy.orm import Session 
from passlib.context import CryptContext
from database.database import obter_db
from models import User

router = APIRouter(tags=["Registro"])

templates = Jinja2Templates(directory="templates")

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


@router.get("/registro", response_class=HTMLResponse)
async def pagina_registro(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="register.html",
        context={
            "error": None,
            "email": ""
        }
    )


@router.post("/registro", response_class=HTMLResponse)
async def registrar_usuario(
    request:Request,
    email: Annotated[str, Form()],
    senha: Annotated[str, Form()],
    confirmar_senha: Annotated[str, Form()],
    db: Annotated[Session, Depends(obter_db)]
):
    email = email.strip().lower()

    def renderizar_erro(mensagem: str):
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={
                "error": mensagem,
                "email": email
            },
            status_code=status.HTTP_400_BAD_REQUEST
        )

    if not email or not senha or not confirmar_senha:
        return renderizar_erro(
            "Preencha todos os campos."
        )

    if senha != confirmar_senha:
        return renderizar_erro(
            "As senhas não coincidem."
        )

    if len(senha) < 8:
        return renderizar_erro(
            "A senha deve ter pelo menos 8 caracteres."
        )

    if len(senha.encode("utf-8")) > 72:
        return renderizar_erro(
            "A senha não pode ultrapassar 72 bytes."
        )

    usuario_existente = db.scalar(
        select(User).where(User.email == email)
    )

    if usuario_existente:
        return renderizar_erro(
            "Este e-mail já está cadastrado."
        )

    novo_usuario = User(
        email=email,
        password_hash=pwd_context.hash(senha),
        nivel="pendente"
    )

    try:
        db.add(novo_usuario)
        db.commit()
    except Exception:
        db.rollback()
        return renderizar_erro(
            "Não foi possível concluir o cadastro. Tente novamente."
        )

    return templates.TemplateResponse(
        request=request,
        name="register.html",
        context={
            "error": None,
            "email": "",
            "success": (
                "Cadastro realizado com sucesso! "
                "Aguarde a aprovação de um administrador "
                "para acessar o sistema."
            )
        },
        status_code=status.HTTP_201_CREATED
    )