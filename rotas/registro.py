from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from sqlalchemy import select
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from database.database import obter_db
from models import User

from rotas.auditoria import registrar_evento_auditoria


router = APIRouter(tags=["Registro"])

templates = Jinja2Templates(directory="templates")

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


@router.get("/registro", response_class=HTMLResponse)
async def pagina_registro(request: Request):
    registrar_evento_auditoria(
        usuario=None,
        request=request,
        acao="ACESSAR_PAGINA_REGISTRO",
        entidade="usuarios",
        detalhes={
            "resultado": "sucesso",
            "metodo": "GET",
        },
    )

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
    request: Request,
    email: Annotated[str, Form()],
    senha: Annotated[str, Form()],
    confirmar_senha: Annotated[str, Form()],
    db: Annotated[Session, Depends(obter_db)]
):
    email = email.strip().lower()

    def registrar_tentativa(
        acao: str,
        resultado: str,
        motivo: str | None = None,
    ):
        detalhes = {
            "resultado": resultado,
            "metodo": "POST",
        }

        if motivo:
            detalhes["motivo"] = motivo

        # Não registra senhas nem hashes.
        registrar_evento_auditoria(
            usuario=None,
            request=request,
            acao=acao,
            entidade="usuarios",
            detalhes=detalhes,
        )

    def renderizar_erro(
        mensagem: str,
        motivo: str,
    ):
        registrar_tentativa(
            acao="TENTATIVA_REGISTRO_FALHOU",
            resultado="falha",
            motivo=motivo,
        )

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
            "Preencha todos os campos.",
            "campos_obrigatorios",
        )

    if senha != confirmar_senha:
        return renderizar_erro(
            "As senhas não coincidem.",
            "senhas_nao_coincidem",
        )

    if len(senha) < 8:
        return renderizar_erro(
            "A senha deve ter pelo menos 8 caracteres.",
            "senha_muito_curta",
        )

    if len(senha.encode("utf-8")) > 72:
        return renderizar_erro(
            "A senha não pode ultrapassar 72 bytes.",
            "senha_excede_limite",
        )

    usuario_existente = db.scalar(
        select(User).where(User.email == email)
    )

    if usuario_existente:
        return renderizar_erro(
            "Este e-mail já está cadastrado.",
            "email_ja_cadastrado",
        )

    novo_usuario = User(
        email=email,
        password_hash=pwd_context.hash(senha),
        nivel="pendente"
    )

    try:
        db.add(novo_usuario)
        db.commit()
        db.refresh(novo_usuario)

    except Exception:
        db.rollback()

        registrar_tentativa(
            acao="ERRO_REGISTRO_USUARIO",
            resultado="erro",
            motivo="falha_ao_salvar_cadastro",
        )

        return renderizar_erro(
            "Não foi possível concluir o cadastro. Tente novamente.",
            "falha_ao_salvar_cadastro",
        )

    registrar_evento_auditoria(
        usuario=None,
        request=request,
        acao="REGISTRO_USUARIO",
        entidade="usuarios",
        registro_id=novo_usuario.id,
        detalhes={
            "resultado": "sucesso",
            "email_cadastrado": email,
            "nivel_inicial": "pendente",
            "metodo": "POST",
        },
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