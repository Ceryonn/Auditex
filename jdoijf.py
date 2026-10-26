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



import sqlite3

con = sqlite3.connect("clientes.db")

for coluna in con.execute("PRAGMA table_info(clientes)"):
    print(coluna[1], "-", coluna[2])

con.close()