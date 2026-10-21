import os

from datetime import datetime, timedelta, timezone
from typing import Annotated

from dotenv import load_dotenv

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Form,
    status
)

from fastapi.responses import (
    RedirectResponse
)

from fastapi.templating import Jinja2Templates

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from jose import jwt, JWTError

from passlib.context import CryptContext

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.database import obter_db
from models import User


# ============================================================
# CONFIGURAÇÃO
# ============================================================

load_dotenv()


SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY não configurada"
    )


ALGORITHM = "HS256"

TOKEN_EXPIRE_MINUTES = 30


# ============================================================
# SENHAS
# ============================================================

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


# ============================================================
# TEMPLATES
# ============================================================

templates = Jinja2Templates(
    directory="templates"
)


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/auth",
    tags=["Auth"]
)


# ============================================================
# BEARER
# ============================================================

security = HTTPBearer()


# ============================================================
# LOGIN API
#
# POST /auth/login
#
# Usado para API / aplicações externas.
# ============================================================

@router.post("/login")
def login_api(
    dados: dict,
    db: Annotated[
        Session,
        Depends(obter_db)
    ]
):

    email = dados.get("email")
    senha = dados.get("senha")


    if not email or not senha:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email e senha são obrigatórios"
        )


    usuario = db.scalar(
        select(User).where(
            User.email == email
        )
    )


    if not usuario:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha inválidos"
        )


    if not pwd_context.verify(
        senha,
        usuario.password_hash
    ):

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha inválidos"
        )


    if usuario.nivel == "pendente":

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário aguardando aprovação"
        )


    payload = {
        "sub": str(usuario.id),
        "email": usuario.email,
        "nivel": usuario.nivel,
        "session_version": usuario.session_version,
        "exp": (
            datetime.now(timezone.utc)
            + timedelta(
                minutes=TOKEN_EXPIRE_MINUTES
            )
        )
    }


    token = jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


    return {
        "access_token": token,
        "token_type": "bearer"
    }


# ============================================================
# LOGIN WEB
#
# POST /auth/login-form
#
# Usado pelo formulário HTML.
# ============================================================

@router.post("/login-form")
async def login_form(
    request: Request,
    email: str = Form(...),
    senha: str = Form(...),
    db: Session = Depends(obter_db)
):

    usuario = db.scalar(
        select(User).where(
            User.email == email
        )
    )


    # --------------------------------------------------------
    # USUÁRIO NÃO ENCONTRADO
    # --------------------------------------------------------

    if not usuario:

        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "error": "Email ou senha inválidos",
                "email": email
            },
            status_code=status.HTTP_401_UNAUTHORIZED
        )


    # --------------------------------------------------------
    # SENHA INCORRETA
    # --------------------------------------------------------

    if not pwd_context.verify(
        senha,
        usuario.password_hash
    ):

        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "error": "Email ou senha inválidos",
                "email": email
            },
            status_code=status.HTTP_401_UNAUTHORIZED
        )


    # --------------------------------------------------------
    # USUÁRIO PENDENTE
    # --------------------------------------------------------

    if usuario.nivel == "pendente":

        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "error": "Usuário aguardando aprovação",
                "email": email
            },
            status_code=status.HTTP_403_FORBIDDEN
        )


    # --------------------------------------------------------
    # CRIA TOKEN
    # --------------------------------------------------------


    payload = {
        "sub": str(usuario.id),
        "email": usuario.email,
        "nivel": usuario.nivel,
        "session_version": usuario.session_version,
        "exp": (
            datetime.now(timezone.utc)
            + timedelta(
                minutes=TOKEN_EXPIRE_MINUTES
            )
        )
    }


    token = jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


    # --------------------------------------------------------
    # REDIRECIONAMENTO
    # --------------------------------------------------------

    response = RedirectResponse(
        url="/",
        status_code=status.HTTP_303_SEE_OTHER
    )

    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        max_age=TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=False,
        path="/"
    )

    response.set_cookie(
        key="nivel",
        value=usuario.nivel,
        httponly=True,
        max_age=TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=False,
        path="/"
    )

    return response

# ============================================================
# USUÁRIO ATUAL - API
#
# Utilizado quando o cliente envia:
#
# Authorization: Bearer TOKEN
# ============================================================

async def obter_usuario_atual(
    credentials: Annotated[
        HTTPAuthorizationCredentials,
        Depends(security)
    ],
    db: Annotated[
        Session,
        Depends(obter_db)
    ]
):

    token = credentials.credentials


    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )


        user_id = payload.get("sub")


        if user_id is None:

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido"
            )


    except JWTError:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado"
        )


    try:

        user_id = int(user_id)

    except (TypeError, ValueError):

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido"
        )


    usuario = db.get(
        User,
        user_id
    )


    if usuario is None:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado"
        )


    if payload.get("session_version") != usuario.session_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão encerrada. Faça login novamente."
        )

    return usuario





def obter_usuario_logado_web(
    request: Request,
    db: Session
):
    token = request.cookies.get("session_token")

    if not token:
        return None

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        user_id = int(payload.get("sub"))

    except (JWTError, TypeError, ValueError):
        return None

    usuario = db.get(User, user_id)

    if usuario is None:
        return None

    if usuario.nivel == "pendente":
        return None

    if payload.get("session_version") != usuario.session_version:
        return None

    return usuario







logout_router = APIRouter(tags=["Auth"])


@logout_router.get("/logout")
def logout_web(
    request: Request,
    db: Session = Depends(obter_db)
):
    token = request.cookies.get("session_token")

    if token:
        try:
            payload = jwt.decode(
                token,
                SECRET_KEY,
                algorithms=[ALGORITHM]
            )

            user_id = int(payload.get("sub", ""))
            usuario = db.get(User, user_id)

            if (
                usuario is not None
                and payload.get("session_version")
                == usuario.session_version
            ):
                usuario.session_version += 1
                db.commit()

        except (JWTError, TypeError, ValueError):
            pass

    response = RedirectResponse(
        url="/login",
        status_code=status.HTTP_303_SEE_OTHER
    )

    response.delete_cookie(
        key="session_token",
        path="/",
        httponly=True,
        samesite="lax",
        secure=False
    )

    response.delete_cookie(
        key="nivel",
        path="/",
        httponly=True,
        samesite="lax",
        secure=False
    )

    return response