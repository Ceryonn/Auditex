'''
from database.clientes import obter_conexao_clientes

con = obter_conexao_clientes()

try:
    tabelas = con.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = 'logs_sistema'
    """).fetchall()

    print("Tabela logs_sistema:", bool(tabelas))

    if tabelas:
        total = con.execute("""
            SELECT COUNT(*) FROM logs_sistema
        """).fetchone()[0]

        print("Total de logs:", total)

        for row in con.execute("""
            SELECT id, data_hora, email, acao,
                   entidade, registro_id, detalhes
            FROM logs_sistema
            ORDER BY id DESC
            LIMIT 10
        """).fetchall():
            print(dict(row))

finally:
    con.close()

    
'''


import sqlite3
from pathlib import Path

# Ajuste este caminho se necessário.
DB_PATH = Path("clientes.db")

NOVAS_COLUNAS = {
    "cpf_regular": "TEXT",
    "financeiro_ok": "TEXT",
    "documentos_pessoais_ok": "TEXT",
    "pendencia_documental": "TEXT",
}


def adicionar_campos():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Banco de dados não encontrado: {DB_PATH.resolve()}"
        )

    con = sqlite3.connect(DB_PATH)

    try:
        cursor = con.cursor()

        # Confirma que a tabela existe.
        cursor.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name = 'clientes'
        """)

        if cursor.fetchone() is None:
            raise RuntimeError(
                "A tabela 'clientes' não existe neste banco."
            )

        # Identifica as colunas existentes.
        cursor.execute("PRAGMA table_info(clientes)")
        colunas_existentes = {
            linha[1] for linha in cursor.fetchall()
        }

        adicionadas = []

        for nome, tipo in NOVAS_COLUNAS.items():
            if nome in colunas_existentes:
                print(f"[EXISTENTE] {nome} — nenhuma alteração.")
                continue

            cursor.execute(
                f'ALTER TABLE clientes ADD COLUMN "{nome}" {tipo}'
            )
            adicionadas.append(nome)
            print(f"[OK] Coluna adicionada: {nome}")

        con.commit()

        print("\nMigração concluída!")
        print(f"Banco utilizado: {DB_PATH.resolve()}")
        print(f"Novas colunas adicionadas: {len(adicionadas)}")

    except Exception:
        con.rollback()
        raise

    finally:
        con.close()


if __name__ == "__main__":
    adicionar_campos()
