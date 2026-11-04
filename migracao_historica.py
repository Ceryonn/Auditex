
import json
import sqlite3
import tkinter as tk

from tkinter import filedialog, messagebox
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path

from openpyxl import load_workbook


# =========================================================
# CONFIGURAÇÕES
# =========================================================

FUSO_BRASIL = ZoneInfo("America/Sao_Paulo")

ACAO = "ATUALIZAR_AUDITORIA"
ENTIDADE = "clientes"
IP_MIGRACAO = "MIGRACAO_HISTORICA"

COLUNAS_NECESSARIAS = {
    "ccb",
    "auditoria_modificada_em",
    "responsavel",
}


# =========================================================
# INTERFACE TKINTER
# =========================================================

root = tk.Tk()
root.withdraw()

root.attributes("-topmost", True)

messagebox.showinfo(
    "Migração de logs históricos",
    "Selecione o arquivo Excel que contém o histórico "
    "das auditorias."
)

arquivo_excel = filedialog.askopenfilename(
    title="Selecionar planilha de auditorias",
    filetypes=[
        ("Planilhas Excel", "*.xlsx"),
        ("Todos os arquivos", "*.*"),
    ],
)

if not arquivo_excel:
    messagebox.showinfo(
        "Cancelado",
        "Nenhuma planilha foi selecionada."
    )
    root.destroy()
    raise SystemExit


messagebox.showinfo(
    "Banco de dados",
    "Agora selecione o arquivo clientes.db utilizado "
    "pelo Auditex."
)

arquivo_banco = filedialog.askopenfilename(
    title="Selecionar clientes.db",
    filetypes=[
        ("Banco SQLite", "*.db"),
        ("Todos os arquivos", "*.*"),
    ],
)

if not arquivo_banco:
    messagebox.showinfo(
        "Cancelado",
        "Nenhum banco de dados foi selecionado."
    )
    root.destroy()
    raise SystemExit


# =========================================================
# TRATAMENTO DE DATAS
# =========================================================

def converter_data_para_utc(valor):

    if valor is None:
        raise ValueError("Data vazia.")

    if isinstance(valor, datetime):

        data = valor

    else:

        texto = str(valor).strip()

        formatos = [
            "%d/%m/%y %H:%M",
            "%d/%m/%Y %H:%M",
            "%d/%m/%y",
            "%d/%m/%Y",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
        ]

        data = None

        for formato in formatos:

            try:
                data = datetime.strptime(texto, formato)
                break

            except ValueError:
                continue

        if data is None:
            try:
                data = datetime.fromisoformat(texto)

            except ValueError:
                raise ValueError(
                    f"Formato de data inválido: {texto}"
                )

    # Datas sem fuso são interpretadas como horário de Brasília.
    if data.tzinfo is None:
        data = data.replace(tzinfo=FUSO_BRASIL)

    data_utc = data.astimezone(timezone.utc)

    return data_utc.isoformat(timespec="seconds")


# =========================================================
# NORMALIZAÇÃO
# =========================================================

def normalizar(valor):

    if valor is None:
        return ""

    return str(valor).strip()


def assinatura_log(data_hora, email, ccb):

    return (
        data_hora,
        normalizar(email).casefold(),
        normalizar(ccb).casefold(),
    )


# =========================================================
# LEITURA DA PLANILHA
# =========================================================

def ler_planilha(caminho):

    workbook = load_workbook(
        caminho,
        read_only=True,
        data_only=True,
    )

    registros = []

    ignorados = 0
    abas_processadas = 0

    for planilha in workbook.worksheets:

        linhas = planilha.iter_rows(values_only=True)

        cabecalho_original = next(linhas, None)

        if not cabecalho_original:
            continue

        cabecalho = [
            normalizar(coluna).lower()
            for coluna in cabecalho_original
        ]

        if not COLUNAS_NECESSARIAS.issubset(set(cabecalho)):
            continue

        abas_processadas += 1

        indices = {
            nome: cabecalho.index(nome)
            for nome in COLUNAS_NECESSARIAS
        }

        for linha in linhas:

            try:

                ccb = normalizar(
                    linha[indices["ccb"]]
                )

                responsavel = normalizar(
                    linha[indices["responsavel"]]
                )

                data_original = linha[
                    indices["auditoria_modificada_em"]
                ]

                if not ccb or not responsavel or not data_original:
                    ignorados += 1
                    continue

                data_hora = converter_data_para_utc(
                    data_original
                )

                registros.append({
                    "ccb": ccb,
                    "email": responsavel,
                    "data_hora": data_hora,
                })

            except (ValueError, TypeError, IndexError):
                ignorados += 1

    workbook.close()

    return registros, ignorados, abas_processadas


# =========================================================
# CONSULTA DO BANCO
# SOMENTE LEITURA NA TABELA CLIENTES
# =========================================================

def obter_clientes(con):

    cursor = con.cursor()

    cursor.execute("""
        SELECT id, ccb
        FROM clientes
        WHERE ccb IS NOT NULL
          AND TRIM(ccb) <> ''
    """)

    clientes = {}

    ambiguos = set()

    for row in cursor.fetchall():

        ccb = normalizar(row["ccb"]).casefold()

        if ccb in clientes:
            ambiguos.add(ccb)
        else:
            clientes[ccb] = row["id"]

    for ccb in ambiguos:
        clientes.pop(ccb, None)

    return clientes, ambiguos


# =========================================================
# IDENTIFICA LOGS JÁ EXISTENTES
# =========================================================

def obter_logs_existentes(con, clientes_por_id):

    cursor = con.cursor()

    cursor.execute("""
        SELECT
            data_hora,
            email,
            registro_id,
            detalhes
        FROM logs_sistema
        WHERE acao = ?
          AND entidade = ?
    """, (ACAO, ENTIDADE))

    existentes = set()

    for row in cursor.fetchall():

        try:

            detalhes = json.loads(
                row["detalhes"] or "{}"
            )

            ccb = normalizar(detalhes.get("ccb"))

            if not ccb:

                ccb = normalizar(
                    clientes_por_id.get(
                        str(row["registro_id"]),
                        ""
                    )
                )

            if not ccb:
                continue

            data_existente = datetime.fromisoformat(
                row["data_hora"]
            )

            if data_existente.tzinfo is None:
                data_existente = data_existente.replace(
                    tzinfo=timezone.utc
                )

            data_existente = data_existente.astimezone(
                timezone.utc
            ).isoformat(timespec="seconds")

            existentes.add(
                assinatura_log(
                    data_existente,
                    row["email"],
                    ccb,
                )
            )

        except (ValueError, TypeError, AttributeError):
            continue

    return existentes


# =========================================================
# PROCESSAMENTO E INSERÇÃO DOS LOGS
# =========================================================

def executar_migracao():

    con = None

    try:

        print("\nLendo planilha...")

        registros, invalidos, abas = ler_planilha(
            arquivo_excel
        )

        if not registros:
            messagebox.showwarning(
                "Nenhum registro",
                "Nenhum registro válido foi encontrado "
                "nas abas da planilha."
            )
            return

        print(f"Abas processadas: {abas}")
        print(f"Registros válidos: {len(registros)}")
        print(f"Registros inválidos: {invalidos}")

        # Não cria nem altera tabelas.
        con = sqlite3.connect(arquivo_banco)
        con.row_factory = sqlite3.Row

        # Confere se a tabela já existe.
        cursor = con.cursor()

        cursor.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name = 'logs_sistema'
        """)

        if cursor.fetchone() is None:
            raise RuntimeError(
                "A tabela logs_sistema não existe no banco."
            )

        # Consulta os clientes.
        clientes, ambiguos = obter_clientes(con)

        clientes_por_id = {
            str(id_cliente): ccb
            for ccb, id_cliente in clientes.items()
        }

        # Consulta os logs anteriores.
        existentes = obter_logs_existentes(
            con,
            clientes_por_id,
        )

        novos_logs = []

        duplicados = 0
        sem_cliente = 0
        ccb_ambiguas = 0

        # Evita duplicidade também dentro da própria planilha.
        processados = set()

        for registro in registros:

            ccb = registro["ccb"]
            email = registro["email"]
            data_hora = registro["data_hora"]

            chave_ccb = ccb.casefold()

            if chave_ccb in ambiguos:
                ccb_ambiguas += 1
                continue

            id_cliente = clientes.get(chave_ccb)

            if id_cliente is None:
                sem_cliente += 1
                continue

            assinatura = assinatura_log(
                data_hora,
                email,
                ccb,
            )

            if assinatura in existentes or assinatura in processados:
                duplicados += 1
                continue

            processados.add(assinatura)

            detalhes = {
                "resultado": "sucesso",
                "ccb": ccb,
                "origem": "migracao_historica",
            }

            novos_logs.append((
                data_hora,
                email,
                IP_MIGRACAO,
                ACAO,
                ENTIDADE,
                str(id_cliente),
                json.dumps(
                    detalhes,
                    ensure_ascii=False,
                ),
            ))

        # Prévia antes da gravação.
        mensagem = (
            "PRÉVIA DA MIGRAÇÃO\n\n"
            f"Registros lidos: {len(registros)}\n"
            f"Logs novos: {len(novos_logs)}\n"
            f"Duplicados: {duplicados}\n"
            f"CCBs inexistentes: {sem_cliente}\n"
            f"CCBs ambíguas: {ccb_ambiguas}\n"
            f"Registros inválidos: {invalidos}\n\n"
            "Somente logs serão inseridos.\n"
            "A tabela clientes não será modificada.\n\n"
            "Deseja continuar?"
        )

        confirmar = messagebox.askyesno(
            "Confirmar importação",
            mensagem,
        )

        if not confirmar:
            messagebox.showinfo(
                "Cancelado",
                "Nenhum log foi inserido."
            )
            return

        if not novos_logs:
            messagebox.showinfo(
                "Sem novos logs",
                "Não existem registros novos para importar."
            )
            return

        # ÚNICA OPERAÇÃO DE ESCRITA DO SCRIPT.
        cursor.executemany("""
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
        """, novos_logs)

        con.commit()

        messagebox.showinfo(
            "Migração concluída",
            (
                "Importação realizada com sucesso!\n\n"
                f"Logs inseridos: {len(novos_logs)}\n"
                f"Duplicados ignorados: {duplicados}\n"
                f"CCBs inexistentes: {sem_cliente}\n"
                f"CCBs ambíguas: {ccb_ambiguas}\n"
                f"Registros inválidos: {invalidos}\n\n"
                "Nenhum cadastro de cliente foi alterado."
            ),
        )

        print("\nMIGRAÇÃO CONCLUÍDA")
        print(f"Logs inseridos: {len(novos_logs)}")

    except Exception as erro:

        if con is not None:
            con.rollback()

        print(f"\nERRO: {erro}")

        messagebox.showerror(
            "Erro na migração",
            (
                "A importação não foi concluída.\n\n"
                f"Detalhes: {erro}\n\n"
                "As inserções desta execução foram revertidas."
            ),
        )

    finally:

        if con is not None:
            con.close()

        root.destroy()


# =========================================================
# EXECUÇÃO
# =========================================================

if __name__ == "__main__":
    executar_migracao()
