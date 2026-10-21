import sqlite3

conn = sqlite3.connect("users.db")

try:
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE users
        SET nivel = ?
        WHERE id = ?
    """, ("admin", 1))

    conn.commit()
    print(f"{cursor.rowcount} registro(s) atualizado(s).")

finally:
    conn.close()
