"""
Instalar: pip install -r requirements.txt
na outra maquina trocar a URL por: bolt://100.122.141.42:7687
no host: bolt://localhost:7687
"""
import os
import random
import time
from datetime import date

from neo4j import GraphDatabase

URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
USER = os.getenv("NEO4J_USER", "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD", "Jupiter07?")

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

def run(query, **params):
    with driver.session() as session:
        return list(session.run(query, **params))


def cadastrar_usuario(email, nome):
    run(
        """
        MERGE (u:Usuario {email: $email})
        ON CREATE SET u.nome = $nome
        """,
        email=email, nome=nome,
    )


def avaliar(email, titulo, nota):
    r = run(
        """
        MATCH (u:Usuario {email: $email}), (f:Filme {titulo: $titulo})
        MERGE (u)-[r:AVALIOU]->(f)
        SET r.nota = $nota, r.data = date($data)
        RETURN f.titulo AS titulo
        """,
        email=email, titulo=titulo, nota=nota, data=str(date.today()),
    )
    return bool(r)


def minhas_avaliacoes(email):
    return run(
        """
        MATCH (:Usuario {email: $email})-[r:AVALIOU]->(f:Filme)
        RETURN f.titulo AS titulo, r.nota AS nota ORDER BY r.nota DESC
        """,
        email=email,
    )


def media_filme(titulo):
    r = run(
        """
        MATCH (:Usuario)-[a:AVALIOU]->(f:Filme {titulo: $titulo})
        RETURN count(a) AS total, round(avg(a.nota), 2) AS media
        """,
        titulo=titulo,
    )
    return r[0]["total"], r[0]["media"]


def top_filmes(n=10):
    return run(
        """
        MATCH (:Usuario)-[a:AVALIOU]->(f:Filme)
        WITH f, count(a) AS total, avg(a.nota) AS media
        WHERE total > 100
        RETURN f.titulo AS titulo, total, round(media, 2) AS media
        ORDER BY media DESC LIMIT $n
        """,
        n=n,
    )


def usuario_compativel(email, minimo=2):
    # compara as notas nos filmes que os dois avaliaram: menor diferença média = mais compatível
    r = run(
        """
        MATCH (u:Usuario {email: $email})-[a:AVALIOU]->(f:Filme)<-[b:AVALIOU]-(o:Usuario)
        WHERE o <> u
        WITH o, count(f) AS em_comum, avg(abs(a.nota - b.nota)) AS dif
        WHERE em_comum >= $minimo
        RETURN o.nome AS nome, o.email AS email, em_comum, round(dif, 2) AS dif
        ORDER BY dif ASC, em_comum DESC LIMIT 1
        """,
        email=email, minimo=minimo,
    )
    return r[0] if r else None


def simulador(qtd=20, intervalo=1.0):
    """Insere avaliações aleatórias, uma por segundo, e mostra o total subindo."""
    filmes = [r["titulo"] for r in run("MATCH (f:Filme) RETURN f.titulo AS titulo")]
    for _ in range(qtd):
        email = f"usuario{random.randint(1, 100000)}@exemplo.com"
        titulo = random.choice(filmes)
        nota = random.randint(1, 5)
        avaliar(email, titulo, nota)
        total = run("MATCH ()-[r:AVALIOU]->() RETURN count(r) AS c")[0]["c"]
        print(f"{email} deu {nota} para '{titulo}' | total de avaliações: {total}")
        time.sleep(intervalo)


MENU = """
1) Cadastrar usuário
2) Avaliar um filme
3) Minhas avaliações
4) Achar usuário mais compatível
5) Média de um filme
6) Top 10 filmes
7) Simulador em tempo real
0) Sair
> """

if __name__ == "__main__":
    while True:
        op = input(MENU).strip()
        if op == "1":
            cadastrar_usuario(input("email: "), input("nome: "))
            print("Usuário cadastrado.")
        elif op == "2":
            email = input("email: ")
            titulo = input("filme (título exato): ")
            if avaliar(email, titulo, int(input("nota (1-5): "))):
                print("Avaliação salva.")
            else:
                print("Usuário ou filme não encontrado. Confira o e-mail e o título.")
        elif op == "3":
            for r in minhas_avaliacoes(input("email: ")):
                print(f"{r['titulo']}: {r['nota']}")
        elif op == "4":
            r = usuario_compativel(input("seu email: "))
            if r:
                print(f"Mais compatível: {r['nome']} ({r['email']})")
                print(f"{r['em_comum']} filmes em comum, diferença média de nota: {r['dif']}")
            else:
                print("Nenhum usuário compatível encontrado.")
        elif op == "5":
            total, media = media_filme(input("filme: "))
            print(f"{total} avaliações, média {media}")
        elif op == "6":
            for r in top_filmes():
                print(f"{r['titulo']}: {r['media']} ({r['total']} avaliações)")
        elif op == "7":
            simulador()
        elif op == "0":
            break
    driver.close()