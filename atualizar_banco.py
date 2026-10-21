
import sqlite3

# Ajuste o caminho caso seu users.db esteja em outra pasta.
conexao = sqlite3.connect("users.db")

try:
    colunas = conexao.execute(
        "PRAGMA table_info(users)"
    ).fetchall()

    nomes = [coluna[1] for coluna in colunas]

    if not colunas:
        raise RuntimeError(
            "Tabela 'users' não encontrada. Confira o caminho do banco."
        )

    if "session_version" not in nomes:
        conexao.execute("""
            ALTER TABLE users
            ADD COLUMN session_version INTEGER NOT NULL DEFAULT 0
        """)
        conexao.commit()
        print("Coluna session_version adicionada com sucesso.")
    else:
        print("A coluna session_version já existe. Nada foi alterado.")

finally:
    conexao.close()
