
from datetime import datetime, timezone
from typing import Annotated
import os

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Request, status, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from database.database import obter_db
from models import User


load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY não configurada")

ALGORITHM = "HS256"

router = APIRouter(tags=["Admin"])
templates = Jinja2Templates(directory="templates")


def obter_admin_web(
    request: Request,
    db: Annotated[Session, Depends(obter_db)]
) -> User:
    token = request.cookies.get("session_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"}
        )

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        user_id = int(payload.get("sub", ""))

        expiracao = payload.get("exp")
        if expiracao is None or int(expiracao) <= int(
            datetime.now(timezone.utc).timestamp()
        ):
            raise JWTError("Token expirado")

    except (JWTError, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"}
        )

    usuario = db.get(User, user_id)

    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"}
        )

    if usuario.nivel != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso permitido somente a administradores."
        )


    if payload.get("session_version") != usuario.session_version:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"}
        )

    return usuario


@router.get("/usuarios")
def listar_usuarios(
    request: Request,
    admin: Annotated[User, Depends(obter_admin_web)],
    db: Annotated[Session, Depends(obter_db)],
    mensagem: str | None = None
):
    usuarios = db.scalars(
        select(User).order_by(User.id.desc())
    ).all()

    return templates.TemplateResponse(
        request=request,
        name="usuarios.html",
        context={
            "usuarios": usuarios,
            "admin": admin,
            "mensagem": mensagem
        }
    )


@router.post("/usuarios/{user_id}/aprovar")
def aprovar_usuario(
    user_id: int,
    admin: Annotated[User, Depends(obter_admin_web)],
    db: Annotated[Session, Depends(obter_db)]
):
    usuario = db.get(User, user_id)

    if usuario is None:
        raise HTTPException(
            status_code=404,
            detail="Usuário não encontrado."
        )

    if usuario.id == admin.id:
        raise HTTPException(
            status_code=400,
            detail="Não é necessário aprovar sua própria conta."
        )

    if usuario.nivel != "pendente":
        return RedirectResponse(
            url="/usuarios?mensagem=Este+usuário+não+está+pendente",
            status_code=303
        )

    usuario.nivel = "operacional"
    usuario.session_version += 1
    
    db.commit()

    return RedirectResponse(
        url="/usuarios?mensagem=Usuário+aprovado+com+sucesso",
        status_code=303
    )


@router.post("/usuarios/{user_id}/excluir")
def excluir_usuario(
    user_id: int,
    admin: Annotated[User, Depends(obter_admin_web)],
    db: Annotated[Session, Depends(obter_db)]
):
    usuario = db.get(User, user_id)

    if usuario is None:
        raise HTTPException(
            status_code=404,
            detail="Usuário não encontrado."
        )

    if usuario.id == admin.id:
        raise HTTPException(
            status_code=400,
            detail="Você não pode excluir sua própria conta."
        )

    if usuario.nivel != "pendente":
        raise HTTPException(
            status_code=400,
            detail="Só é possível excluir cadastros pendentes por esta tela."
        )

    db.delete(usuario)
    db.commit()

    return RedirectResponse(
        url="/usuarios?mensagem=Cadastro+pendente+excluído",
        status_code=303
    )




@router.post("/usuarios/{user_id}/nivel")
def alterar_nivel_usuario(
    user_id: int,
    nivel: Annotated[str, Form()],
    admin: Annotated[User, Depends(obter_admin_web)],
    db: Annotated[Session, Depends(obter_db)]
):
    niveis_permitidos = {"operacional", "admin"}

    if nivel not in niveis_permitidos:
        raise HTTPException(
            status_code=400,
            detail="Nível de acesso inválido."
        )

    usuario = db.get(User, user_id)

    if usuario is None:
        raise HTTPException(
            status_code=404,
            detail="Usuário não encontrado."
        )

    if usuario.id == admin.id:
        raise HTTPException(
            status_code=400,
            detail="Não é permitido alterar seu próprio nível."
        )

    usuario.nivel = nivel

    # Invalida as sessões anteriores após mudança de permissão.
    usuario.session_version += 1

    db.commit()

    return RedirectResponse(
        url="/usuarios?mensagem=Nível+alterado+com+sucesso",
        status_code=303
    )


@router.post("/usuarios/{user_id}/desconectar")
def desconectar_usuario(
    user_id: int,
    admin: Annotated[User, Depends(obter_admin_web)],
    db: Annotated[Session, Depends(obter_db)]
):
    usuario = db.get(User, user_id)

    if usuario is None:
        raise HTTPException(
            status_code=404,
            detail="Usuário não encontrado."
        )

    if usuario.id == admin.id:
        raise HTTPException(
            status_code=400,
            detail="Use a opção Sair para encerrar sua própria sessão."
        )

    usuario.session_version += 1
    db.commit()

    return RedirectResponse(
        url="/usuarios?mensagem=Sessões+do+usuário+revogadas",
        status_code=303
    )