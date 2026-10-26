
import sqlite3
import os

caminho = os.path.join(
    os.path.dirname(__file__),
    "instance",
    "studyflow.db"
)

conexao = sqlite3.connect(caminho)
cursor = conexao.cursor()

cursor.execute("""
    SELECT id, usuario_id, inicio_em,
           fim_em, duracao_segundos, status
    FROM sessoes_estudo
    ORDER BY id DESC
""")

sessoes = cursor.fetchall()

for sessao in sessoes:
    print(sessao)

if not sessoes:
    print("Nenhuma sessão encontrada.")

conexao.close()
