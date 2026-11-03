'''
import sqlite3

conn = sqlite3.connect("clientes.db")
cursor = conn.cursor()

cursor.execute("""
    SELECT id, ccb, "status final", auditado
    FROM clientes
    WHERE id = 5051
""")

registro = cursor.fetchone()

if registro:
    print("Registro no banco:")
    print("ID:", registro[0])
    print("CCB:", repr(registro[1]))
    print("Status final atual:", repr(registro[2]))
    print("Auditado atual:", repr(registro[3]))
else:
    print("Registro 5051 não encontrado.")

conn.close()

'''

import sqlite3

conn = sqlite3.connect("clientes.db")
cursor = conn.cursor()

cursor.execute("""
    SELECT *
    FROM clientes
    WHERE operacao = 'V8 - BANCO BRB'
    AND lastro IS NULL
""")

registros = cursor.fetchall()

for registro in registros:
    print(registro)

print(f"Total de registros encontrados: {len(registros)}")

conn.close()