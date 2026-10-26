import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CLIENTES_DB = BASE_DIR / "clientes.db"


def obter_conexao_clientes():
    con = sqlite3.connect(str(CLIENTES_DB))
    con.row_factory = sqlite3.Row
    return con