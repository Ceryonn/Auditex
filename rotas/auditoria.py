import io
import logging
import os
import re
import sqlite3
import zipfile

import boto3

from botocore.exceptions import BotoCoreError, ClientError
from dotenv import load_dotenv

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
)
from fastapi.responses import StreamingResponse
from fastapi.templating import Jinja2Templates

from sqlalchemy.orm import Session

from database.database import obter_db
from database.clientes import obter_conexao_clientes
from rotas.auth import obter_usuario_logado_web


load_dotenv()

router = APIRouter(tags=["Auditoria"])
templates = Jinja2Templates(directory="templates")

logger = logging.getLogger(__name__)

AWS_REGION = os.getenv("AWS_REGION")
AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")






def exigir_usuario_logado(
    request: Request,
    db: Session = Depends(obter_db),
):
    usuario = obter_usuario_logado_web(request, db)

    if usuario is None:
        raise HTTPException(
            status_code=401,
            detail="Sessão inválida ou expirada. Faça login novamente.",
        )

    return usuario


@router.get("/auditorias")
async def pagina_auditoria(
    request: Request,
    usuario=Depends(exigir_usuario_logado),
):
    return templates.TemplateResponse(
        request=request,
        name="auditoria.html",
        context={
            "titulo": "Central de Auditoria",
            "usuario_logado": usuario,
        },
    )



@router.get("/auditorias/operacoes")
def listar_operacoes(
    usuario=Depends(exigir_usuario_logado),
):
    con = obter_conexao_clientes()

    try:
        cursor = con.cursor()

        cursor.execute("""
            SELECT DISTINCT TRIM(operacao) AS operacao
            FROM clientes
            WHERE operacao IS NOT NULL
              AND TRIM(operacao) <> ''
            ORDER BY operacao COLLATE NOCASE
        """)

        operacoes = [
            row["operacao"]
            for row in cursor.fetchall()
        ]

        return {"data": operacoes}

    finally:
        con.close()



@router.get("/auditorias/registros")
def listar_registros(
    busca: str = Query(default="", max_length=200),
    operacao: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    request: Request = None,
    usuario=Depends(exigir_usuario_logado),
):
    con = obter_conexao_clientes()

    try:
        cursor = con.cursor()

        condicoes = []
        parametros = []

        # Pesquisa parcial por CPF/documento, CCB ou nome.
        if busca.strip():
            termo = busca.strip()

            condicoes.append("""
                (
                    documento LIKE ?
                    OR ccb LIKE ?
                    OR nome LIKE ?
                )
            """)

            like = f"%{termo}%"
            parametros.extend([like, like, like])

        # Filtro exato de operação.
        if operacao and operacao.strip():
            condicoes.append("TRIM(operacao) = ?")
            parametros.append(operacao.strip())

        where = ""

        if condicoes:
            where = "WHERE " + " AND ".join(condicoes)

        cursor.execute(
            f"""
            SELECT COUNT(*)
            FROM clientes
            {where}
            """,
            parametros,
        )

        total = cursor.fetchone()[0]

        cursor.execute(
            f"""
            SELECT
                id,
                operacao,
                ccb,
                documento,
                nome,
                lastro,
                auditado,
                "status final" AS status_final,
                motivo
            FROM clientes
            {where}
            ORDER BY id
            LIMIT ? OFFSET ?
            """,
            parametros + [limit, offset],
        )

        registros = [
            dict(row)
            for row in cursor.fetchall()
        ]

        logger.info(
            "usuario=%s | AUDITORIA | busca=%s | operacao=%s | "
            "total=%s | offset=%s | limit=%s",
            getattr(usuario, "email", "desconhecido"),
            busca,
            operacao,
            total,
            offset,
            limit,
        )

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "data": registros,
        }

    finally:
        con.close()



def criar_cliente_s3():
    """Cria o cliente S3 utilizando as credenciais configuradas."""

    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")

    if not AWS_REGION or not AWS_BUCKET_NAME:
        raise HTTPException(
            status_code=500,
            detail="Configuração do S3 incompleta.",
        )

    if access_key and secret_key:
        return boto3.client(
            "s3",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=AWS_REGION,
        )

    # Permite utilizar credenciais de IAM role ou perfil AWS.
    return boto3.client(
        "s3",
        region_name=AWS_REGION,
    )


def obter_cliente_por_id(cliente_id: int):
    """Consulta o cliente usando a conexão oficial de clientes.db."""

    con = obter_conexao_clientes()

    try:
        cursor = con.cursor()

        cursor.execute(
            """
            SELECT id, ccb, lastro
            FROM clientes
            WHERE id = ?
            """,
            (cliente_id,),
        )

        registro = cursor.fetchone()

        return dict(registro) if registro else None

    except sqlite3.Error:
        logger.exception(
            "Erro ao consultar cliente: id=%s",
            cliente_id,
        )

        raise HTTPException(
            status_code=500,
            detail="Erro ao consultar o cadastro do cliente.",
        )

    finally:
        con.close()



@router.get("/auditorias/download-lastro/{id}")
async def baixar_lastro(
    id: int,
    request: Request,
    db: Session = Depends(obter_db),
):
    usuario = obter_usuario_logado_web(request, db)

    if usuario is None:
        raise HTTPException(
            status_code=401,
            detail="Sessão inválida ou expirada. Faça login novamente.",
        )

    # Mantém a restrição de acesso do projeto anterior.
    if getattr(usuario, "nivel", None) not in {
        "operacional",
        "admin",
    }:
        raise HTTPException(
            status_code=403,
            detail="Você não tem permissão para baixar o lastro.",
        )

    cliente = obter_cliente_por_id(id)

    if cliente is None:
        raise HTTPException(
            status_code=404,
            detail="Cliente não encontrado.",
        )

    prefixo = (cliente.get("lastro") or "").strip()
    ccb = str(cliente.get("ccb") or id).strip()

    if not prefixo:
        raise HTTPException(
            status_code=404,
            detail="Este cliente não possui caminho de lastro cadastrado.",
        )

    # Considera o lastro como uma pasta/prefixo do bucket.
    prefixo = prefixo.strip("/") + "/"

    s3 = criar_cliente_s3()
    zip_buffer = io.BytesIO()
    quantidade_arquivos = 0

    try:
        paginator = s3.get_paginator("list_objects_v2")

        with zipfile.ZipFile(
            zip_buffer,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
        ) as zip_file:

            for pagina in paginator.paginate(
                Bucket=AWS_BUCKET_NAME,
                Prefix=prefixo,
            ):
                for obj in pagina.get("Contents", []):
                    chave = obj["Key"]

                    # Ignora entradas que representam pastas.
                    if chave.endswith("/"):
                        continue

                    nome_arquivo = chave[len(prefixo):].lstrip("/")

                    if not nome_arquivo:
                        continue

                    # Evita caminhos absolutos e travessia de diretórios
                    # dentro do arquivo ZIP.
                    partes = nome_arquivo.replace("\\", "/").split("/")

                    if (
                        nome_arquivo.startswith("/")
                        or any(parte == ".." for parte in partes)
                    ):
                        logger.warning(
                            "Objeto ignorado por caminho inválido: %s",
                            chave,
                        )
                        continue

                    arquivo = s3.get_object(
                        Bucket=AWS_BUCKET_NAME,
                        Key=chave,
                    )

                    try:
                        with arquivo["Body"] as body:
                            zip_file.writestr(
                                nome_arquivo,
                                body.read(),
                            )
                    finally:
                        arquivo["Body"].close()

                    quantidade_arquivos += 1

    except (ClientError, BotoCoreError):
        logger.exception(
            "Erro ao baixar lastro do S3: id=%s",
            id,
        )

        raise HTTPException(
            status_code=502,
            detail="Não foi possível obter os arquivos do lastro no S3.",
        )

    if quantidade_arquivos == 0:
        raise HTTPException(
            status_code=404,
            detail="Nenhum arquivo encontrado para este lastro.",
        )

    zip_buffer.seek(0)

    # Evita caracteres problemáticos no nome do download.
    ccb_segura = re.sub(r"[^A-Za-z0-9_-]", "_", ccb)[:100]
    nome_zip = f"lastro_{ccb_segura or id}.zip"

    logger.info(
        "usuario=%s | DOWNLOAD_LASTRO | id_cliente=%s | arquivos=%s",
        getattr(usuario, "email", "desconhecido"),
        id,
        quantidade_arquivos,
    )

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{nome_zip}"'
            ),
            "Cache-Control": "no-store",
        },
    )
