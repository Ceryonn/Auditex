'''
import sqlite3

conn = sqlite3.connect("clientes.db")

try:
    cursor = conn.cursor()

    cursor.execute("""
        ALTER TABLE clientes
        ADD COLUMN auditado TEXT NOT NULL DEFAULT 'não'
        CHECK (auditado IN ('sim', 'não'))
    """)

    cursor.execute("""
        ALTER TABLE clientes
        ADD COLUMN "status final" TEXT
        CHECK ("status final" IN (
            'aprovado',
            'pendenciado',
            'reprovado'
        ))
    """)

    cursor.execute("""
        ALTER TABLE clientes
        ADD COLUMN motivo TEXT
    """)

    conn.commit()
    print("Colunas de auditoria adicionadas com sucesso!")

except sqlite3.Error as erro:
    conn.rollback()
    print(f"Erro: {erro}")

finally:
    conn.close()

    '''
'''



import sqlite3

conn = sqlite3.connect("clientes.db")

try:
    cursor = conn.cursor()

    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
    """)

    tabelas = cursor.fetchall()

    for (tabela,) in tabelas:
        print(f"\nTabela: {tabela}")

        cursor.execute(f'PRAGMA table_info("{tabela}")')

        colunas = cursor.fetchall()

        for coluna in colunas:
            print(f" - {coluna[1]}")

finally:
    conn.close()

'''

'''

import sqlite3

con = sqlite3.connect("clientes.db")

for coluna in con.execute("PRAGMA table_info(clientes)"):
    print(coluna[1], "-", coluna[2])

con.close()




import sqlite3

con = sqlite3.connect("clientes.db")

print(con.execute("""
    SELECT sql
    FROM sqlite_master
    WHERE type = 'table' AND name = 'clientes'
""").fetchone()[0])

con.close()

'''
'''



import sqlite3
import shutil
from pathlib import Path
from datetime import datetime

DB_PATH = Path("clientes.db")

if not DB_PATH.exists():
    raise FileNotFoundError(
        f"Banco não encontrado: {DB_PATH.resolve()}"
    )

# Backup de segurança
backup = DB_PATH.with_name(
    f"clientes_backup_{datetime.now():%Y%m%d_%H%M%S}.db"
)
shutil.copy2(DB_PATH, backup)

print(f"Backup criado: {backup.resolve()}")

con = sqlite3.connect(DB_PATH)

try:
    con.execute("PRAGMA foreign_keys = OFF")
    con.execute("BEGIN IMMEDIATE")

    # Confere se a estrutura esperada existe.
    colunas = {
        row[1]
        for row in con.execute(
            "PRAGMA table_info(clientes)"
        ).fetchall()
    }

    obrigatorias = {
        "id",
        "originador",
        "fundo",
        "operacao",
        "cessao",
        "ccb",
        "documento",
        "nome",
        "lastro",
        "auditado",
        "status final",
        "motivo",
        "auditoria_modificada_em",
    }

    faltantes = obrigatorias - colunas
    if faltantes:
        raise RuntimeError(
            f"Colunas ausentes: {sorted(faltantes)}"
        )

    # Cria a nova tabela com as restrições corrigidas.
    con.execute("""
        CREATE TABLE clientes_nova (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            originador TEXT NOT NULL,
            fundo TEXT NOT NULL,
            operacao TEXT NOT NULL,
            cessao TEXT,
            ccb TEXT,
            documento TEXT,
            nome TEXT,
            lastro TEXT,
            auditado TEXT NOT NULL DEFAULT 'Pendente'
                CHECK (
                    auditado IN (
                        'Pendente',
                        'Em análise',
                        'Concluído'
                    )
                ),
            "status final" TEXT
                CHECK (
                    "status final" IN (
                        'Aprovado',
                        'Reprovado',
                        'Pendente de regularização'
                    )
                ),
            motivo TEXT,
            auditoria_modificada_em TEXT
        )
    """)

    # Migra todos os registros existentes.
    con.execute("""
        INSERT INTO clientes_nova (
            id, originador, fundo, operacao, cessao,
            ccb, documento, nome, lastro, auditado,
            "status final", motivo, auditoria_modificada_em
        )
        SELECT
            id,
            originador,
            fundo,
            operacao,
            cessao,
            ccb,
            documento,
            nome,
            lastro,
            CASE
                WHEN auditado = 'sim' THEN 'Concluído'
                WHEN auditado = 'não' THEN 'Pendente'
                WHEN auditado IN (
                    'Pendente', 'Em análise', 'Concluído'
                ) THEN auditado
                ELSE 'Pendente'
            END,
            CASE
                WHEN "status final" = 'aprovado'
                    THEN 'Aprovado'
                WHEN "status final" = 'reprovado'
                    THEN 'Reprovado'
                WHEN "status final" = 'pendenciado'
                    THEN 'Pendente de regularização'
                WHEN "status final" IN (
                    'Aprovado',
                    'Reprovado',
                    'Pendente de regularização'
                ) THEN "status final"
                ELSE NULL
            END,
            motivo,
            auditoria_modificada_em
        FROM clientes
    """)

    # Substitui a tabela antiga pela nova.
    con.execute("DROP TABLE clientes")
    con.execute(
        "ALTER TABLE clientes_nova RENAME TO clientes"
    )

    con.commit()

    print("Migração concluída com sucesso!")

    print("\nValores de auditado:")
    for linha in con.execute("""
        SELECT auditado, COUNT(*)
        FROM clientes
        GROUP BY auditado
    """):
        print(f"{linha[0]}: {linha[1]} registro(s)")

    print("\nValores de status final:")
    for linha in con.execute("""
        SELECT "status final", COUNT(*)
        FROM clientes
        GROUP BY "status final"
    """):
        print(f"{linha[0]}: {linha[1]} registro(s)")

except Exception:
    con.rollback()
    print("Erro na migração. Alterações revertidas.")
    print(f"Backup disponível em: {backup.resolve()}")
    raise

finally:
    con.close()


'''

'''

import sqlite3

con = sqlite3.connect("clientes.db")

print("Estrutura da tabela:")
print(con.execute("""
    SELECT sql
    FROM sqlite_master
    WHERE type = 'table'
      AND name = 'clientes'
""").fetchone()[0])

print("\nValores de auditado:")
print(con.execute("""
    SELECT auditado, COUNT(*)
    FROM clientes
    GROUP BY auditado
""").fetchall())

print("\nValores de status final:")
print(con.execute("""
    SELECT "status final", COUNT(*)
    FROM clientes
    GROUP BY "status final"
""").fetchall())

con.close()

'''



'''
import sqlite3

conn = sqlite3.connect("clientes.db")

try:
    cursor = conn.cursor()

    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
    """)

    tabelas = cursor.fetchall()

    for (tabela,) in tabelas:
        print(f"\nTabela: {tabela}")

        cursor.execute(f'PRAGMA table_info("{tabela}")')

        colunas = cursor.fetchall()

        for coluna in colunas:
            print(f" - {coluna[1]}")

finally:
    conn.close()

'''



'''


import sqlite3
import pandas as pd
import tkinter as tk

from tkinter import filedialog, messagebox
from pathlib import Path


# =========================
# CONFIGURAÇÕES
# =========================

DB_PATH = Path(__file__).parent / "clientes.db"
TABELA = "clientes"

COLUNAS_ATUALIZAR = [
    "auditado",
    "status final",
    "motivo",
    "auditoria_modificada_em",
    "cpf_regular",
    "financeiro_ok",
    "documentos_pessoais_ok",
    "pendencia_documental",
    "responsavel",
]


def esta_preenchido(valor):
    if pd.isna(valor):
        return False

    if isinstance(valor, str) and not valor.strip():
        return False

    return True


def executar_atualizacao():
    # Selecionar a planilha Excel
    arquivo_excel = filedialog.askopenfilename(
        title="Selecione a planilha Excel",
        filetypes=[
            ("Planilhas Excel", "*.xlsx *.xls"),
            ("Todos os arquivos", "*.*"),
        ],
    )

    # Usuário cancelou a seleção
    if not arquivo_excel:
        return

    try:
        if not DB_PATH.exists():
            raise FileNotFoundError(
                f"Banco de dados não encontrado:\n{DB_PATH}"
            )

        # Ler a planilha
        df = pd.read_excel(
            arquivo_excel,
            dtype={"ccb": str},
        )

        # Remover espaços dos nomes das colunas
        df.columns = df.columns.str.strip()

        obrigatorias = ["ccb"] + COLUNAS_ATUALIZAR
        faltantes = [
            coluna for coluna in obrigatorias
            if coluna not in df.columns
        ]

        if faltantes:
            raise ValueError(
                "Estas colunas não foram encontradas no Excel:\n\n"
                + "\n".join(faltantes)
            )

        atualizados = 0
        nao_encontrados = 0
        sem_dados = 0
        sem_ccb = 0

        # Abrir conexão com o banco
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            for _, linha in df.iterrows():
                ccb = linha["ccb"]

                if not esta_preenchido(ccb):
                    sem_ccb += 1
                    continue

                ccb = str(ccb).strip()

                # Separar apenas os campos preenchidos
                campos = {}

                for coluna in COLUNAS_ATUALIZAR:
                    valor = linha[coluna]

                    if not esta_preenchido(valor):
                        continue

                    # Converter datas do pandas para texto
                    if isinstance(valor, pd.Timestamp):
                        valor = valor.strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )

                    # Converter tipos NumPy para tipos Python
                    if hasattr(valor, "item"):
                        valor = valor.item()

                    campos[coluna] = valor

                if not campos:
                    sem_dados += 1
                    continue

                # Verificar se o CCB existe no banco
                cursor.execute(
                    f'SELECT id FROM "{TABELA}" WHERE ccb = ?',
                    (ccb,),
                )

                registros = cursor.fetchall()

                if not registros:
                    nao_encontrados += 1
                    continue

                # Montar o UPDATE apenas com as colunas preenchidas
                set_sql = ", ".join(
                    f'"{coluna}" = ?'
                    for coluna in campos
                )

                sql = (
                    f'UPDATE "{TABELA}" '
                    f'SET {set_sql} WHERE ccb = ?'
                )

                cursor.execute(
                    sql,
                    list(campos.values()) + [ccb],
                )

                atualizados += cursor.rowcount

        # Exibir resultado
        messagebox.showinfo(
            "Atualização concluída",
            f"Planilha processada com sucesso!\n\n"
            f"Registros atualizados: {atualizados}\n"
            f"CCBs não encontrados: {nao_encontrados}\n"
            f"Linhas sem dados para atualizar: {sem_dados}\n"
            f"Linhas sem CCB: {sem_ccb}",
        )

    except Exception as erro:
        messagebox.showerror(
            "Erro na atualização",
            str(erro),
        )


# =========================
# INTERFACE TKINTER
# =========================

janela = tk.Tk()
janela.title("Atualizar clientes SQLite")
janela.geometry("430x190")
janela.resizable(False, False)

titulo = tk.Label(
    janela,
    text="Atualização de clientes",
    font=("Arial", 15, "bold"),
)
titulo.pack(pady=(25, 10))

descricao = tk.Label(
    janela,
    text="Selecione uma planilha Excel para atualizar o banco.",
    font=("Arial", 10),
)
descricao.pack(pady=5)

botao = tk.Button(
    janela,
    text="Selecionar planilha e atualizar",
    command=executar_atualizacao,
    font=("Arial", 11),
    padx=12,
    pady=7,
)
botao.pack(pady=15)

janela.mainloop()



'''

'''
import sqlite3

conn = sqlite3.connect("clientes.db")
cursor = conn.cursor()

# Estrutura da tabela
cursor.execute("PRAGMA table_info(clientes)")

print("\n=== COLUNAS DA TABELA CLIENTES ===\n")

for coluna in cursor.fetchall():
    cid, nome, tipo, notnull, default, pk = coluna
    print(
        f"Coluna: {nome} | Tipo: {tipo} | "
        f"NOT NULL: {notnull} | Default: {default} | PK: {pk}"
    )

# SQL de criação: mostra CHECK constraints e outras regras
cursor.execute("""
    SELECT sql
    FROM sqlite_master
    WHERE type = 'table' AND name = 'clientes'
""")

print("\n=== REGRAS E CONSTRAINTS ===\n")
print(cursor.fetchone()[0])

# Valores existentes em cada coluna
print("\n=== VALORES DISTINTOS POR COLUNA ===\n")

cursor.execute("PRAGMA table_info(clientes)")

for coluna in cursor.fetchall():
    nome = coluna[1]
    cursor.execute(
        f'SELECT DISTINCT "{nome}" FROM clientes LIMIT 100'
    )
    valores = [linha[0] for linha in cursor.fetchall()]
    print(f"{nome}: {valores}")

conn.close()

'''

'''


import sqlite3
import shutil
import threading
import queue
import tkinter as tk
import pandas as pd

from pathlib import Path
from tkinter import filedialog, messagebox
from datetime import datetime

PASTA = Path(__file__).parent
DB_PATH = PASTA / "clientes.db"

COLUNAS = [
    "auditado",
    "status final",
    "motivo",
    "auditoria_modificada_em",
    "cpf_regular",
    "financeiro_ok",
    "documentos_pessoais_ok",
    "pendencia_documental",
    "responsavel",
]

eventos = queue.Queue()


def preencher(valor):
    if pd.isna(valor):
        return False
    return not (isinstance(valor, str) and not valor.strip())


def executar(excel):
    try:
        if not DB_PATH.exists():
            raise FileNotFoundError(f"Banco não encontrado: {DB_PATH}")

        # Backup antes de alterar o banco
        backup = DB_PATH.with_name(
            f"clientes_backup_{datetime.now():%Y%m%d_%H%M%S}.db"
        )
        shutil.copy2(DB_PATH, backup)

        df = pd.read_excel(excel, dtype=str)
        df.columns = df.columns.str.strip()

        faltantes = [
            c for c in ["ccb"] + COLUNAS
            if c not in df.columns
        ]
        if faltantes:
            raise ValueError(f"Colunas ausentes: {faltantes}")

        # Carregar registros do banco uma única vez
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT ccb, id FROM clientes")
            mapa = {}
            for ccb, id_registro in cursor.fetchall():
                if ccb is not None:
                    mapa.setdefault(str(ccb).strip(), []).append(id_registro)

            # Preparar atualizações em memória
            tarefas = []

            for _, linha in df.iterrows():
                ccb = linha["ccb"]

                if not preencher(ccb):
                    continue

                ccb = str(ccb).strip()
                ids = mapa.get(ccb, [])

                if not ids:
                    continue

                campos = {}
                for coluna in COLUNAS:
                    valor = linha[coluna]
                    if preencher(valor):
                        campos[coluna] = valor.strip() if isinstance(valor, str) else valor

                if campos:
                    for id_registro in ids:
                        tarefas.append((id_registro, campos))

            total = len(tarefas)
            eventos.put(("progresso", 0, total))

            # Transação única; atualizações parametrizadas
            with conn:
                for inicio in range(0, total, 500):
                    lote = tarefas[inicio:inicio + 500]

                    
                    for id_registro, campos in lote:

                        set_sql = ", ".join(
                            f'"{coluna}" = ?' for coluna in campos
                        )
                        sql = f'UPDATE clientes SET {set_sql} WHERE id = ?'

                        try:
                            cursor.execute(
                                sql,
                                list(campos.values()) + [id_registro]
                            )
                        except sqlite3.IntegrityError as erro:
                            raise RuntimeError(
                                f"Erro no registro ID {id_registro}: {erro}"
                            ) from erro

                    eventos.put((
                        "progresso",
                        min(inicio + len(lote), total),
                        total
                    ))

        eventos.put(("fim", total, backup))

    except Exception as erro:
        eventos.put(("erro", str(erro)))


def selecionar():
    excel = filedialog.askopenfilename(
        title="Selecione a planilha",
        filetypes=[("Excel", "*.xlsx *.xls")]
    )
    if not excel:
        return

    botao.config(state="disabled")
    status.config(text="Iniciando...")
    threading.Thread(
        target=executar,
        args=(excel,),
        daemon=True
    ).start()
    janela.after(100, verificar_eventos)


def verificar_eventos():
    try:
        while True:
            evento = eventos.get_nowait()

            if evento[0] == "progresso":
                _, atual, total = evento
                status.config(text=f"Atualizando: {atual}/{total}")

            elif evento[0] == "fim":
                _, total, backup = evento
                status.config(text="Concluído!")
                botao.config(state="normal")
                messagebox.showinfo(
                    "Concluído",
                    f"Registros atualizados: {total}\n\n"
                    f"Backup criado em:\n{backup}"
                )
                return

            elif evento[0] == "erro":
                status.config(text="Erro na atualização")
                botao.config(state="normal")
                messagebox.showerror("Erro", evento[1])
                return

    except queue.Empty:
        pass

    janela.after(100, verificar_eventos)


janela = tk.Tk()
janela.title("Atualizar clientes")
janela.geometry("430x180")
janela.resizable(False, False)

tk.Label(
    janela,
    text="Atualização do banco SQLite",
    font=("Arial", 14, "bold")
).pack(pady=20)

botao = tk.Button(
    janela,
    text="Selecionar Excel e atualizar",
    command=selecionar
)
botao.pack(pady=5)

status = tk.Label(janela, text="Aguardando planilha...")
status.pack(pady=10)

janela.mainloop()


'''

'''
import sqlite3

conn = sqlite3.connect("clientes.db")

try:
    cursor = conn.cursor()

    cursor.execute("""
        SELECT lastro
        FROM clientes
        WHERE ccb = ?    
    """, ("FJB26R3064",))


    resultado = cursor.fetchone()
    print(resultado)


#    conn.commit()


finally:
    conn.close()

    
    '''

'''


import sqlite3

conn = sqlite3.connect("clientes.db")
cursor = conn.cursor()

# Estrutura da tabela
cursor.execute("PRAGMA table_info(clientes)")

print("\n=== COLUNAS DA TABELA CLIENTES ===\n")

for coluna in cursor.fetchall():
    cid, nome, tipo, notnull, default, pk = coluna
    print(
        f"Coluna: {nome} | Tipo: {tipo} | "
        f"NOT NULL: {notnull} | Default: {default} | PK: {pk}"
    )

# SQL de criação: mostra CHECK constraints e outras regras
cursor.execute("""
    SELECT sql
    FROM sqlite_master
    WHERE type = 'table' AND name = 'clientes'
""")

print("\n=== REGRAS E CONSTRAINTS ===\n")
print(cursor.fetchone()[0])

# Valores existentes em cada coluna
print("\n=== VALORES DISTINTOS POR COLUNA ===\n")

cursor.execute("PRAGMA table_info(clientes)")

for coluna in cursor.fetchall():
    nome = coluna[1]
    cursor.execute(
        f'SELECT DISTINCT "{nome}" FROM clientes LIMIT 100'
    )
    valores = [linha[0] for linha in cursor.fetchall()]
    print(f"{nome}: {valores}")

conn.close()


'''

'''

### NOME COLUNAS ###
# 
# import sqlite3

conn = sqlite3.connect("clientes.db")

try:
    cursor = conn.cursor()

    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
    """)

    tabelas = cursor.fetchall()

    for (tabela,) in tabelas:
        print(f"\nTabela: {tabela}")

        cursor.execute(f'PRAGMA table_info("{tabela}")')

        colunas = cursor.fetchall()

        for coluna in colunas:
            print(f" - {coluna[1]}")

finally:
    conn.close()


'''


'''

### Atualizar banco ###


import sqlite3
import pandas as pd
import tkinter as tk

from tkinter import filedialog, messagebox
from pathlib import Path


# =========================
# CONFIGURAÇÕES
# =========================

DB_PATH = Path(__file__).parent / "clientes.db"
TABELA = "clientes"

COLUNAS_ATUALIZAR = [
    "auditado",
    "status final",
    "motivo",
    "auditoria_modificada_em",
    "cpf_regular",
    "financeiro_ok",
    "documentos_pessoais_ok",
    "pendencia_documental",
    "responsavel",
]


def esta_preenchido(valor):
    if pd.isna(valor):
        return False

    if isinstance(valor, str) and not valor.strip():
        return False

    return True


def executar_atualizacao():
    # Selecionar a planilha Excel
    arquivo_excel = filedialog.askopenfilename(
        title="Selecione a planilha Excel",
        filetypes=[
            ("Planilhas Excel", "*.xlsx *.xls"),
            ("Todos os arquivos", "*.*"),
        ],
    )

    # Usuário cancelou a seleção
    if not arquivo_excel:
        return

    try:
        if not DB_PATH.exists():
            raise FileNotFoundError(
                f"Banco de dados não encontrado:\n{DB_PATH}"
            )

        # Ler a planilha
        df = pd.read_excel(
            arquivo_excel,
            dtype={"ccb": str},
        )

        # Remover espaços dos nomes das colunas
        df.columns = df.columns.str.strip()

        obrigatorias = ["ccb"] + COLUNAS_ATUALIZAR
        faltantes = [
            coluna for coluna in obrigatorias
            if coluna not in df.columns
        ]

        if faltantes:
            raise ValueError(
                "Estas colunas não foram encontradas no Excel:\n\n"
                + "\n".join(faltantes)
            )

        atualizados = 0
        nao_encontrados = 0
        sem_dados = 0
        sem_ccb = 0

        # Abrir conexão com o banco
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            for _, linha in df.iterrows():
                ccb = linha["ccb"]

                if not esta_preenchido(ccb):
                    sem_ccb += 1
                    continue

                ccb = str(ccb).strip()

                # Separar apenas os campos preenchidos
                campos = {}

                for coluna in COLUNAS_ATUALIZAR:
                    valor = linha[coluna]

                    if not esta_preenchido(valor):
                        continue

                    # Converter datas do pandas para texto
                    if isinstance(valor, pd.Timestamp):
                        valor = valor.strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )

                    # Converter tipos NumPy para tipos Python
                    if hasattr(valor, "item"):
                        valor = valor.item()

                    campos[coluna] = valor

                if not campos:
                    sem_dados += 1
                    continue

                # Verificar se o CCB existe no banco
                cursor.execute(
                    f'SELECT id FROM "{TABELA}" WHERE ccb = ?',
                    (ccb,),
                )

                registros = cursor.fetchall()

                if not registros:
                    nao_encontrados += 1
                    continue

                # Montar o UPDATE apenas com as colunas preenchidas
                set_sql = ", ".join(
                    f'"{coluna}" = ?'
                    for coluna in campos
                )

                sql = (
                    f'UPDATE "{TABELA}" '
                    f'SET {set_sql} WHERE ccb = ?'
                )

                cursor.execute(
                    sql,
                    list(campos.values()) + [ccb],
                )

                atualizados += cursor.rowcount

        # Exibir resultado
        messagebox.showinfo(
            "Atualização concluída",
            f"Planilha processada com sucesso!\n\n"
            f"Registros atualizados: {atualizados}\n"
            f"CCBs não encontrados: {nao_encontrados}\n"
            f"Linhas sem dados para atualizar: {sem_dados}\n"
            f"Linhas sem CCB: {sem_ccb}",
        )

    except Exception as erro:
        messagebox.showerror(
            "Erro na atualização",
            str(erro),
        )


# =========================
# INTERFACE TKINTER
# =========================

janela = tk.Tk()
janela.title("Atualizar clientes SQLite")
janela.geometry("430x190")
janela.resizable(False, False)

titulo = tk.Label(
    janela,
    text="Atualização de clientes",
    font=("Arial", 15, "bold"),
)
titulo.pack(pady=(25, 10))

descricao = tk.Label(
    janela,
    text="Selecione uma planilha Excel para atualizar o banco.",
    font=("Arial", 10),
)
descricao.pack(pady=5)

botao = tk.Button(
    janela,
    text="Selecionar planilha e atualizar",
    command=executar_atualizacao,
    font=("Arial", 11),
    padx=12,
    pady=7,
)
botao.pack(pady=15)

janela.mainloop()


'''


'''
import sqlite3

conn = sqlite3.connect("clientes.db")

try:
    cursor = conn.cursor()

    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
    """)

    tabelas = cursor.fetchall()

    for (tabela,) in tabelas:
        print(f"\nTabela: {tabela}")

        cursor.execute(f'PRAGMA table_info("{tabela}")')

        colunas = cursor.fetchall()

        for coluna in colunas:
            print(f" - {coluna[1]}")

finally:
    conn.close()

    
    '''


import sqlite3

conn = sqlite3.connect("clientes.db")


cursor = conn.cursor()

cursor.execute("""
                SELECT auditoria_modificada_em 
                FROM clientes  
                WHERE CCB LIKE "050DFA5467"
                """)

resultado = cursor.fetchone()

print(resultado)

