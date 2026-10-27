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