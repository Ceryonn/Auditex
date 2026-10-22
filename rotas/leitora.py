from fastapi import APIRouter, Request, File, UploadFile
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from passlib.context import CryptContext
import pdfplumber
from io import BytesIO
from html import escape
import re


router = APIRouter(tags=["Leitora"])

templates = Jinja2Templates(directory="templates")

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)






# Utilitário

def extrair_texto(pdf_file):
    texto = ""


    with pdfplumber.open(pdf_file) as pdf:
        for pagina in pdf.pages:
            conteudo = pagina.extract_text()
            if conteudo:
                texto += conteudo + "\n"

    return texto



def limpar_cpf(cpf):
    return re.sub(r'\D', '', cpf or "")

def limpar_rg(rg):
    return re.sub(r'\D', '', rg or "")

def normalizar_nome(nome):
    return (nome or "").lower.strip()

def normalizar_valor(valor):
    if not valor:
        return None
    return valor.replace("R$", "").strip()




# CCB

def extrair_dados_ccb(texto):


    rg = None

    match = re.search(
        r'\bRG\b\s*(?:n[º°o]\s*)?[:\-]?\s*([\d.\-]+)',
        texto,
        re.IGNORECASE
    )

    if match:
        rg = limpar_rg(match.group(1))

#####


    cpf = None

    match = re.search(
        r'CPF\s*sob\s*n[º°o]\s*([\d.\-]+)',
        texto,
        re.IGNORECASE
    )

    if match:
        cpf = limpar_cpf(match.group(1))

    else:
        match2 = re.search(
            r'CPF.(\d{3}\.\d{3}\.\d{3}-\d{2})',
            texto,
            re.DOTALL | re.IGNORECASE
        )

        if match2:
            cpf = limpar_cpf(match2.group(1))

#####

    kg = None

    match = re.search(r'KG Nº\s*(\S+)', texto, re.IGNORECASE)
    if match:
        kg = match.group(1).strip()


#####

    nome = None

    match = re.search(r'Nome:\s*(.*?)\,', texto, re.IGNORECASE)
    if match:
        nome = match.group(1).strip()


#####

    valor_lib = None

    match = re.search(
        r'a\.m\.\s*R\$\s*([\d\.,]+)',
        texto,
        re.IGNORECASE
    )

    if match:
        valor_lib = match.group(1).strip()
    else:
        match2 = re.search(
            r'Valor Liberado ao Cliente.*?R\$\*([\d\.,]+)',
            texto,
            re.DOTALL | re.IGNORECASE
        )

        if match2:
            valor_lib = match2.group(1).strip()



#####

    vlrtccb = None

    match = re.search(
        r'Valor Total da Dívida:\s*R\$\s*([\d\.,]+)',
        texto
    )

    if match:
        vlrtccb = float(
            match.group(1)
            .replace('.', '')
            .replace(',', '.')
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



@router.post("/leitora", response_class=HTMLResponse)
async def leitora_geral(pdf: UploadFile = File(...)):
    conteudo_pdf = await pdf.read()

    texto = extrair_texto(BytesIO(conteudo_pdf))

    return HTMLResponse(
        content=f"<pre>{escape(texto)}</pre>"
    )



@router.post("/parse_leitora")
async def parse_leitora(pdf: UploadFile = File(...)):
    conteudo_pdf = await pdf.read()

    dados = {}



    texto = extrair_texto(BytesIO(conteudo_pdf))

    dados = extrair_dados_ccb(texto)



    return dados

 
'''    return HTMLResponse(
        content=f"<pre>{escape(texto)}</pre>"
    )

'''