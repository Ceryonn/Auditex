from io import BytesIO
from html import escape
import re

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


router = APIRouter(tags=["Leitora"])

templates = Jinja2Templates(directory="templates")

MAX_FILE_SIZE = 15 * 1024 * 1024


# ============================================================

def exigir_usuario_logado(
    request: Request,
    db: Session = Depends(obter_db),
):
    usuario = obter_usuario_logado_web(request, db)

    if usuario is None:
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
    # Normaliza espaços sem remover as quebras de linha originais.
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

    # Modelo antigo: valor precedido por a.m. R$
    match = re.search(
        r'a\.m\.\s*R\$\s*([\d.]+,\d{2})',
        texto,
        re.IGNORECASE
    )

    if match:
        valor_lib = match.group(1).strip()

    # Modelo em que os dois valores aparecem na mesma linha
    # Valor Financiado = R$ 295,98
    # Valor Liberado ao Cliente = R$ 127,77
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

    # Modelo com rótulos e valores separados por quebras de linha
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

    # Alternativa mais flexível para PDFs cuja extração
    # reorganiza os rótulos e os valores.
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

    # Fallback do modelo antigo
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

    # Modelo antigo e modelo em que o rótulo e o valor
    # aparecem em linhas diferentes.
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
        "valor total": vlrtccb
    }




# ============================================================

@router.get("/leitora", response_class=HTMLResponse)
async def pagina_leitora(
    request: Request,
    usuario=Depends(exigir_usuario_logado),
):
    return templates.TemplateResponse(
        request=request,
        name="leitora.html",
        context={
            "usuario_logado": usuario,
            "messages": [],
        },
    )


# ============================================================

@router.post("/leitora", response_class=HTMLResponse)
async def leitora_geral(
    pdf: UploadFile = File(...),
    usuario=Depends(exigir_usuario_logado),
):
    conteudo_pdf = await ler_pdf(pdf)
    texto = extrair_texto(BytesIO(conteudo_pdf))

    return HTMLResponse(
        content=f"<pre>{escape(texto)}</pre>"
    )

# ============================================================

@router.post("/parse_leitora")
async def parse_leitora(
    pdf: UploadFile = File(...),
    usuario=Depends(exigir_usuario_logado),
):
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

    return JSONResponse(
        content=extrair_dados_ccb(texto)
    )