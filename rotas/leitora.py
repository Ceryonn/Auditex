from io import BytesIO
from html import escape
import re
import logging

import pdfplumber

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database.database import obter_db
from rotas.auth import obter_usuario_logado_web
from rotas.auditoria import registrar_evento_auditoria


router = APIRouter(tags=["Leitora"])
templates = Jinja2Templates(directory="templates")
MAX_FILE_SIZE = 15 * 1024 * 1024

logger = logging.getLogger(__name__)


# ============================================================
# FUNÇÃO AUXILIAR DE LOG
# ============================================================

def registrar_evento_leitora(
    request: Request,
    usuario,
    acao: str,
    *,
    resultado: str = "sucesso",
    motivo: str | None = None,
    detalhes: dict | None = None,
):
    informacoes = {
        "resultado": resultado,
        "metodo": request.method,
        "recurso": request.url.path,
    }

    if motivo:
        informacoes["motivo"] = motivo

    if detalhes:
        informacoes.update(detalhes)

    registrar_evento_auditoria(
        usuario=usuario,
        request=request,
        acao=acao,
        entidade="leitora",
        detalhes=informacoes,
    )


# ============================================================

def exigir_usuario_logado(
    request: Request,
    db: Session = Depends(obter_db),
):
    usuario = obter_usuario_logado_web(request, db)

    if usuario is None:
        registrar_evento_leitora(
            request,
            None,
            "FALHA_AUTENTICACAO_LEITORA",
            resultado="negado",
            motivo="sessao_invalida_ou_expirada",
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão inválida ou expirada. Faça login novamente.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return usuario


# ============================================================

async def ler_pdf(pdf: UploadFile) -> bytes:
    nome = (pdf.filename or "").lower()

    if not nome.endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Envie um arquivo PDF válido.",
        )

    conteudo = await pdf.read(MAX_FILE_SIZE + 1)

    if not conteudo:
        raise HTTPException(
            status_code=400,
            detail="O arquivo enviado está vazio.",
        )

    if len(conteudo) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="O PDF ultrapassa o limite de 15 MB.",
        )

    if not conteudo.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=400,
            detail="O arquivo enviado não parece ser um PDF válido.",
        )

    return conteudo


# ============================================================

def extrair_texto(pdf_file) -> str:
    partes = []

    try:
        with pdfplumber.open(pdf_file) as pdf:
            for pagina in pdf.pages:
                conteudo = pagina.extract_text()

                if conteudo:
                    partes.append(conteudo)

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail="Não foi possível ler o PDF. Verifique se o arquivo está íntegro.",
        ) from exc

    return "\n".join(partes)


# ============================================================

def limpar_cpf(cpf):
    return re.sub(r"\D", "", cpf or "")


def limpar_rg(rg):
    return re.sub(r"\D", "", rg or "")


def normalizar_nome(nome):
    return (nome or "").lower().strip()


def normalizar_valor(valor):
    if not valor:
        return None

    return valor.replace("R$", "").strip()


# ============================================================

def extrair_dados_ccb(texto):
    texto = texto.replace("\xa0", " ")

    # RG
    rg = None

    match = re.search(
        r'\bRG\b\s*(?:n[º°o]\s*)?[:\-]?\s*([\d.\-]+)',
        texto,
        re.IGNORECASE
    )

    if match:
        rg = limpar_rg(match.group(1))

    # CPF
    cpf = None

    match = re.search(
        r'CPF\s*sob\s*n[º°o]\s*([\d.\-]+)',
        texto,
        re.IGNORECASE
    )

    if not match:
        match = re.search(
            r'\bCPF\b.{0,40}?(\d{3}\.\d{3}\.\d{3}-\d{2})',
            texto,
            re.DOTALL | re.IGNORECASE
        )

    if not match:
        match = re.search(
            r'\bCPF\b.{0,40}?(\d{11})',
            texto,
            re.DOTALL | re.IGNORECASE
        )

    if match:
        cpf = limpar_cpf(match.group(1))

    # NÚMERO KG
    kg = None

    match = re.search(
        r'\bKG\s*(?:N[º°o]\s*)?[:\-]?\s*(\S+)',
        texto,
        re.IGNORECASE
    )

    if match:
        kg = match.group(1).strip()

    # NOME
    nome = None

    match = re.search(
        r'\bNome\s*:\s*(.*?)(?:,|\n|$)',
        texto,
        re.IGNORECASE
    )

    if match:
        nome = match.group(1).strip()

    # VALOR LIBERADO AO CLIENTE
    valor_lib = None

    match = re.search(
        r'a\.m\.\s*R\$\s*([\d.]+,\d{2})',
        texto,
        re.IGNORECASE
    )

    if match:
        valor_lib = match.group(1).strip()

    if not valor_lib:
        match = re.search(
            r'Valor\s+Financiado\s+'
            r'Valor\s+Liberado\s+ao\s+Cliente\s*:?\s*'
            r'Taxa\s+Juros\s+Nominal\s*:?\s*'
            r'[\d.,]+\s*%\s*a\.m\.\s*'
            r'R\$\s*([\d.]+,\d{2})\s+'
            r'R\$\s*([\d.]+,\d{2})',
            texto,
            re.IGNORECASE | re.DOTALL
        )

        if match:
            valor_lib = match.group(2).strip()

    if not valor_lib:
        match = re.search(
            r'Valor\s+Financiado\s+'
            r'Valor\s+Liberado\s+ao\s+Cliente\s*:?\s*'
            r'Taxa\s+Juros\s+Nominal\s*:?\s*'
            r'[\d.,]+\s*%\s*a\.m\.\s*'
            r'R\$\s*([\d.]+,\d{2})\s+'
            r'R\$\s*([\d.]+,\d{2})',
            texto,
            re.IGNORECASE | re.DOTALL
        )

        if match:
            valor_lib = match.group(2).strip()

    if not valor_lib:
        match = re.search(
            r'Valor\s+Financiado.{0,200}?'
            r'R\$\s*([\d.]+,\d{2}).{0,100}?'
            r'R\$\s*([\d.]+,\d{2})',
            texto,
            re.IGNORECASE | re.DOTALL
        )

        if match:
            valor_lib = match.group(2).strip()

    if not valor_lib:
        match = re.search(
            r'Valor\s+Liberado\s+ao\s+Cliente'
            r'.{0,150}?R\$\s*\*?\s*([\d.]+,\d{2})',
            texto,
            re.DOTALL | re.IGNORECASE
        )

        if match:
            valor_lib = match.group(1).strip()

    # VALOR TOTAL DA DÍVIDA
    vlrtccb = None

    match = re.search(
        r'Valor\s+Total\s+da\s+D[ií]vida\s*:?\s*'
        r'(?:Data\s+de\s+Emiss[aã]o\s*:?\s*)?'
        r'(?:DIAS\s*:?\s*)?'
        r'.{0,200}?'
        r'R\$\s*([\d.]+,\d{2})',
        texto,
        re.IGNORECASE | re.DOTALL
    )

    if match:
        valor_texto = match.group(1)
        vlrtccb = float(
            valor_texto.replace(".", "").replace(",", ".")
        )
    else:
        vlrtccb = "Valor não encontrado."

    return {
        "rg": rg,
        "cpf": cpf,
        "kg": kg,
        "nome": nome,
        "valor liberado": valor_lib,
        "valor total": vlrtccb,
        "parcelas": extrair_parcelas_ccb(texto)
    }


# ============================================================
# PÁGINAS DA LEITORA
# ============================================================

@router.get("/leitora", response_class=HTMLResponse)
async def front_leitora(
    request: Request,
    usuario=Depends(exigir_usuario_logado),
):
    registrar_evento_leitora(
        request, usuario, "ACESSAR_LEITORA"
    )

    return templates.TemplateResponse(
        request=request,
        name="leitora.html",
        context={
            "usuario_logado": usuario,
            "messages": [],
        },
    )


@router.get("/leitora/ccb", response_class=HTMLResponse)
async def pagina_leitora(
    request: Request,
    usuario=Depends(exigir_usuario_logado),
):
    registrar_evento_leitora(
        request, usuario, "ACESSAR_LEITORA_CCB"
    )

    return templates.TemplateResponse(
        request=request,
        name="leitoraccb.html",
        context={
            "usuario_logado": usuario,
            "messages": [],
        },
    )


@router.get("/leitora/comp", response_class=HTMLResponse)
async def pagina_leitora_comp(
    request: Request,
    usuario=Depends(exigir_usuario_logado),
):
    registrar_evento_leitora(
        request, usuario, "ACESSAR_LEITORA_COMPROVANTES"
    )

    return templates.TemplateResponse(
        request=request,
        name="leitora comp.html",
        context={
            "usuario_logado": usuario,
            "messages": [],
        },
    )


# ============================================================
# EXTRAÇÃO DE PARCELAS
# ============================================================

def extrair_parcelas_ccb(texto: str) -> list[dict]:
    parcelas = []

    if not texto:
        return parcelas

    texto = texto.replace("\xa0", " ")

    padrao_valor = r"(?:\d{1,3}(?:\.\d{3})+|\d+)[,.]\d{2}"

    padrao_linha = re.compile(
        rf"^\s*"
        rf"(?P<parcela>\d{{1,4}})\s+"
        rf"(?P<vencimento>\d{{2}}/\d{{2}}/\d{{4}})\s+"
        rf"(?P<prazo>\d{{1,5}})\s+"
        rf"(?P<valor_parcela>{padrao_valor})\s+"
        rf"(?P<descontos>{padrao_valor})\s+"
        rf"(?P<divida>{padrao_valor})"
        rf"\s*$"
    )

    for linha in texto.splitlines():
        linha = linha.strip()

        if not linha:
            continue

        match = padrao_linha.match(linha)

        if not match:
            continue

        dados = match.groupdict()

        parcelas.append({
            "parcela": dados["parcela"],
            "vencimento": dados["vencimento"],
            "prazo": int(dados["prazo"]),
            "valor_parcela": dados["valor_parcela"],
            "descontos": dados["descontos"],
            "divida": dados["divida"],
        })

    return parcelas

# ============================================================
# LEITURA GERAL DO PDF
# ============================================================

@router.post("/leitora/nova", response_class=HTMLResponse)
async def leitora_geral(
    request: Request,
    pdf: UploadFile = File(...),
    usuario=Depends(exigir_usuario_logado),
):
    try:
        conteudo_pdf = await ler_pdf(pdf)
        texto = extrair_texto(BytesIO(conteudo_pdf))

        registrar_evento_leitora(
            request,
            usuario,
            "LER_PDF_GERAL",
            detalhes={
                "tamanho_bytes": len(conteudo_pdf),
                "texto_extraido": bool(texto.strip()),
            },
        )

        return HTMLResponse(
            content=f"<pre>{escape(texto)}</pre>"
        )

    except HTTPException as exc:
        registrar_evento_leitora(
            request,
            usuario,
            "FALHA_LEITURA_PDF_GERAL",
            resultado="falha",
            detalhes={
                "status_http": exc.status_code,
            },
        )
        raise

    except Exception:
        logger.exception(
            "Erro inesperado na leitura geral de PDF."
        )

        registrar_evento_leitora(
            request,
            usuario,
            "ERRO_LEITURA_PDF_GERAL",
            resultado="erro",
            motivo="erro_interno",
        )
        raise


# ============================================================
# EXTRAÇÃO DOS DADOS DA CCB
# ============================================================

@router.post("/parse_leitora")
async def parse_leitora(
    request: Request,
    pdf: UploadFile = File(...),
    usuario=Depends(exigir_usuario_logado),
):
    try:
        conteudo_pdf = await ler_pdf(pdf)
        texto = extrair_texto(BytesIO(conteudo_pdf))

        if not texto.strip():
            raise HTTPException(
                status_code=422,
                detail=(
                    "Não foi possível extrair texto deste PDF. "
                    "Se ele for digitalizado como imagem, será necessário OCR."
                ),
            )

        dados = extrair_dados_ccb(texto)

        registrar_evento_leitora(
            request,
            usuario,
            "EXTRAIR_DADOS_CCB",
            detalhes={
                "tamanho_bytes": len(conteudo_pdf),
                "quantidade_parcelas": len(dados["parcelas"]),
            },
        )

        return JSONResponse(content=dados)

    except HTTPException as exc:
        registrar_evento_leitora(
            request,
            usuario,
            "FALHA_EXTRACAO_CCB",
            resultado="falha",
            detalhes={
                "status_http": exc.status_code,
            },
        )
        raise

    except Exception:
        logger.exception(
            "Erro inesperado na extração de dados da CCB."
        )

        registrar_evento_leitora(
            request,
            usuario,
            "ERRO_EXTRACAO_CCB",
            resultado="erro",
            motivo="erro_interno",
        )
        raise


# ============================================================
# EXTRAÇÃO DE DADOS DO COMPROVANTE
# ============================================================

def extrair_comp(texto):

    dados = {
        "nome": None,
        "valor": None,
        "cpf_miolo": None
    }

    linhas = [
        l.strip()
        for l in texto.splitlines()
        if l.strip()
    ]

    for i, linha in enumerate(linhas):
        if linha.lower().rstrip(":") == 'valor':
            if i + 1 < len(linhas):
                dados['valor'] = normalizar_valor(linhas[i + 1])
            break

    for i, linha in enumerate(linhas):
        if linha.lower().rstrip(":") == 'nome':
            if i + 1 < len(linhas):
                dados['nome'] = linhas[i + 1]

            break

    # CPF parcialmente oculto
    cpf = re.search(
        r"\*{3}\.(\d{3})\.(\d{3})-\*{2}",
        texto
    )

    if cpf:
        cpf_miolo = cpf.group(1) + cpf.group(2)
    else:
        # Fallback: segundo bloco com 2 dígitos e 1 asterisco
        cpf = re.search(
            r"\*{3}\.(\d{3})\.(\d{2})\*-\*{2}",
            texto
        )

        if cpf:
            dados["cpf_miolo"] = cpf.group(1) + cpf.group(2)

    if dados['nome'] == None:
        dados['nome'] = "Nome não informado no comprovante."

    return dados


# ============================================================
# EXTRAÇÃO DOS DADOS DO COMPROVANTE
# ============================================================

@router.post("/parse_leitora/comp")
async def parse_leitora_comp(
    request: Request,
    pdf: UploadFile = File(...),
    usuario=Depends(exigir_usuario_logado),
):
    try:
        conteudo_pdf = await ler_pdf(pdf)
        texto = extrair_texto(BytesIO(conteudo_pdf))

        if not texto.strip():
            raise HTTPException(
                status_code=422,
                detail=(
                    "Não foi possível extrair texto deste PDF. "
                    "Se ele for digitalizado como imagem, será necessário OCR."
                ),
            )

        dados = extrair_comp(texto)

        registrar_evento_leitora(
            request,
            usuario,
            "EXTRAIR_DADOS_COMPROVANTE",
            detalhes={
                "tamanho_bytes": len(conteudo_pdf),
            },
        )

        return JSONResponse(content=dados)

    except HTTPException as exc:
        registrar_evento_leitora(
            request,
            usuario,
            "FALHA_EXTRACAO_COMPROVANTE",
            resultado="falha",
            detalhes={
                "status_http": exc.status_code,
            },
        )
        raise

    except Exception:
        logger.exception(
            "Erro inesperado na extração do comprovante."
        )

        registrar_evento_leitora(
            request,
            usuario,
            "ERRO_EXTRACAO_COMPROVANTE",
            resultado="erro",
            motivo="erro_interno",
        )
        raise
    