import json
from datetime import datetime, timezone
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
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from sqlalchemy.orm import Session

from database.database import obter_db
from database.clientes import obter_conexao_clientes
from rotas.auth import obter_usuario_logado_web


load_dotenv()

router = APIRouter(tags=["Auditoria"])
templates = Jinja2Templates(directory="templates")

logger = logging.getLogger(__name__)


def agora_utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")



def garantir_schema_auditoria(con):
    cursor = con.cursor()

    cursor.execute("PRAGMA table_info(clientes)")
    colunas = {
        row["name"]
        for row in cursor.fetchall()
    }

    novas_colunas = {
        "auditoria_modificada_em": "TEXT",
        "cpf_regular": "TEXT",
        "financeiro_ok": "TEXT",
        "documentos_pessoais_ok": "TEXT",
        "pendencia_documental": "TEXT",
    }

    for nome, tipo in novas_colunas.items():
        if nome not in colunas:
            cursor.execute(
                f'ALTER TABLE clientes ADD COLUMN "{nome}" {tipo}'
            )
            colunas.add(nome)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs_sistema (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_hora TEXT NOT NULL,
            email TEXT,
            ip TEXT,
            acao TEXT NOT NULL,
            entidade TEXT,
            registro_id TEXT,
            detalhes TEXT
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_logs_sistema_data_hora
        ON logs_sistema(data_hora)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_logs_sistema_email
        ON logs_sistema(email)
    """)

    con.commit()



def obter_ip_requisicao(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host

    return "desconhecido"


def registrar_log(
    con,
    *,
    usuario,
    request: Request,
    acao: str,
    entidade: str,
    registro_id,
    detalhes: dict,
):
    con.execute(
        """
        INSERT INTO logs_sistema (
            data_hora,
            email,
            ip,
            acao,
            entidade,
            registro_id,
            detalhes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            agora_utc(),
            getattr(usuario, "email", None),
            obter_ip_requisicao(request),
            acao,
            entidade,
            str(registro_id) if registro_id is not None else None,
            json.dumps(
                detalhes,
                ensure_ascii=False,
            ),
        ),
    )


def registrar_evento_auditoria(
    *,
    usuario,
    request: Request,
    acao: str,
    entidade: str | None = None,
    registro_id=None,
    detalhes: dict | None = None,
):
    con = obter_conexao_clientes()

    try:
        garantir_schema_auditoria(con)

        registrar_log(
            con,
            usuario=usuario,
            request=request,
            acao=acao,
            entidade=entidade,
            registro_id=registro_id,
            detalhes=detalhes or {},
        )

        con.commit()

    except sqlite3.Error:
        con.rollback()

        logger.exception(
            "Falha ao registrar evento de auditoria: acao=%s",
            acao,
        )

    finally:
        con.close()


AWS_REGION = os.getenv("AWS_REGION")
AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")


def exigir_usuario_logado(
    request: Request,
    db: Session = Depends(obter_db),
):
    usuario = obter_usuario_logado_web(request, db)

    if usuario is None:
        registrar_evento_auditoria(
            usuario=None,
            request=request,
            acao="FALHA_AUTENTICACAO",
            entidade="sessao",
            detalhes={
                "resultado": "negado",
                "motivo": "sessao_invalida_ou_expirada",
                "recurso": request.url.path,
                "metodo": request.method,
            },
        )

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
    registrar_evento_auditoria(
        usuario=usuario,
        request=request,
        acao="ACESSAR_AUDITORIA",
        entidade="auditoria",
        detalhes={
            "resultado": "sucesso",
            "recurso": "/auditorias",
            "metodo": "GET",
        },
    )

    return templates.TemplateResponse(
        request=request,
        name="auditoria.html",
        context={
            "titulo": "Central de Auditoria",
            "usuario_logado": usuario,
        },
    )



@router.get("/logs", response_class=HTMLResponse)
async def pagina_log(
    request: Request,
    usuario=Depends(exigir_usuario_logado),
):
    if getattr(usuario, "nivel", None) != "admin":
        raise HTTPException(
            status_code=403,
            detail="Você não tem permissão para acessar os logs.",
        )

    # Registra o acesso à página.
    registrar_evento_auditoria(
        usuario=usuario,
        request=request,
        acao="ACESSAR_LOGS",
        entidade="logs_sistema",
        detalhes={
            "pagina": "/logs",
            "metodo": "GET",
        },
    )

    params = request.query_params

    filtros = {
        "busca": params.get("busca", "").strip(),
        "acao": params.get("acao", "").strip(),
        "resultado": params.get("resultado", "").strip(),
        "data_inicio": params.get("data_inicio", "").strip(),
        "data_fim": params.get("data_fim", "").strip(),
        "email": params.get("email", "").strip(),
        "entidade": params.get("entidade", "").strip(),
    }

    try:
        pagina = max(1, int(params.get("pagina", "1")))
        limit = int(params.get("limit", "50"))
    except (ValueError, TypeError):
        pagina = 1
        limit = 50

    if limit not in (25, 50, 100, 200):
        limit = 50

    # Valida as datas para evitar filtros malformados.
    for campo in ("data_inicio", "data_fim"):
        valor = filtros[campo]

        if valor:
            try:
                datetime.strptime(valor, "%Y-%m-%d")
            except ValueError:
                filtros[campo] = ""

    con = obter_conexao_clientes()

    try:
        garantir_schema_auditoria(con)

        where = []
        valores = []

        if filtros["busca"]:
            termo = f"%{filtros['busca']}%"
            where.append("""
                (
                    email LIKE ?
                    OR acao LIKE ?
                    OR entidade LIKE ?
                    OR registro_id LIKE ?
                    OR detalhes LIKE ?
                    OR ip LIKE ?
                )
            """)
            valores.extend([termo] * 6)

        if filtros["acao"]:
            where.append("acao = ?")
            valores.append(filtros["acao"])

        if filtros["email"]:
            where.append("email LIKE ?")
            valores.append(f"%{filtros['email']}%")

        if filtros["entidade"]:
            where.append("entidade = ?")
            valores.append(filtros["entidade"])

        if filtros["resultado"]:
            where.append("""
                COALESCE(
                    json_extract(detalhes, '$.resultado'),
                    ''
                ) = ?
            """)
            valores.append(filtros["resultado"])

        if filtros["data_inicio"]:
            where.append("substr(data_hora, 1, 10) >= ?")
            valores.append(filtros["data_inicio"])

        if filtros["data_fim"]:
            where.append("substr(data_hora, 1, 10) <= ?")
            valores.append(filtros["data_fim"])

        clausula_where = (
            "WHERE " + " AND ".join(where)
            if where else ""
        )

        cursor = con.cursor()

        # Total de eventos que correspondem aos filtros.
        cursor.execute(
            f"""
            SELECT COUNT(*)
            FROM logs_sistema
            {clausula_where}
            """,
            valores,
        )
        total = cursor.fetchone()[0]

        # Indicadores calculados sobre o conjunto filtrado.
        cursor.execute(
            f"""
            SELECT
                SUM(
                    CASE
                        WHEN json_extract(
                            detalhes, '$.resultado'
                        ) = 'sucesso'
                        THEN 1 ELSE 0
                    END
                ) AS sucessos,

                SUM(
                    CASE
                        WHEN json_extract(
                            detalhes, '$.resultado'
                        ) IN (
                            'falha', 'erro', 'negado',
                            'bloqueado'
                        )
                        THEN 1 ELSE 0
                    END
                ) AS falhas,

                COUNT(DISTINCT email) AS usuarios_ativos
            FROM logs_sistema
            {clausula_where}
            """,
            valores,
        )

        indicadores = cursor.fetchone()

        sucessos = indicadores["sucessos"] or 0
        falhas = indicadores["falhas"] or 0
        usuarios_ativos = indicadores["usuarios_ativos"] or 0

        # Opções dos filtros.
        cursor.execute("""
            SELECT DISTINCT acao
            FROM logs_sistema
            WHERE acao IS NOT NULL AND acao <> ''
            ORDER BY acao
        """)
        acoes = [row["acao"] for row in cursor.fetchall()]

        cursor.execute("""
            SELECT DISTINCT entidade
            FROM logs_sistema
            WHERE entidade IS NOT NULL AND entidade <> ''
            ORDER BY entidade
        """)
        entidades = [
            row["entidade"] for row in cursor.fetchall()
        ]

        # Paginação.
        paginas = max(1, (total + limit - 1) // limit)
        pagina = min(pagina, paginas)
        offset = (pagina - 1) * limit

        cursor.execute(
            f"""
            SELECT
                id,
                data_hora,
                email,
                ip,
                acao,
                entidade,
                registro_id,
                detalhes
            FROM logs_sistema
            {clausula_where}
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            """,
            valores + [limit, offset],
        )

        logs = []

        for row in cursor.fetchall():
            log = dict(row)

            try:
                detalhes = json.loads(log.get("detalhes") or "{}")
                if not isinstance(detalhes, dict):
                    detalhes = {}
            except (ValueError, TypeError):
                detalhes = {}

            # O template utiliza log.resultado para colorir o evento.
            log["resultado"] = detalhes.get("resultado", "")

            logs.append(log)

        return templates.TemplateResponse(
            request=request,
            name="log.html",
            context={
                "titulo": "Logs do Sistema",
                "usuario_logado": usuario,
                "messages": [],
                "filtros": filtros,
                "logs": logs,
                "total": total,
                "sucessos": sucessos,
                "falhas": falhas,
                "usuarios_ativos": usuarios_ativos,
                "acoes": acoes,
                "entidades": entidades,
                "pagina": pagina,
                "paginas": paginas,
                "limit": limit,
            },
        )

    except sqlite3.Error:
        logger.exception("Erro ao consultar a página de logs.")

        raise HTTPException(
            status_code=500,
            detail="Não foi possível carregar os logs do sistema.",
        )

    finally:
        con.close()



@router.get("/auditorias/operacoes")
def listar_operacoes(
    request: Request,
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

    finally:
        con.close()

    # Registrar o evento depois de liberar a conexão
    # utilizada pela consulta.
    registrar_evento_auditoria(
        usuario=usuario,
        request=request,
        acao="LISTAR_OPERACOES",
        entidade="clientes",
        detalhes={
            "resultado": "sucesso",
            "quantidade": len(operacoes),
        },
    )

    return {"data": operacoes}






import time
from threading import Lock

# Cache em memória dos indicadores globais.
# Não altera o banco de dados.
_cache_resumo_global = {
    "expira_em": 0.0,
    "dados": None,
}
_cache_resumo_lock = Lock()


def obter_resumo_global(con):
    agora = time.monotonic()

    with _cache_resumo_lock:
        if (
            _cache_resumo_global["dados"] is not None
            and agora < _cache_resumo_global["expira_em"]
        ):
            return _cache_resumo_global["dados"]

    cursor = con.cursor()

    cursor.execute("""
        SELECT
            COUNT(*) AS total,
            COALESCE(SUM(
                CASE WHEN TRIM(COALESCE(auditado, '')) = 'Concluído'
                THEN 1 ELSE 0 END
            ), 0) AS auditados,
            COALESCE(SUM(
                CASE WHEN TRIM(COALESCE(auditado, ''))
                    IN ('Pendente', 'Em análise')
                THEN 1 ELSE 0 END
            ), 0) AS pendentes
        FROM clientes
    """)

    row = cursor.fetchone()

    total = row["total"] or 0
    auditados = row["auditados"] or 0
    pendentes = row["pendentes"] or 0

    dados = {
        "total": total,
        "auditados": auditados,
        "pendentes": pendentes,
        "percentual_auditado": (
            round(auditados * 100 / total, 2) if total else 0
        ),
    }

    with _cache_resumo_lock:
        _cache_resumo_global["dados"] = dados
        _cache_resumo_global["expira_em"] = time.monotonic() + 60

    return dados


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
        garantir_schema_auditoria(con)

        condicoes = []
        parametros = []

        termo = busca.strip()

        if termo:
            condicoes.append("""
                (
                    documento LIKE ?
                    OR ccb LIKE ?
                    OR nome LIKE ?
                )
            """)
            like = f"%{termo}%"
            parametros.extend([like, like, like])

        filtro_operacao = operacao.strip() if operacao else ""

        if filtro_operacao:
            condicoes.append("TRIM(operacao) = ?")
            parametros.append(filtro_operacao)

        where = (
            "WHERE " + " AND ".join(condicoes)
            if condicoes else ""
        )

        cursor = con.cursor()

        # Um único resumo atende tanto à contagem quanto
        # aos indicadores da consulta filtrada.
        cursor.execute(
            f"""
            SELECT
                COUNT(*) AS total,
                COALESCE(SUM(
                    CASE
                        WHEN TRIM(COALESCE(auditado, '')) = 'Concluído'
                        THEN 1 ELSE 0
                    END
                ), 0) AS auditados,
                COALESCE(SUM(
                    CASE
                        WHEN TRIM(COALESCE(auditado, ''))
                            IN ('Pendente', 'Em análise')
                        THEN 1 ELSE 0
                    END
                ), 0) AS pendentes
            FROM clientes
            {where}
            """,
            parametros,
        )

        resumo = cursor.fetchone()

        total = resumo["total"] or 0
        auditados = resumo["auditados"] or 0
        pendentes = resumo["pendentes"] or 0

        resumo_consulta = {
            "total": total,
            "auditados": auditados,
            "pendentes": pendentes,
            "percentual_auditado": (
                round(auditados * 100 / total, 2) if total else 0
            ),
        }

        # Sem filtros, o resumo global também é o da consulta.
        if not termo and not filtro_operacao:
            resumo_global = resumo_consulta
            with _cache_resumo_lock:
                _cache_resumo_global["dados"] = resumo_global
                _cache_resumo_global["expira_em"] = (
                    time.monotonic() + 60
                )
        else:
            resumo_global = obter_resumo_global(con)

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
                motivo,
                auditoria_modificada_em,
                cpf_regular,
                financeiro_ok,
                documentos_pessoais_ok,
                pendencia_documental
            FROM clientes
            {where}
            ORDER BY id
            LIMIT ? OFFSET ?
            """,
            parametros + [limit, offset],
        )

        registros = [dict(row) for row in cursor.fetchall()]

    finally:
        con.close()

    registrar_evento_auditoria(
        usuario=usuario,
        request=request,
        acao="CONSULTAR_REGISTROS",
        entidade="clientes",
        detalhes={
            "resultado": "sucesso",
            "busca_realizada": bool(termo),
            "filtro_operacao": bool(filtro_operacao),
            "operacao": filtro_operacao or None,
            "total_encontrado": total,
            "limit": limit,
            "offset": offset,
        },
    )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": registros,
        "resumo_global": resumo_global,
        "resumo_consulta": resumo_consulta,
    }




@router.put("/auditorias/registros/{id}")
async def atualizar_auditoria(
    id: int,
    request: Request,
    usuario=Depends(exigir_usuario_logado),
):
    if getattr(usuario, "nivel", None) not in {"auditor", "admin"}:
        registrar_evento_auditoria(
            usuario=usuario,
            request=request,
            acao="ACESSO_NEGADO",
            entidade="clientes",
            registro_id=id,
            detalhes={
                "resultado": "negado",
                "motivo": "permissao_insuficiente",
                "recurso": "atualizar_auditoria",
            },
        )

        raise HTTPException(
            status_code=403,
            detail="Você não tem permissão para editar auditorias.",
        )

    try:
        dados = await request.json()
    except (ValueError, TypeError):
        registrar_evento_auditoria(
            usuario=usuario,
            request=request,
            acao="FALHA_VALIDACAO",
            entidade="clientes",
            registro_id=id,
            detalhes={
                "resultado": "falha",
                "motivo": "corpo_requisicao_invalido",
            },
        )

        raise HTTPException(
            status_code=400,
            detail="Corpo da requisição inválido.",
        )

    if not isinstance(dados, dict):
        registrar_evento_auditoria(
            usuario=usuario,
            request=request,
            acao="FALHA_VALIDACAO",
            entidade="clientes",
            registro_id=id,
            detalhes={
                "resultado": "falha",
                "motivo": "json_nao_e_objeto",
            },
        )

        raise HTTPException(
            status_code=400,
            detail="Os dados enviados devem ser um objeto JSON.",
        )

    situacoes_permitidas = {
        "Pendente",
        "Em análise",
        "Concluído",
    }

    # Mantém os status finais já utilizados pelo seu sistema.
    resultados_permitidos = {
        "Aprovado",
        "Reprovado",
        "Pendente",
    }

    campos_sim_nao = (
        "cpf_regular",
        "financeiro_ok",
        "documentos_pessoais_ok",
    )

    # Exige os campos antigos, como antes.
    auditado = dados.get("auditado")
    status_final = dados.get("status_final")
    motivo = dados.get("motivo", "")

    if auditado not in situacoes_permitidas:
        raise HTTPException(
            status_code=422,
            detail="Selecione uma situação válida para a auditoria.",
        )

    if status_final not in resultados_permitidos:
        raise HTTPException(
            status_code=422,
            detail=(
                "O status final deve ser Aprovado, "
                "Reprovado ou Pendente."
            ),
        )

    if not isinstance(motivo, str):
        raise HTTPException(
            status_code=422,
            detail="O motivo deve ser um texto.",
        )

    motivo = motivo.strip()

    if len(motivo) > 5000:
        raise HTTPException(
            status_code=422,
            detail="O motivo deve ter no máximo 5.000 caracteres.",
        )

    if status_final != "Aprovado" and not motivo:
        raise HTTPException(
            status_code=422,
            detail="Informe o motivo para este resultado.",
        )

    # Os campos novos são opcionais na requisição para manter
    # compatibilidade com a tela atual.
    for campo in campos_sim_nao:
        if campo in dados:
            valor = dados[campo]

            if valor not in ("Sim", "Não", None):
                raise HTTPException(
                    status_code=422,
                    detail=f"O campo {campo} deve ser Sim ou Não.",
                )

    if "pendencia_documental" in dados:
        pendencia_documental = dados["pendencia_documental"]

        if pendencia_documental is not None:
            if not isinstance(pendencia_documental, str):
                raise HTTPException(
                    status_code=422,
                    detail="A pendência documental deve ser um texto.",
                )

            pendencia_documental = pendencia_documental.strip()

            if len(pendencia_documental) > 5000:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "A pendência documental deve ter "
                        "no máximo 5.000 caracteres."
                    ),
                )
    else:
        pendencia_documental = None

    con = obter_conexao_clientes()

    try:
        garantir_schema_auditoria(con)

        cursor = con.cursor()

        cursor.execute(
            """
            SELECT
                id,
                auditado,
                "status final" AS status_final,
                motivo,
                cpf_regular,
                financeiro_ok,
                documentos_pessoais_ok,
                pendencia_documental
            FROM clientes
            WHERE id = ?
            """,
            (id,),
        )

        registro = cursor.fetchone()

        if registro is None:
            raise HTTPException(
                status_code=404,
                detail="Registro não encontrado.",
            )

        anterior = dict(registro)

        # Se um campo novo não for enviado, preserva o valor
        # existente no banco.
        novos_valores = {}

        for campo in campos_sim_nao:
            if campo in dados:
                novos_valores[campo] = dados[campo]
            else:
                novos_valores[campo] = anterior.get(campo)

        if "pendencia_documental" in dados:
            novos_valores["pendencia_documental"] = (
                pendencia_documental
            )
        else:
            novos_valores["pendencia_documental"] = (
                anterior.get("pendencia_documental")
            )

        data_modificacao = agora_utc()

        cursor.execute(
            """
            UPDATE clientes
            SET
                auditado = ?,
                "status final" = ?,
                motivo = ?,
                cpf_regular = ?,
                financeiro_ok = ?,
                documentos_pessoais_ok = ?,
                pendencia_documental = ?,
                auditoria_modificada_em = ?
            WHERE id = ?
            """,
            (
                auditado,
                status_final,
                motivo,
                novos_valores["cpf_regular"],
                novos_valores["financeiro_ok"],
                novos_valores["documentos_pessoais_ok"],
                novos_valores["pendencia_documental"],
                data_modificacao,
                id,
            ),
        )

        campos_alterados = {
            "auditado": {
                "anterior": anterior["auditado"],
                "novo": auditado,
            },
            "status_final": {
                "anterior": anterior["status_final"],
                "novo": status_final,
            },
            "motivo_alterado": (
                (anterior.get("motivo") or "") != motivo
            ),
        }

        for campo in campos_sim_nao:
            campos_alterados[campo] = {
                "anterior": anterior.get(campo),
                "novo": novos_valores[campo],
            }

        campos_alterados["pendencia_documental"] = {
            "anterior": anterior.get("pendencia_documental"),
            "novo": novos_valores["pendencia_documental"],
        }

        detalhes = {
            "resultado": "sucesso",
            "campos_alterados": campos_alterados,
            "data_modificacao": data_modificacao,
        }

        registrar_log(
            con,
            usuario=usuario,
            request=request,
            acao="ATUALIZAR_AUDITORIA",
            entidade="clientes",
            registro_id=id,
            detalhes=detalhes,
        )

        con.commit()

        logger.info(
            "usuario=%s | ip=%s | AUDITORIA_ATUALIZADA | id=%s",
            getattr(usuario, "email", "desconhecido"),
            obter_ip_requisicao(request),
            id,
        )

        return {
            "message": "Auditoria salva com sucesso.",
            "data": {
                "id": id,
                "auditado": auditado,
                "status_final": status_final,
                "motivo": motivo,
                "cpf_regular": novos_valores["cpf_regular"],
                "financeiro_ok": novos_valores["financeiro_ok"],
                "documentos_pessoais_ok": (
                    novos_valores["documentos_pessoais_ok"]
                ),
                "pendencia_documental": (
                    novos_valores["pendencia_documental"]
                ),
                "auditoria_modificada_em": data_modificacao,
            },
        }

    except HTTPException:
        con.rollback()
        raise

    except sqlite3.Error:
        con.rollback()

        logger.exception(
            "Erro ao salvar auditoria e registrar log: id=%s",
            id,
        )

        raise HTTPException(
            status_code=500,
            detail="Não foi possível salvar a auditoria.",
        )

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
        registrar_evento_auditoria(
            usuario=None,
            request=request,
            acao="FALHA_AUTENTICACAO",
            entidade="sessao",
            registro_id=id,
            detalhes={
                "resultado": "negado",
                "motivo": "sessao_invalida_ou_expirada",
                "recurso": "baixar_lastro",
            },
        )

        raise HTTPException(
            status_code=401,
            detail="Sessão inválida ou expirada. Faça login novamente.",
        )

    if getattr(usuario, "nivel", None) not in {
        "auditor",
        "admin",
    }:
        registrar_evento_auditoria(
            usuario=usuario,
            request=request,
            acao="ACESSO_NEGADO",
            entidade="clientes",
            registro_id=id,
            detalhes={
                "resultado": "negado",
                "motivo": "permissao_insuficiente",
                "recurso": "baixar_lastro",
            },
        )

        raise HTTPException(
            status_code=403,
            detail="Você não tem permissão para baixar o lastro.",
        )

    cliente = obter_cliente_por_id(id)

    if cliente is None:
        registrar_evento_auditoria(
            usuario=usuario,
            request=request,
            acao="REGISTRO_NAO_ENCONTRADO",
            entidade="clientes",
            registro_id=id,
            detalhes={
                "resultado": "falha",
                "recurso": "baixar_lastro",
            },
        )

        raise HTTPException(
            status_code=404,
            detail="Cliente não encontrado.",
        )

    prefixo = (cliente.get("lastro") or "").strip()
    ccb = str(cliente.get("ccb") or id).strip()

    if not prefixo:
        registrar_evento_auditoria(
            usuario=usuario,
            request=request,
            acao="DOWNLOAD_LASTRO_INDISPONIVEL",
            entidade="clientes",
            registro_id=id,
            detalhes={
                "resultado": "falha",
                "motivo": "caminho_lastro_nao_cadastrado",
            },
        )

        raise HTTPException(
            status_code=404,
            detail="Este cliente não possui caminho de lastro cadastrado.",
        )

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

                    if chave.endswith("/"):
                        continue

                    nome_arquivo = chave[len(prefixo):].lstrip("/")

                    if not nome_arquivo:
                        continue

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

        registrar_evento_auditoria(
            usuario=usuario,
            request=request,
            acao="ERRO_DOWNLOAD_LASTRO",
            entidade="clientes",
            registro_id=id,
            detalhes={
                "resultado": "erro",
                "motivo": "falha_no_s3",
            },
        )

        raise HTTPException(
            status_code=502,
            detail="Não foi possível obter os arquivos do lastro no S3.",
        )

    if quantidade_arquivos == 0:
        registrar_evento_auditoria(
            usuario=usuario,
            request=request,
            acao="DOWNLOAD_LASTRO_SEM_ARQUIVOS",
            entidade="clientes",
            registro_id=id,
            detalhes={
                "resultado": "falha",
                "motivo": "nenhum_arquivo_encontrado",
            },
        )

        raise HTTPException(
            status_code=404,
            detail="Nenhum arquivo encontrado para este lastro.",
        )

    zip_buffer.seek(0)

    ccb_segura = re.sub(r"[^A-Za-z0-9_-]", "_", ccb)[:100]
    nome_zip = f"lastro_{ccb_segura or id}.zip"

    registrar_evento_auditoria(
        usuario=usuario,
        request=request,
        acao="DOWNLOAD_LASTRO",
        entidade="clientes",
        registro_id=id,
        detalhes={
            "resultado": "sucesso",
            "quantidade_arquivos": quantidade_arquivos,
            "formato": "zip",
        },
    )

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