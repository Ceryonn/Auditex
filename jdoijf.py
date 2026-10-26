"""
import sqlite3

conn = sqlite3.connect("users.db")

try:
    cursor = conn.cursor()

    cursor.execute(""" """
        UPDATE users
        SET nivel = ?
        WHERE id = ?
   , ("admin", 1))

    conn.commit()
    print(f"{cursor.rowcount} registro(s) atualizado(s).")

finally:
    conn.close()

"""


from rotas.leitora import extrair_parcelas_ccb

texto_teste = """
Parc. Dt. Vcto Prazo
Parcela Descontos Dívida
001 01/12/2025 172 52,44 16,49 35,95
002 01/12/2026 537 44,59 20,38 24,21
003 01/12/2027 902 50,53 28,45 22,08
004 01/12/2028 1268 40,42 26,21 14,21
005 01/12/2029 1633 48,50 34,77 13,73
"""

print(extrair_parcelas_ccb(texto_teste))


print(extrair_parcelas_ccb(texto_teste))